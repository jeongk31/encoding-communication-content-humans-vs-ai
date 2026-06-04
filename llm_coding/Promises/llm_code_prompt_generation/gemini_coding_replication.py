#!/usr/bin/env python3
"""
Gemini Coding Replication Script - PROMPT GENERATION VERSION
Replicates the human coding exercise using Google Gemini API for the Promises and Partnerships experiment data.

Phase 1: The LLM reads the experimental + coding instructions and generates its own reusable prompt template.
Phase 2: The generated template is used to classify each message.

TEST MODE:
export TEST_MODE=true
python gemini_coding_replication.py
"""

import os
import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, using system environment variables")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiCodingReplication:
    def __init__(self, api_key: str, test_mode: bool = False):
        self.api_key = api_key
        self.test_mode = test_mode

        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

        # EXPERIMENTAL INSTRUCTIONS (from Experiment_Instructions.pdf)
        self.experimental_instructions = """
EXPERIMENTAL INSTRUCTIONS:
===========================

Experiment Instructions
Promises and Partnerships

Thank you for participating in this session. The purpose of this experiment is to study how people make decisions in a particular situation. Feel free to ask us questions as they arise, by raising your hand. Please do not speak to other participants during the experiment.

You will receive $5 for participating in this session. You may also receive additional money, depending on the decisions made (as described below). Upon completion of the session, this additional amount will be paid to you individually and privately.

During the session, you will be paired with another person. However, no participant will ever know the identity of the person with whom he or she is paired.

Decision Tasks

In each pair, one person will have the role of A, and the other will have the role of B. The amount of money you earn depends on the decisions made in your pair.

On the designated decision sheet, each person A will indicate whether he or she wishes to choose IN or OUT.
- If A chooses OUT, A and B each receive $5.

We will collect these sheets after the choices have been indicated. Next, each person B will indicate whether he or she wishes to choose ROLL or DON'T ROLL (a die). Note that B will not know whether A has chosen IN or OUT; however, since B's decision will only make a difference when A has chosen IN, we ask B's to presume (for the purpose of making this decision) that A has chosen IN.

Payoffs Summary

Decision                                      A Receives    B Receives
A chooses OUT                                 $5            $5
A chooses IN, B chooses DON'T ROLL            $0            $14
A chooses IN, B chooses ROLL, die = 1         $0            $10
A chooses IN, B chooses ROLL, die = 2,3,4,5, or 6    $12    $10

(All of these amounts are in addition to the $5 show-up fee.)

Message Instructions
[For Message from B Treatment]

Prior to the decision by A and B concerning IN or OUT, B has an option to send a message to A. Each B receives a blank sheet, on which a message can be written, if desired. We will allow time as needed for people to write messages, then these will be collected. Please print clearly if you wish to send a message to A.

Restrictions:
- No one is allowed to identify him or herself by name, number, gender, or appearance.
- The experimenter will monitor the messages. Violations (at experimenter discretion) will result in B receiving only the $5 show-up fee, and the paired A receiving the average amount received by other A's.
- Other than these restrictions, B may say anything that he or she wishes in this message.
- If you wish not to send a message, simply circle the letter B at the top of the sheet.
"""

        # CODING INSTRUCTIONS (from Coding_Instructions.pdf)
        self.coding_instructions = """
CODING INSTRUCTIONS:
====================

General Description of the Task

You will be coding messages sent by participants in the "Promises and Partnership" experiment conducted by Charness & Dufwenberg (2006). The study focuses on the impact of communication on trust and cooperation.

In this experiment, participants played a one-shot trust game where:
- Participants were paired and referred to as Player A (principal) and Player B (agent).
- Player A decides whether to enter a partnership ("In") or opt out ("Out").
- If A chooses "Out", both players A and B receive ($5, $5) or ($7, $7) depending on the treatment.
- If A chooses "In", Player B decides to:
  - "Roll": A six-sided die is rolled with the following payoff possibilities:
    5/6 probability -> A gets $12, B gets $10
    1/6 probability -> A gets $0, B gets $10
  - "Don't Roll": A gets $0, B gets $14.
- In some treatments, Player B could send a pre-play message to Player A before decisions were made. These messages were non-binding and free-form.

Your task now is to code each message based on its content to analyze how communication type influences trust and cooperation.

Your Coding Task

You will be shown each message sent by Player B. Classify each message into one of these categories:

1. Promise (P)
The message explicitly states an intention to choose "Roll" (i.e. to cooperate) if player A chooses "In". This includes direct promises, commitments, or statements of intended action. Examples: "I will roll", "if you choose In, I will roll", "don't worry, I promise to roll."

2. Empty Talk (E)
The message does not express any promise or intention to Roll. This includes greetings, good luck wishes, jokes, general thoughts, comments irrelevant to the game decision, or messages expressing uncertainty about their intended action.

3. No Message (N)
No message was sent (blank or opted out). This category applies when Player B had the option to send a message but explicitly declined to do so.

If a message is difficult to classify, use your best judgment based on explicit content.

Overview of The Coding Procedure

Step 1: Read thoroughly the full message (or lack thereof) for each observation.
Step 2: Assign each message to one and only one of the three defined categories (P, E, N).
Step 3: Record the assigned category.

Respond in JSON format:
{
    "classification": "P/E/N"
}
"""

        self.results = {}
        self.generated_template = None

    def generate_coding_prompt(self):
        """Phase 1: Ask the LLM to generate its own coding prompt template."""
        logger.info("Phase 1: Generating coding prompt template from Gemini...")

        meta_prompt = f"""You are a research assistant. Below are the experimental instructions and coding instructions for a trust game experiment ("Promises and Partnerships"). Your task is to read and internalize these instructions, then generate a single reusable prompt template that will be used to classify messages from this experiment.

=== EXPERIMENTAL INSTRUCTIONS ===
{self.experimental_instructions}

=== CODING INSTRUCTIONS ===
{self.coding_instructions}

=== YOUR TASK ===
Based on the above instructions, generate a single, self-contained prompt template that can be reused to classify any message from this experiment. The template must:

1. Contain all necessary context about the experiment and coding categories so that a coder (or AI) can understand the task without seeing the original instructions
2. Include these EXACT placeholders (with curly braces) that will be filled in for each message:
   - {{message}} — the actual message text to classify (or [NO MESSAGE/EMPTY] if blank)
   - {{context}} — additional context about the session/player
3. Instruct the coder to return ONLY a JSON object: {{"classification": "P/E/N"}}
4. Clearly explain the three categories: Promise (P), Empty Talk (E), No Message (N)
5. Explain the experimental setup so the coder understands what "Roll" and "Don't Roll" mean

Return ONLY the prompt template text, nothing else. Do not wrap it in quotes or code blocks."""

        for attempt in range(5):
            try:
                response = self.model.generate_content(meta_prompt)
                generated_prompt = response.text.strip()
                logger.info(f"Generated prompt template ({len(generated_prompt)} chars)")
                self.generated_template = generated_prompt
                return generated_prompt
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Resource exhausted" in error_str:
                    wait_time = (2 ** attempt) * 2
                    logger.warning(f"Rate limited (attempt {attempt + 1}/5). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Prompt generation attempt {attempt + 1} failed: {str(e)}")
                    if attempt < 4:
                        time.sleep(2 ** attempt)

        raise RuntimeError("Failed to generate coding prompt template after 5 attempts")

    def classify_message_with_gemini(self, message: str, context: str = "", max_retries: int = 5) -> Dict[str, Any]:
        """Phase 2: Use the generated template to classify a message."""
        for attempt in range(max_retries):
            try:
                message_str = str(message) if not pd.isna(message) else ""
                if not message_str or message_str.strip() == "" or message_str.lower() == 'nan':
                    message_str = "[NO MESSAGE/EMPTY]"

                prompt = self.generated_template.replace('{message}', message_str)
                prompt = prompt.replace('{context}', context)

                if self.test_mode:
                    print("\n" + "=" * 80)
                    print("SENDING TO LLM:")
                    print("=" * 80)
                    print(f"\n[USER PROMPT]:\n{prompt}")
                    print("=" * 80)

                response = self.model.generate_content(prompt)
                response_text = response.text

                if self.test_mode:
                    print("\n[LLM RESPONSE]:")
                    print(response_text)
                    print("=" * 80)

                try:
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        result = json.loads(json_str)
                    else:
                        result = self._extract_classification_from_text(response_text)

                    if self.test_mode:
                        print(f"Processed: {result['classification']}")
                    return result

                except json.JSONDecodeError:
                    result = self._extract_classification_from_text(response_text)
                    if self.test_mode:
                        print(f"Processed: {result['classification']}")
                    return result

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Resource exhausted" in error_str:
                    wait_time = (2 ** attempt) * 2
                    logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error classifying message with Gemini: {e}")
                    return {
                        "classification": "ERROR",
                        "explanation": f"Error: {str(e)}",
                        "confidence": 0
                    }

        logger.error(f"Max retries ({max_retries}) exhausted for rate limiting")
        return {
            "classification": "ERROR",
            "explanation": "Rate limit exceeded after max retries",
            "confidence": 0
        }

    def _extract_classification_from_text(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        if "no message" in text_lower or text_lower.strip() == "n":
            classification = "N"
        elif "promise" in text_lower:
            classification = "P"
        elif "empty talk" in text_lower:
            classification = "E"
        else:
            classification = "UNKNOWN"

        confidence = 5
        if "confidence" in text:
            import re
            conf_match = re.search(r'confidence.*?(\d+)', text)
            if conf_match:
                confidence = int(conf_match.group(1))

        return {
            "classification": classification,
            "explanation": f"Extracted from text: {text[:100]}...",
            "confidence": confidence
        }

    def process_csv_file(self, file_path: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Successfully loaded {file_path} with {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()

    def process_excel_file(self, file_path: str) -> pd.DataFrame:
        try:
            df = pd.read_excel(file_path)
            logger.info(f"Successfully loaded {file_path} with {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()

    def process_table_s1(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Processing Table S.I (5x5 Messages from B)")
        if self.test_mode:
            df = df.head(5).reset_index(drop=True)
            logger.info(f"TEST MODE: Processing only first {len(df)} rows")

        results = []
        for idx, row in df.iterrows():
            session = row['Sess']
            player_id = row['ID']
            message = row['Message']
            human_class = row.get('Class', '')
            choice_a = row.get('A', '')
            choice_b = row.get('B', '')

            context = f"Session {session}, Player ID {player_id}, Player A chose {choice_a}, Player B chose {choice_b}, Human classified as: {human_class}"
            gemini_result = self.classify_message_with_gemini(message, context)

            result_row = {
                'Sess': session,
                'ID': player_id,
                'Message': message,
                'Class': gemini_result['classification']
            }
            results.append(result_row)
            time.sleep(2)

            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(df)} rows from Table S.I")

        return pd.DataFrame(results)

    def process_table_s2(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Processing Table S.II (7x7 Messages from B)")
        if self.test_mode:
            df = df.head(5).reset_index(drop=True)
            logger.info(f"TEST MODE: Processing only first {len(df)} rows")

        results = []
        for idx, row in df.iterrows():
            session = row['Sess']
            player_id = row['ID']
            message = row['Message']
            human_class = row.get('Class', '')
            choice_a = row.get('A', '')
            choice_b = row.get('B', '')

            context = f"Session {session}, Player ID {player_id}, Player A chose {choice_a}, Player B chose {choice_b}, Human classified as: {human_class}, 7x7 payoff matrix"
            gemini_result = self.classify_message_with_gemini(message, context)

            result_row = {
                'Sess': session,
                'ID': player_id,
                'Message': message,
                'Class': gemini_result['classification']
            }
            results.append(result_row)
            time.sleep(2)

            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(df)} rows from Table S.II")

        return pd.DataFrame(results)

    def process_table_s3(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Processing Table S.III (5x5 Messages from A)")
        if self.test_mode:
            df = df.head(5).reset_index(drop=True)
            logger.info(f"TEST MODE: Processing only first {len(df)} rows")

        results = []
        for idx, row in df.iterrows():
            session = row['Sess']
            player_id = row['ID']
            message = row['Message']
            choice_a = row.get("A's Choice", '')
            choice_b = row.get("B's Choice", '')

            context = f"Session {session}, Player ID {player_id}, Player A chose {choice_a}, Player B chose {choice_b}, Message is from Player A (not B)"
            gemini_result = self.classify_message_with_gemini(message, context)

            result_row = {
                'Sess': session,
                'ID': player_id,
                'Message': message,
                'Class': gemini_result['classification']
            }
            results.append(result_row)
            time.sleep(2)

            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(df)} rows from Table S.III")

        return pd.DataFrame(results)

    def process_excel_data(self, agent_file: str, principal_file: str) -> Dict[str, pd.DataFrame]:
        logger.info("Processing Excel data files")
        agent_df = self.process_excel_file(agent_file)
        principal_df = self.process_excel_file(principal_file)

        agent_results = []
        if 'agent_message' in agent_df.columns and 'Sent_message' in agent_df.columns:
            if self.test_mode:
                message_rows = agent_df[agent_df['Sent_message'] == 1].head(5)
            else:
                message_rows = agent_df[agent_df['Sent_message'] == 1]

            for idx, row in message_rows.iterrows():
                if row['Sent_message'] == 1:
                    agent_id = row['Agent']
                    message = row.get('agent_message', '')
                    principal_row = principal_df[principal_df['Principal'] == agent_id]
                    if not principal_row.empty:
                        choice_in = principal_row.iloc[0]['IN']
                        choice_roll = row['ROLL']
                        context = f"Agent {agent_id}, Player A chose IN={choice_in}, Player B chose ROLL={choice_roll}"
                        gemini_result = self.classify_message_with_gemini(message, context)
                        result_row = {
                            'Sess': agent_id,
                            'ID': agent_id,
                            'Message': message,
                            'Class': gemini_result['classification']
                        }
                        agent_results.append(result_row)
                        time.sleep(2)

        principal_results = []
        if 'principal_message' in principal_df.columns and 'Received_message' in principal_df.columns:
            if self.test_mode:
                message_rows = principal_df[principal_df['Received_message'] == 1].head(5)
            else:
                message_rows = principal_df[principal_df['Received_message'] == 1]

            for idx, row in message_rows.iterrows():
                if row['Received_message'] == 1:
                    principal_id = row['Principal']
                    message = row.get('principal_message', '')
                    agent_row = agent_df[agent_df['Agent'] == principal_id]
                    if not agent_row.empty:
                        choice_in = row['IN']
                        choice_roll = agent_row.iloc[0]['ROLL']
                        context = f"Principal {principal_id}, Player A chose IN={choice_in}, Player B chose ROLL={choice_roll}"
                        gemini_result = self.classify_message_with_gemini(message, context)
                        result_row = {
                            'Sess': principal_id,
                            'ID': principal_id,
                            'Message': message,
                            'Class': gemini_result['classification']
                        }
                        principal_results.append(result_row)
                        time.sleep(2)

        return {
            'agent_messages': pd.DataFrame(agent_results),
            'principal_messages': pd.DataFrame(principal_results)
        }

    def run_full_replication(self, data_dir: str = "../Data", output_dir: str = None) -> Dict[str, pd.DataFrame]:
        logger.info("Starting full Gemini coding replication (PROMPT GENERATION)")

        self.output_dir = Path(output_dir or os.getenv('OUTPUT_DIR', 'results'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Phase 1: Generate the coding prompt template
        self.generate_coding_prompt()

        # Save the generated prompt for inspection
        prompt_file = self.output_dir / "generated_prompt_gemini.txt"
        with open(prompt_file, 'w') as f:
            f.write(self.generated_template)
        logger.info(f"Saved generated prompt to {prompt_file}")

        # Phase 2: Process data using the generated prompt
        data_path = Path(data_dir)
        results = {}

        table_s1_path = data_path / "Table S.I \u2013 (5\u00d75) Messages from B - Table S.I \u2013 (5\u00d75) Messages from B.csv"
        if table_s1_path.exists():
            df_s1 = self.process_csv_file(str(table_s1_path))
            if not df_s1.empty:
                results['table_s1_results'] = self.process_table_s1(df_s1)

        table_s2_path = data_path / "Table S.II \u2013 (7\u00d77) Messages from B - Table S.II \u2013 (7\u00d77) Messages from B.csv"
        if table_s2_path.exists():
            df_s2 = self.process_csv_file(str(table_s2_path))
            if not df_s2.empty:
                results['table_s2_results'] = self.process_table_s2(df_s2)

        self.save_results(results)
        logger.info("Full replication completed")
        return results

    def save_results(self, results: Dict[str, pd.DataFrame]):
        self.output_dir.mkdir(parents=True, exist_ok=True)

        all_results = []
        for name, df in results.items():
            if not df.empty:
                all_results.append(df)

        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            output_file = self.output_dir / "gemini_classifications.csv"
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved all results to {output_file}")


def main():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        return

    test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
    if test_mode:
        print("TEST MODE ENABLED - Processing only 5 random rows per table")

    replicator = GeminiCodingReplication(api_key, test_mode=test_mode)

    try:
        results = replicator.run_full_replication()
        print("\nReplication completed successfully!")
        print("Results saved to results/gemini_classifications.csv")
    except Exception as e:
        logger.error(f"Error during replication: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

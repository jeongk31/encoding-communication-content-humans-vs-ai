#!/usr/bin/env python3
"""
DeepSeek Coding Replication Script - PROMPT GENERATION VERSION
Replicates the human coding exercise using DeepSeek API for the
Legitimacy, Communication, and Leadership in the Turnaround Game experiment.

Phase 1: The LLM reads the experimental + coding instructions and generates its own reusable prompt template.
Phase 2: The generated template is used to classify each message.

TEST MODE:
export TEST_MODE=true
python deepseek_coding_replication.py
"""

import os
import pandas as pd
import json
import time
import requests
from pathlib import Path
from typing import Dict
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, using system environment variables")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DeepSeekCodingReplication:
    def __init__(self, api_key: str, test_mode: bool = False):
        self.api_key = api_key
        self.test_mode = test_mode
        self.api_url = "https://api.deepseek.com/v1/chat/completions"

        self.categories = [
            'cat_1a_suggested_effort_0',
            'cat_1b_suggested_effort_10',
            'cat_1c_suggested_effort_20',
            'cat_1d_suggested_effort_30',
            'cat_1e_suggested_effort_40',
            'cat_1f_ambiguous_suggestion',
            'cat_2_explanation_for_effort',
            'cat_3_trust_statements',
            'cat_4_positive_feedback',
            'cat_5_negative_feedback',
            'cat_6_social_banter'
        ]

        # EXPERIMENTAL INSTRUCTIONS (from experimental_instructions.docx)
        self.experimental_instructions = """
EXPERIMENTAL INSTRUCTIONS:
===========================

STAGE 2

Parts, Rounds, and Firms: Stage II of the experiment will have two parts. In the first part there are 6 rounds and in the second part there are 12 rounds.

For the remainder of this experiment you will be randomly assigned to a firm consisting of five participants. You will be grouped with the same four other participants for all 18 rounds.

The following instructions are for the first part of Stage II -- the first six rounds. You will receive instructions about any changes to the rules prior to the start of the second part of Stage II.

Task: There are five employees in each firm. Each round of the experiment can be thought of as a workweek. Each of the five employees spends 40 hours per week at their firm. In each round, there will be a bonus rate for all employees.

After seeing the bonus rate, each employee has to choose how to allocate his or her time between two activities, Activity A and Activity B. Specifically, each employee will be asked to choose how much time to devote to Activity A. The available choices are 0 hours, 10 hours, 20 hours, 30 hours, and 40 hours. That employee's remaining hours will be put towards Activity B. For example, if an employee devotes 30 hours to Activity A, this means that 10 hours will be put towards Activity B. Weekly payoffs for employees depend on a bonus rate and on the number of hours allocated to Activity A by the employees.

Employee Payoffs: The payoff for an employee of the firm is determined in each round by the bonus rate (B), how many hours that employee spends on activity A, and the minimum number of hours employees in his or her firm spend on Activity A. The employee's payoff is reduced by 5 ECUs per hour that he or she spends on Activity A. The employee also receives the bonus rate multiplied by the minimum number of hours any employee in his or her firm spends on Activity A. Each employee also automatically gets a flat payoff of 200 ECUs in each round.

For example, suppose an employee spends 10 hours on Activity A. Suppose the other three workers in his or her firm spend 20, 40 and 40 hours and the bonus rate equals 8. The minimum hours spent on Activity A is 10 hours. The employee's payoff equals 200 - 5*10 + 8*10 = 230 ECUs.

Firm Managers: In the second part of Stage II (Rounds 7 - 18), there will be a firm manager. The manager will be selected from among the five employees in the firm. Each firm will have five employees who perform the same task as in the first part of Stage II. However, one employee will also now serve as the firm manager. For the remainder of the experiment, one of the five people in your firm will be the manager. The manager will always be the same person.

At the beginning of each round, the manager will be able to type a message to the other employees in his or her firm. Except for the following restrictions, the manager may type whatever he or she wants.

Restrictions on Messages:
1. Please do not identify yourself or send any information that could be used to identify you (e.g. age, race, gender, etc.).
2. Please refrain from using obscene or offensive language.
"""

        # CODING INSTRUCTIONS - NO EXAMPLES VERSION (from Coding Instructions.docx, examples removed)
        self.coding_instructions = """
CODING INSTRUCTIONS:
====================

All sessions have 18 periods. Subjects are in fixed groups of five playing a weaklink game in each round. Each player chooses an effort in each period from 5 possible choices (0,10,20,30,40). The group outcome is determined by the minimum effort chosen by a group member. The Pareto dominant equilibrium is for everyone to choose 40, but this is risky. The experiment revolves around seeing what gets them to the efficient outcome.

What we need you to do is code the messages that managers sent. Please mark a 1 for any comment that you think fits the category. You can code more than one category per message. Here are categories:

Suggested effort level:
- cat_1a_suggested_effort_0: Suggests choosing 0 hours
- cat_1b_suggested_effort_10: Suggests choosing 10 hours
- cat_1c_suggested_effort_20: Suggests choosing 20 hours
- cat_1d_suggested_effort_30: Suggests choosing 30 hours
- cat_1e_suggested_effort_40: Suggests choosing 40 hours
- cat_1f_ambiguous_suggestion: Ambiguous suggestion - positive about effort but not specific about a number

cat_2_explanation_for_effort: Provided an explanation for choosing suggested effort

cat_3_trust_statements: Statements about needing to trust each other

cat_4_positive_feedback: Positive feedback about previous outcome

cat_5_negative_feedback: Negative feedback about previous outcome

cat_6_social_banter: Social banter \u2013 friendly chatter not directly related to the game
"""

        self.generated_template = None

    def generate_coding_prompt(self):
        """Phase 1: Ask the LLM to generate its own coding prompt template."""
        logger.info("Phase 1: Generating coding prompt template from DeepSeek...")

        json_template = json.dumps({cat: 0 for cat in self.categories}, indent=4)

        meta_prompt = f"""You are a research assistant. Below are the experimental instructions and coding instructions for a weak-link coordination game experiment ("Legitimacy, Communication, and Leadership in the Turnaround Game"). Your task is to read and internalize these instructions, then generate a single reusable prompt template that will be used to code manager messages from this experiment.

=== EXPERIMENTAL INSTRUCTIONS ===
{self.experimental_instructions}

=== CODING INSTRUCTIONS ===
{self.coding_instructions}

=== YOUR TASK ===
Based on the above instructions, generate a single, self-contained prompt template that can be reused to code any manager message from this experiment. The template must:

1. Contain all necessary context about the experiment and coding categories so that a coder (or AI) can understand the task without seeing the original instructions
2. Include these EXACT placeholders (with curly braces) that will be filled in for each message:
   - {{message}} — the actual manager message text to code
   - {{period_context}} — context about which period this message is from
   - {{json_template}} — the JSON structure to fill in with 0/1 values
3. Instruct the coder to return ONLY a JSON object with binary 0 or 1 values for each category
4. Clearly explain ALL 11 coding categories (suggested effort levels 0-40, ambiguous suggestion, explanation for effort, trust statements, positive feedback, negative feedback, social banter)
5. Explain that multiple categories can be coded 1 for a single message
6. Explain the experimental setup: weak-link game, 5 employees per firm, effort choices 0/10/20/30/40, payoffs determined by minimum effort

Return ONLY the prompt template text, nothing else. Do not wrap it in quotes or code blocks."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a research assistant helping to create coding prompts for experimental data analysis."},
                {"role": "user", "content": meta_prompt}
            ],
            "temperature": 0
        }

        for attempt in range(3):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
                generated_prompt = response_data['choices'][0]['message']['content'].strip()
                logger.info(f"Generated prompt template ({len(generated_prompt)} chars)")
                self.generated_template = generated_prompt
                return generated_prompt
            except Exception as e:
                logger.error(f"Prompt generation attempt {attempt + 1} failed: {str(e)}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        raise RuntimeError("Failed to generate coding prompt template after 3 attempts")

    def classify_message(self, message: str, period: int = None) -> Dict[str, int]:
        try:
            message_str = str(message) if not pd.isna(message) else ""
            if not message_str or message_str.strip() == "" or message_str.lower() == 'nan':
                return {cat: 0 for cat in self.categories}

            period_context = ""
            if period:
                period_context = f"This message is from Period {period} of the experiment."

            json_template = json.dumps({cat: 0 for cat in self.categories}, indent=4)

            # Fill in the generated template
            prompt = self.generated_template.replace('{message}', message_str)
            prompt = prompt.replace('{period_context}', period_context)
            prompt = prompt.replace('{json_template}', json_template)

            # Print what we're sending to the LLM
            print("\n" + "=" * 80)
            print("SENDING TO LLM:")
            print("=" * 80)
            print(f"\n[SYSTEM MESSAGE]:\nYou are an expert coder for economic experiment messages. Always respond with valid JSON.")
            print(f"\n[USER PROMPT]:\n{prompt}")
            print("=" * 80)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert coder for economic experiment messages. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0,
                "max_tokens": 500
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content']

            # Print what we received from the LLM
            print("\n[LLM RESPONSE]:")
            print(response_text)
            print("=" * 80)

            result = self._parse_response(response_text)

            # Print parsed result
            print(f"\n[PARSED RESULT]: {result}")
            print("=" * 80 + "\n")

            return result

        except Exception as e:
            logger.error(f"Error classifying message: {e}")
            return {cat: 0 for cat in self.categories}

    def _parse_response(self, response_text: str) -> Dict[str, int]:
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)

                parsed = {}
                for cat in self.categories:
                    val = result.get(cat, 0)
                    parsed[cat] = 1 if val == 1 or val == "1" or val is True else 0

                return parsed
            else:
                logger.warning(f"Could not find JSON in response: {response_text[:100]}")
                return {cat: 0 for cat in self.categories}

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return {cat: 0 for cat in self.categories}

    def process_data(self, data_path: str) -> pd.DataFrame:
        logger.info(f"Loading data from {data_path}")

        df = pd.read_csv(data_path)
        logger.info(f"Loaded {len(df)} rows")

        if self.test_mode:
            df = df.head(10).copy()
            logger.info(f"TEST MODE: Processing only {len(df)} rows")

        message_col = 't'
        logger.info(f"Using message column: {message_col}")

        for cat in self.categories:
            df[cat] = 0

        total = len(df)
        for idx, row in df.iterrows():
            message = row[message_col]
            period = row.get('Period', None)

            coding = self.classify_message(message, period)

            for cat, val in coding.items():
                df.at[idx, cat] = val

            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{total} messages")

            time.sleep(0.3)

        return df

    def run_replication(self, data_dir: str = "../data collection", output_dir: str = None) -> pd.DataFrame:
        logger.info("Starting DeepSeek coding replication (PROMPT GENERATION version)")

        self.output_dir = Path(output_dir or os.getenv('OUTPUT_DIR', 'results'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Phase 1: Generate the coding prompt template
        self.generate_coding_prompt()

        # Save the generated prompt for inspection
        prompt_file = self.output_dir / "generated_prompt_deepseek.txt"
        with open(prompt_file, 'w') as f:
            f.write(self.generated_template)
        logger.info(f"Saved generated prompt to {prompt_file}")

        # Phase 2: Process data using the generated prompt
        data_path = Path(data_dir)
        data_file = data_path / "data_encoding_template.csv"

        if not data_file.exists():
            alt_paths = [
                Path("../data collection/data_encoding_template.csv"),
                Path("data_encoding_template.csv"),
            ]
            for alt in alt_paths:
                if alt.exists():
                    data_file = alt
                    break
            else:
                csv_files = list(data_path.glob("*.csv"))
                if csv_files:
                    data_file = csv_files[0]
                else:
                    raise FileNotFoundError(f"No data file found in {data_dir}")

        logger.info(f"Using data file: {data_file}")
        results_df = self.process_data(str(data_file))
        self.save_results(results_df)
        logger.info("Replication completed")
        return results_df

    def save_results(self, df: pd.DataFrame):
        self.output_dir.mkdir(parents=True, exist_ok=True)

        csv_path = self.output_dir / "deepseek_classifications_no_examples.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved results to {csv_path}")

        try:
            dta_path = self.output_dir / "deepseek_classifications_no_examples.dta"
            df.to_stata(dta_path, write_index=False)
            logger.info(f"Saved Stata file to {dta_path}")
        except Exception as e:
            logger.warning(f"Could not save Stata file: {e}")

        print("\n=== CODING SUMMARY ===")
        for cat in self.categories:
            count = df[cat].sum()
            pct = (count / len(df)) * 100
            print(f"{cat}: {count} ({pct:.1f}%)")


def main():
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        return

    test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
    if test_mode:
        print("TEST MODE ENABLED - Processing only first 10 rows")

    replicator = DeepSeekCodingReplication(api_key, test_mode=test_mode)

    try:
        results = replicator.run_replication()
        print("\nReplication completed successfully!")
        print(f"Results saved to results/deepseek_classifications_no_examples.csv")
    except Exception as e:
        logger.error(f"Error during replication: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

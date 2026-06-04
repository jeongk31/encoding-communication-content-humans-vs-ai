#!/usr/bin/env python3
"""
DeepSeek Coding Replication Script - CONTEXT VERSION
Replicates the human coding exercise using DeepSeek API for the
Legitimacy, Communication, and Leadership in the Turnaround Game experiment.

This version sends all chatgroups for each period together, allowing the LLM
to understand context when messages reference previous messages (e.g., "do the same as before").

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
from typing import Dict, List, Tuple
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

cat_6_social_banter: Social banter – friendly chatter not directly related to the game
"""

    def classify_period_messages(self, period_data: List[Tuple[int, str]], session: int, period: int) -> Dict[int, Dict[str, int]]:
        """
        Classify all chatgroup messages for a given period together.

        Args:
            period_data: List of tuples (chatgroup_id, message)
            session: Session number
            period: Period number

        Returns:
            Dictionary mapping chatgroup_id to classification results
        """
        try:
            # Filter out empty messages
            valid_messages = []
            for chatgroup, message in period_data:
                message_str = str(message) if not pd.isna(message) else ""
                if message_str and message_str.strip() != "" and message_str.lower() != 'nan':
                    valid_messages.append((chatgroup, message_str))

            if not valid_messages:
                return {cg: {cat: 0 for cat in self.categories} for cg, _ in period_data}

            # Build the combined message block
            messages_block = ""
            for chatgroup, message in valid_messages:
                messages_block += f"[chatgroup {chatgroup}]\n{message}\n\n"

            prompt = f"""
{self.experimental_instructions}

{self.coding_instructions}

CONTEXT: This is Session {session}, Period {period} of the experiment.

Below are ALL the manager messages from different chatgroups in this period. Some messages may reference previous messages (e.g., "do the same as before", "again", "same thing"). When coding such messages, consider what the previous chatgroup messages suggested.

MESSAGES TO CODE:
{messages_block}

For EACH chatgroup, provide the classification. Respond with a JSON object where keys are chatgroup IDs and values are the category codes:

{{
    "chatgroup_X": {{
        "cat_1a_suggested_effort_0": 0,
        "cat_1b_suggested_effort_10": 0,
        "cat_1c_suggested_effort_20": 0,
        "cat_1d_suggested_effort_30": 0,
        "cat_1e_suggested_effort_40": 0,
        "cat_1f_ambiguous_suggestion": 0,
        "cat_2_explanation_for_effort": 0,
        "cat_3_trust_statements": 0,
        "cat_4_positive_feedback": 0,
        "cat_5_negative_feedback": 0,
        "cat_6_social_banter": 0
    }},
    ...
}}

IMPORTANT:
- Code EACH chatgroup separately
- If a message says "again", "same as before", "do the same", etc., look at what previous chatgroups in this period suggested and code accordingly
- Return labels for chatgroups: {[cg for cg, _ in valid_messages]}
"""

            # Print what we're sending to the LLM
            print("\n" + "=" * 80)
            print(f"SENDING TO LLM (Session {session}, Period {period}):")
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
                "max_tokens": 2000
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content']

            # Print what we received from the LLM
            print("\n[LLM RESPONSE]:")
            print(response_text)
            print("=" * 80)

            result = self._parse_period_response(response_text, [cg for cg, _ in valid_messages])

            # Print parsed result
            print(f"\n[PARSED RESULT]: {result}")
            print("=" * 80 + "\n")

            # Fill in empty results for any chatgroups that weren't in valid_messages
            all_chatgroups = {cg for cg, _ in period_data}
            for cg in all_chatgroups:
                if cg not in result:
                    result[cg] = {cat: 0 for cat in self.categories}

            return result

        except Exception as e:
            logger.error(f"Error classifying period messages: {e}")
            return {cg: {cat: 0 for cat in self.categories} for cg, _ in period_data}

    def _parse_period_response(self, response_text: str, chatgroups: List[int]) -> Dict[int, Dict[str, int]]:
        """Parse the LLM response for multiple chatgroups."""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)

                parsed = {}
                for cg in chatgroups:
                    # Try different key formats
                    cg_key = None
                    for possible_key in [f"chatgroup_{cg}", f"chatgroup {cg}", str(cg), cg]:
                        if possible_key in result:
                            cg_key = possible_key
                            break

                    if cg_key and isinstance(result[cg_key], dict):
                        cg_result = result[cg_key]
                        parsed[cg] = {}
                        for cat in self.categories:
                            val = cg_result.get(cat, 0)
                            parsed[cg][cat] = 1 if val == 1 or val == "1" or val is True else 0
                    else:
                        parsed[cg] = {cat: 0 for cat in self.categories}

                return parsed
            else:
                logger.warning(f"Could not find JSON in response: {response_text[:100]}")
                return {cg: {cat: 0 for cat in self.categories} for cg in chatgroups}

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return {cg: {cat: 0 for cat in self.categories} for cg in chatgroups}

    def process_data(self, data_path: str) -> pd.DataFrame:
        logger.info(f"Loading data from {data_path}")

        df = pd.read_csv(data_path)
        logger.info(f"Loaded {len(df)} rows")

        # Initialize category columns
        for cat in self.categories:
            df[cat] = 0

        message_col = 't'
        logger.info(f"Using message column: {message_col}")

        # Group by session and period
        grouped = df.groupby(['session', 'Period'])

        total_groups = len(grouped)
        processed = 0

        if self.test_mode:
            # In test mode, only process first 2 session-period combinations
            test_limit = 2
            processed_count = 0

        for (session, period), group in grouped:
            if self.test_mode and processed_count >= test_limit:
                break

            logger.info(f"Processing Session {session}, Period {period} ({len(group)} messages)")

            # Collect all chatgroup messages for this period
            period_data = []
            row_indices = []
            for idx, row in group.iterrows():
                chatgroup = row['chatGroup']
                message = row[message_col]
                period_data.append((chatgroup, message))
                row_indices.append(idx)

            # Classify all messages together
            classifications = self.classify_period_messages(period_data, session, period)

            # Apply classifications back to dataframe
            for i, idx in enumerate(row_indices):
                chatgroup = period_data[i][0]
                if chatgroup in classifications:
                    for cat, val in classifications[chatgroup].items():
                        df.at[idx, cat] = val

            processed += 1
            if self.test_mode:
                processed_count += 1

            logger.info(f"Processed {processed}/{total_groups} session-period groups")

            # Rate limiting
            time.sleep(0.5)

        return df

    def run_replication(self, data_dir: str = "../data collection") -> pd.DataFrame:
        logger.info("Starting DeepSeek coding replication (CONTEXT version)")

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
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)

        # Save as the labeled version of data_encoding_template
        csv_path = output_dir / "deepseek_labeled_data.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved results to {csv_path}")

        try:
            dta_path = output_dir / "deepseek_labeled_data.dta"
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
        print("TEST MODE ENABLED - Processing only first 2 session-period groups")

    replicator = DeepSeekCodingReplication(api_key, test_mode=test_mode)

    try:
        results = replicator.run_replication()
        print("\nReplication completed successfully!")
        print(f"Results saved to results/deepseek_labeled_data.csv")
    except Exception as e:
        logger.error(f"Error during replication: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

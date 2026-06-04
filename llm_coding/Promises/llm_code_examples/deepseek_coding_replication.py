#!/usr/bin/env python3
"""
DeepSeek Coding Replication Script
Replicates the human coding exercise using DeepSeek API for the Promises and Partnerships experiment data.

This script processes all CSV files and Excel files in the Data directory and uses DeepSeek to classify
messages and replicate the human coding exercise.

TEST MODE:
To run in test mode (process only 5 random rows per table with full input/output printing):
export TEST_MODE=true
python deepseek_coding_replication.py

To run full replication:
export TEST_MODE=false  # or unset the variable
python deepseek_coding_replication.py
"""

import os
import pandas as pd
import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
    print("   Install with: pip install python-dotenv")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeepSeekCodingReplication:
    def __init__(self, api_key: str, test_mode: bool = False):
        """
        Initialize the DeepSeek coding replication system.
        
        Args:
            api_key (str): DeepSeek API key
            test_mode (bool): If True, only process 5 random rows and print full input/output
        """
        self.api_key = api_key
        self.test_mode = test_mode
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
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
The message explicitly states an intention to choose "Roll" (i.e. to cooperate) if player A chooses "In". This includes direct promises, commitments, or statements of intended action.
    Example of YES (P): "I will choose roll."
    Example of NO (not P): "Please choose In so we can get paid more."

2. Empty Talk (E)
The message does not express any promise or intention to Roll. This includes greetings, good luck wishes, jokes, general thoughts, comments irrelevant to the game decision, or messages expressing uncertainty about their intended action.
    Example of YES (E): "Please choose In so we can get paid more."
    Example of NO (not E): "I will choose roll."

3. No Message (N)
No message was sent (blank or opted out). This category applies when Player B had the option to send a message but explicitly declined to do so.
    Example of YES (N): [BLANK/EMPTY MESSAGE]
    Example of NO (not N): "Hello!"

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
        
        # Store results
        self.results = {}
        
    def process_csv_file(self, file_path: str) -> pd.DataFrame:
        """
        Process a CSV file and return the data.
        
        Args:
            file_path (str): Path to the CSV file
            
        Returns:
            pd.DataFrame: Processed data
        """
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Successfully loaded {file_path} with {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
    
    def process_excel_file(self, file_path: str) -> pd.DataFrame:
        """
        Process an Excel file and return the data.
        
        Args:
            file_path (str): Path to the Excel file
            
        Returns:
            pd.DataFrame: Processed data
        """
        try:
            df = pd.read_excel(file_path)
            logger.info(f"Successfully loaded {file_path} with {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
    
    def classify_message_with_deepseek(self, message: str, context: str = "") -> Dict[str, Any]:
        """
        Use DeepSeek to classify a message.
        
        Args:
            message (str): The message to classify
            context (str): Additional context about the message
            
        Returns:
            Dict[str, Any]: Classification results
        """
        try:
            # Convert to string and handle NaN values
            message_str = str(message) if not pd.isna(message) else ""
            if not message_str or message_str.strip() == "" or message_str.lower() == 'nan':
                prompt = f"""
                {self.experimental_instructions}

                {self.coding_instructions}

                Message to classify: [NO MESSAGE/EMPTY]
                Context: {context}

                Classify this message.
                """
            else:
                prompt = f"""
                {self.experimental_instructions}

                {self.coding_instructions}

                Message to classify: "{message_str}"
                Context: {context}

                Classify this message.
                """
            
            # Prepare the API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a coding assistant for message classification."},
                    {"role": "user", "content": prompt}
                ],
            }
            
            # Generate response
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content']
            
            # Try to parse JSON response
            try:
                # Extract JSON from response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                else:
                    # Fallback: try to extract classification from text
                    result = self._extract_classification_from_text(response_text)
                
                # Print simple progress in test mode
                if self.test_mode:
                    print(f"Processed: {result['classification']}")
                
                return result
                
            except json.JSONDecodeError:
                # Fallback parsing
                result = self._extract_classification_from_text(response_text)
                
                # Print simple progress in test mode
                if self.test_mode:
                    print(f"Processed: {result['classification']}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error classifying message with DeepSeek: {e}")
            return {
                "classification": "ERROR",
                "explanation": f"Error: {str(e)}",
                "confidence": 0
            }
    
    def _extract_classification_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract classification from DeepSeek's text response when JSON parsing fails.

        Args:
            text (str): DeepSeek's response text

        Returns:
            Dict[str, Any]: Extracted classification
        """
        text_lower = text.lower()

        # Look for classification indicators (order matters - check most specific first)
        if "no message" in text_lower or text_lower.strip() == "n":
            classification = "N"
        elif "promise" in text_lower:
            classification = "P"
        elif "empty talk" in text_lower:
            classification = "E"
        else:
            classification = "UNKNOWN"
        
        # Try to extract confidence
        confidence = 5  # Default
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
    
    def process_table_s1(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process Table S.I (5×5 Messages from B).
        
        Args:
            df (pd.DataFrame): Input dataframe
            
        Returns:
            pd.DataFrame: Processed dataframe with DeepSeek classifications
        """
        logger.info("Processing Table S.I (5×5 Messages from B)")
        
        # In test mode, select only first 5 rows
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
            
            # Create context for DeepSeek
            context = f"Session {session}, Player ID {player_id}, Player A chose {choice_a}, Player B chose {choice_b}, Human classified as: {human_class}"
            
            # Classify with DeepSeek
            deepseek_result = self.classify_message_with_deepseek(message, context)
            
            # Store results (matching original format)
            result_row = {
                'Sess': session,
                'ID': player_id,
                'Message': message,
                'Class': deepseek_result['classification']
            }
            
            results.append(result_row)
            
            # Add delay to avoid rate limiting
            time.sleep(0.5)
            
            # Log progress
            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(df)} rows from Table S.I")
        
        return pd.DataFrame(results)
    
    def process_table_s2(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process Table S.II (7×7 Messages from B).
        
        Args:
            df (pd.DataFrame): Input dataframe
            
        Returns:
            pd.DataFrame: Processed dataframe with DeepSeek classifications
        """
        logger.info("Processing Table S.II (7×7 Messages from B)")
        
        # In test mode, select only first 5 rows
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
            
            # Create context for DeepSeek
            context = f"Session {session}, Player ID {player_id}, Player A chose {choice_a}, Player B chose {choice_b}, Human classified as: {human_class}, 7×7 payoff matrix"
            
            # Classify with DeepSeek
            deepseek_result = self.classify_message_with_deepseek(message, context)
            
            # Store results (matching original format)
            result_row = {
                'Sess': session,
                'ID': player_id,
                'Message': message,
                'Class': deepseek_result['classification']
            }
            
            results.append(result_row)
            
            # Add delay to avoid rate limiting
            time.sleep(0.5)
            
            # Log progress
            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(df)} rows from Table S.II")
        
        return pd.DataFrame(results)
    
    def process_table_s3(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process Table S.III (5×5 Messages from A).
        
        Args:
            df (pd.DataFrame): Input dataframe
            
        Returns:
            pd.DataFrame: Processed dataframe with DeepSeek classifications
        """
        logger.info("Processing Table S.III (5×5 Messages from A)")
        
        # In test mode, select only first 5 rows
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
            
            # Create context for DeepSeek
            context = f"Session {session}, Player ID {player_id}, Player A chose {choice_a}, Player B chose {choice_b}, Message is from Player A (not B)"
            
            # Classify with DeepSeek
            deepseek_result = self.classify_message_with_deepseek(message, context)
            
            # Store results (matching original format)
            result_row = {
                'Sess': session,
                'ID': player_id,
                'Message': message,
                'Class': deepseek_result['classification']
            }
            
            results.append(result_row)
            
            # Add delay to avoid rate limiting
            time.sleep(0.5)
            
            # Log progress
            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(df)} rows from Table S.III")
        
        return pd.DataFrame(results)
    
    def process_excel_data(self, agent_file: str, principal_file: str) -> Dict[str, pd.DataFrame]:
        """
        Process the Excel data files.
        
        Args:
            agent_file (str): Path to agent data file
            principal_file (str): Path to principal data file
            
        Returns:
            Dict[str, pd.DataFrame]: Processed dataframes
        """
        logger.info("Processing Excel data files")
        
        # Load data
        agent_df = self.process_excel_file(agent_file)
        principal_df = self.process_excel_file(principal_file)
        
        # Process agent messages if they exist
        agent_results = []
        if 'agent_message' in agent_df.columns and 'Sent_message' in agent_df.columns:
            # In test mode, limit to first 5 messages
            if self.test_mode:
                message_rows = agent_df[agent_df['Sent_message'] == 1].head(5)
                logger.info(f"TEST MODE: Processing only first {len(message_rows)} agent messages")
            else:
                message_rows = agent_df[agent_df['Sent_message'] == 1]
            
            for idx, row in message_rows.iterrows():
                if row['Sent_message'] == 1:  # Only process rows with messages
                    agent_id = row['Agent']
                    message = row.get('agent_message', '')
                    
                    # Find corresponding principal data
                    principal_row = principal_df[principal_df['Principal'] == agent_id]
                    if not principal_row.empty:
                        choice_in = principal_row.iloc[0]['IN']
                        choice_roll = row['ROLL']
                        
                        context = f"Agent {agent_id}, Player A chose IN={choice_in}, Player B chose ROLL={choice_roll}"
                        deepseek_result = self.classify_message_with_deepseek(message, context)
                        
                        result_row = {
                            'Sess': agent_id,
                            'ID': agent_id,
                            'Message': message,
                            'Class': deepseek_result['classification']
                        }
                        
                        agent_results.append(result_row)
                        
                        time.sleep(0.5)
        
        # Process principal messages if they exist
        principal_results = []
        if 'principal_message' in principal_df.columns and 'Received_message' in principal_df.columns:
            # In test mode, limit to first 5 messages
            if self.test_mode:
                message_rows = principal_df[principal_df['Received_message'] == 1].head(5)
                logger.info(f"TEST MODE: Processing only first {len(message_rows)} principal messages")
            else:
                message_rows = principal_df[principal_df['Received_message'] == 1]
            
            for idx, row in message_rows.iterrows():
                if row['Received_message'] == 1:  # Only process rows with messages
                    principal_id = row['Principal']
                    message = row.get('principal_message', '')
                    
                    # Find corresponding agent data
                    agent_row = agent_df[agent_df['Agent'] == principal_id]
                    if not agent_row.empty:
                        choice_in = row['IN']
                        choice_roll = agent_row.iloc[0]['ROLL']
                        
                        context = f"Principal {principal_id}, Player A chose IN={choice_in}, Player B chose ROLL={choice_roll}"
                        deepseek_result = self.classify_message_with_deepseek(message, context)
                        
                        result_row = {
                            'Sess': principal_id,
                            'ID': principal_id,
                            'Message': message,
                            'Class': deepseek_result['classification']
                        }
                        
                        principal_results.append(result_row)
                        
                        time.sleep(0.5)
        
        return {
            'agent_messages': pd.DataFrame(agent_results),
            'principal_messages': pd.DataFrame(principal_results)
        }
    
    def run_full_replication(self, data_dir: str = "../Data") -> Dict[str, pd.DataFrame]:
        """
        Run the full replication for all data files.
        
        Args:
            data_dir (str): Directory containing the data files
            
        Returns:
            Dict[str, pd.DataFrame]: All results
        """
        logger.info("Starting full DeepSeek coding replication")
        
        data_path = Path(data_dir)
        
        # Process CSV files
        csv_files = list(data_path.glob("*.csv"))
        excel_files = list(data_path.glob("*.xls")) + list(data_path.glob("*.xlsx"))
        
        results = {}
        
        # Process Table S.I
        table_s1_path = data_path / "Table S.I – (5×5) Messages from B - Table S.I – (5×5) Messages from B.csv"
        if table_s1_path.exists():
            df_s1 = self.process_csv_file(str(table_s1_path))
            if not df_s1.empty:
                results['table_s1_results'] = self.process_table_s1(df_s1)
        
        # Process Table S.II
        table_s2_path = data_path / "Table S.II – (7×7) Messages from B - Table S.II – (7×7) Messages from B.csv"
        if table_s2_path.exists():
            df_s2 = self.process_csv_file(str(table_s2_path))
            if not df_s2.empty:
                results['table_s2_results'] = self.process_table_s2(df_s2)

        # Save all results
        self.save_results(results)
        
        logger.info("Full replication completed")
        return results
    
    def save_results(self, results: Dict[str, pd.DataFrame]):
        """
        Save all results to a single CSV file matching human coder format.
        
        Args:
            results (Dict[str, pd.DataFrame]): Results to save
        """
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        
        # Combine all results into one dataframe
        all_results = []
        
        for name, df in results.items():
            if not df.empty:
                all_results.append(df)
        
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            
            # Save as single CSV file with exact same format as human coding
            output_file = output_dir / "deepseek_classifications.csv"
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved all results to {output_file}")

def main():
    """
    Main function to run the DeepSeek coding replication.
    """
    # Check if API key is provided
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        print("Please set your DeepSeek API key:")
        print("export DEEPSEEK_API_KEY='your_api_key_here'")
        return
    
    # Check if test mode is enabled
    test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
    if test_mode:
        print("🧪 TEST MODE ENABLED - Processing only 5 random rows per table")
        print("Set TEST_MODE=false to run full replication")
    
    # Initialize the replication system
    replicator = DeepSeekCodingReplication(api_key, test_mode=test_mode)
    
    # Run the full replication
    try:
        results = replicator.run_full_replication()
        
        print("\nReplication completed successfully!")
        print("Results saved to results/deepseek_classifications.csv")
        
    except Exception as e:
        logger.error(f"Error during replication: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()


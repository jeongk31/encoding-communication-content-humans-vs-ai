import csv
import os
import time
import json
import re
import logging
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURATION - MODIFY THESE SETTINGS
# =====================================================
TEST_MODE = False   # Set to True to process only first 5 rows
MAX_ROWS = 5 if TEST_MODE else None
# =====================================================

from openai import OpenAI

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
TEMPLATE_FILE = os.path.join(PROJECT_DIR, "Data", "encoding template", "coding_template.csv")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

# Coding columns we need to fill
CODING_PREFIXES = ('All_way_split', 'MWC', 'Compete', 'Future_coalition')

# =====================================================
# EXPERIMENTAL INSTRUCTIONS (from Experimental Instructions.pdf - verbatim)
# =====================================================
EXPERIMENTAL_INSTRUCTIONS = """Experiment Instructions
This is an experiment in the economics of decision making. We follow a no-deception ethical policy at the Economics Lab, hence these instructions fully describe the experiment.

A Brief Overview of the Experiment

In this experiment you will be part of a group of 3 people. One of you will be asked to propose a distribution of $30 among the members of your group. Group members will be able to communicate with each other through chat screens. Proposals are voted up or down according to the simple majority rule. In case the current proposal is rejected, the members of the same group proceed to another proposal and voting round until one allocation is approved. The details of the experiment follow.

The Details of the Experiment

As expressed above, this experiment involves three main components: (1) chat, (2) proposal, and (3) vote. We proceed to fully explain each of them.

(1) Chat
The computer will randomly choose one of you to be the proposer of a distribution of $30. Before a proposal is made, you will have up to three minutes during which time you can exchange written messages with the other two members of your group. Messages can be sent to each member of your group individually through a private chat screen and also collectively through a public chat screen which the other two members can see. The chat screen will remain open during both proposing and voting stages of bargaining, explained below. We ask that you please be respectful of others and do not reveal your identity or personal information while chatting.

(2) Proposal
In this stage the proposer submits a division of the $30.

(3) Voting
You will observe how much the proposer assigned to each member of the group. You can then click "accept" or "reject". For approval, the proposal requires a simple majority (at least 2 votes). The proposer will automatically be counted as a voting in favor.

If rejected: every member in your group will proceed to stage (2) with a member randomly selected as proposer. Feedback on the previous proposal, the voting result, and who was the proposer will be given to you.

The process repeats itself until an allocation of the total fund is approved.

If approved: the result will be binding. Next, you will then be matched into new groups to repeat the stages (1)-(3). You will participate in a total of 15 periods. In each period, you will be randomly reassigned into a group of 3 people, with your subject number for each period determined randomly as well. Thus, while your subject number will remain the same for all rounds within a given period, it will change across periods: in period 1 you can be subject 3, and in period 2 you can be subject 1.

Your Earnings
Only 2 of the 15 periods will be randomly selected to count for payment. Your earnings (E) are then given by the shares you received in those periods plus the show up fee of $10.

Example.
Below, we provide an example for you to understand how the payoffs of the experiment work.

Consider a 3 person group with $30 to divide. The proposer allocates $8 to subject 1, $5 to herself, and $17 to subject 2. If Subject 1 votes in favor and Subject 2 against (the proposer is automatically counted in favor), then the proposal is approved. The payments subjects would receive if this period was selected for payment are the offered shares in the approved proposal. Note however that votes could have been different in which case a new round would take place.

Review of the experiment

1. Everyone is randomly assigned into groups of 3
2. There are $30 to divide.
3. One of you will be randomly chosen as the proposer.
4. You will have up to three minutes to chat while the proposer enters a division of the money and up to three minutes to chat while a voting decision is reached.
5. Be respectful and do not reveal any personal information while chatting.
6. Once a proposal is made, voting will take place. If a majority accepts, the allocation is binding, and you will wait in standby until the other groups in your session decide on an allocation.
7. If a majority rejects, the process repeats itself until a given allocation is accepted.
8. Once an allocation is accepted, you will start a new period with randomly selected members. 2 of the 15 periods of play will be chosen randomly for payment."""

# =====================================================
# CODING INSTRUCTIONS (from Coding Instructions.docx - verbatim)
# =====================================================
CODING_INSTRUCTIONS = """Chat Coding Instructions for Research Assistants

General Description of the Task

You will be reading over conversations between members of a group that were bargaining to divide a given amount of money among themselves. These group members were participants in an experiment that took place between January and April of 2020 in New York University.

In the experiment, one subject of the group was selected to be the person who would divides $30 among himself and two other members. Subjects had up to 3 minutes to chat with the other two members. Proposers had to choose a distribution of the fund and once they did so, the remaining members would proceed to a vote. In some of our experimental sessions, subjects were allowed to keep chatting during the voting stage, while in other sessions this was not allowed. We also conducted sessions where chat only occurred at the voting stage. If a majority approved the proposal, then the proposal was binding. If not, the process would repeat itself until approval. Thus, potentially a same group could negotiate for several rounds.

A copy of the experimental instructions has been given to you. Please read them thoroughly.

Details of the Coding Task

You will be shown the chat transcripts for different groups. Each chat will have three windows, since each person could communicate privately with another member or publicly with all members.

Under each chat window, there will be several categories that you should mark in case it applies to the conversation. The categories are:

All-way split (All_way_split category): whenever a member states that the total fund should be split between all three members, that is, that all members should get something. "I will give everyone something" or members tell the proposer "you should share it with both of us". Calling for a 3-way equal split, $10 for each, is also to be coded here.

Minimum Winning Coalition (MWC category): whenever a proposer mentions that he will only give money to one of the voters. When a voting member explicitly or implicitly tells the proposer that the other member should get zero. Similar phrasing may be used like: "I'm fine with the other person getting 0"; "I don't care if you give money to the other member"; "Let's split us two in half"; "let's go you and I 50-50". "Me 13, you keep the rest".

Competition (Compete category): whenever the proposer tells a voter the amount that the other voter is willing to accept. Also marked if the proposer tells a voter that the other voter is willing to accept less, or that she is looking for the cheapest voter. For voters, whenever he or she asks how much the other one is willing to accept and seeks to undercut or match. "I will take less than the other person" or "I will match the other person".

Future Coalition (Future_coalition category): when non-proposers attempt to strike a deal of a future coalition. "We should reject and next round we split it in half between of ourselves". "We should reject and figure it out between both of us next round" "The proposer is trying to give us a small share, lets reject and divide ourselves".
"""


def init_llm():
    """Initialize the GPT client."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env")
    client = OpenAI(api_key=api_key)
    return client, 'gpt-4o'


IDENTITY_DESC = {
    'p-v1': 'This is a private chat between the Proposer (P) and Voter 1 (V1). Only P and V1 are involved.',
    'p-v2': 'This is a private chat between the Proposer (P) and Voter 2 (V2). Only P and V2 are involved.',
    'v1-v2': 'This is a private chat between Voter 1 (V1) and Voter 2 (V2). Only V1 and V2 are involved.',
    'public': 'This is a public chat visible to all three members: Proposer (P), Voter 1 (V1), and Voter 2 (V2).',
}
IDENTITY_ROLES = {
    'p-v1': ['P', 'V1'],
    'p-v2': ['P', 'V2'],
    'v1-v2': ['V1', 'V2'],
    'public': ['P', 'V1', 'V2'],
}


def build_prompt(chat_text, round_num, identity):
    """Build the coding prompt for a single chat window."""
    identity_desc = IDENTITY_DESC.get(identity, '')
    roles = IDENTITY_ROLES.get(identity, ['P', 'V1', 'V2'])

    # Build JSON keys only for relevant roles
    categories = ['All_way_split', 'MWC', 'Compete', 'Future_coalition']
    json_lines = []
    for cat in categories:
        for role in roles:
            json_lines.append(f'    "{cat}_{role}": 0 or 1')
    json_template = '{\n' + ',\n'.join(json_lines) + '\n}'

    prompt = f"""{EXPERIMENTAL_INSTRUCTIONS}

{CODING_INSTRUCTIONS}

You are now coding a specific chat transcript from one chat window. Each message is labeled with the sender's role.

{identity_desc}

ROLES:
- P = Proposer (the person who proposes the division of $30)
- V1 = Voter 1
- V2 = Voter 2

IMPORTANT: Only code for the participants involved in this chat window. Do NOT assign codes to participants who are not part of this chat.

COLUMN NAMING: Each key follows the pattern {{Category}}_{{Role}}, meaning: "Did {{Role}} express {{Category}} in this chat?" Only look at what that specific person said.

ROUND: {round_num}

CHAT TRANSCRIPT:
{chat_text}

For this chat transcript, code the following categories for each participant present in this chat. Return your response as JSON with this exact structure. Use 0 or 1 for binary categories.

{json_template}

Return ONLY the JSON object, nothing else."""
    return prompt


def call_llm(client_or_model, model_name, prompt, max_retries=3):
    """Call the GPT API with retry logic."""
    for attempt in range(max_retries):
        try:
            if TEST_MODE:
                print("\n" + "=" * 80)
                print("SENDING TO LLM:")
                print("=" * 80)
                print("[SYSTEM]: You are a research assistant coding chat transcripts from a bargaining experiment. Return only valid JSON.")
                print(f"\n[USER PROMPT]:\n{prompt}")
                print("=" * 80)

            response = client_or_model.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a research assistant coding chat transcripts from a bargaining experiment. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
            )
            response_text = response.choices[0].message.content.strip()

            if TEST_MODE:
                print("\nLLM RESPONSE:")
                print("=" * 80)
                print(response_text)
                print("=" * 80)

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.warning(f"No JSON found in response: {response_text[:200]}")

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    return None


def main():
    """Main function to run the encoding process."""
    logger.info("Starting encoding with GPT...")

    # Initialize LLM
    client_or_model, model_name = init_llm()
    logger.info(f"Initialized GPT ({model_name})")

    # Read the encoding template
    logger.info(f"Reading template: {TEMPLATE_FILE}")
    _tdf = pd.read_csv(TEMPLATE_FILE)
    header = _tdf.columns.tolist()
    rows = [[str(v) if pd.notna(v) else '' for v in r] for r in _tdf.values.tolist()]

    logger.info(f"Loaded {len(rows)} rows with {len(header)} columns")

    # Identify column indices
    chat_idx = header.index('Chat')
    round_idx = header.index('Round')
    identity_idx = header.index('identity')

    # Identify coding column indices
    coding_col_indices = {}
    for i, col in enumerate(header):
        if col.startswith(CODING_PREFIXES):
            coding_col_indices[col] = i

    logger.info(f"Coding columns: {len(coding_col_indices)}")

    # Process each row
    total = min(len(rows), MAX_ROWS) if MAX_ROWS else len(rows)
    output_rows = []

    for row_idx in range(total):
        row = rows[row_idx]
        chat = row[chat_idx] if chat_idx < len(row) else ''
        round_num = row[round_idx] if round_idx < len(row) else '1'
        identity = row[identity_idx] if identity_idx < len(row) else ''

        period = row[header.index('Period')]
        group = row[header.index('Group')]
        treatment = row[header.index('Treatment')]

        logger.info(f"Processing row {row_idx + 1}/{total}: T={treatment} P={period} G={group} R={round_num} id={identity}")

        if not chat.strip():
            logger.info(f"  Empty chat, skipping LLM call")
            output_rows.append(list(row))
            continue

        # Build prompt and call LLM
        prompt = build_prompt(chat, round_num, identity)
        result = call_llm(client_or_model, model_name, prompt)

        # Create output row (copy of input)
        out_row = list(row)

        if result:
            # Fill in coding values from LLM response
            for col_name, col_idx in coding_col_indices.items():
                if col_name in result:
                    val = result[col_name]
                    try:
                        out_row[col_idx] = str(int(val))
                    except:
                        out_row[col_idx] = '0'
                else:
                    out_row[col_idx] = '0'
        else:
            logger.error(f"  LLM returned no result, using defaults")
            for col_name, col_idx in coding_col_indices.items():
                out_row[col_idx] = '0'

        output_rows.append(out_row)

        # Rate limiting
        time.sleep(0.2)

        if (row_idx + 1) % 10 == 0:
            logger.info(f"Completed {row_idx + 1}/{total} rows")

    # Save results
    output_file = os.path.join(RESULTS_DIR, "gpt.csv")
    pd.DataFrame(output_rows, columns=header).to_csv(output_file, index=False)

    logger.info(f"Saved results to {output_file}")
    logger.info(f"Total rows processed: {len(output_rows)}")

    # Summary statistics
    print(f"\nENCODING SUMMARY (GPT)")
    print(f"{'=' * 50}")
    print(f"Total rows: {len(output_rows)}")
    print(f"Output: {output_file}")
    if TEST_MODE:
        print(f"TEST MODE: Only processed first {MAX_ROWS} rows")
        print(f"Set TEST_MODE = False to process all data")


if __name__ == "__main__":
    main()

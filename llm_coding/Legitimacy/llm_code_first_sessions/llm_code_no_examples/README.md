# LLM Coding Replication — NO EXAMPLES VERSION
## Legitimacy, Communication, and Leadership in the Turnaround Game

Scripts to replicate human coding of Turnaround Game manager messages with three LLMs.

**VERSION: NO EXAMPLES** — The prompt contains only category *descriptions*, no example messages. Each manager message is classified independently (no surrounding context).

## Coding Categories (11, multi-label binary)

| Category | Description |
|----------|-------------|
| cat_1a_suggested_effort_0 | Suggests 0 hours |
| cat_1b_suggested_effort_10 | Suggests 10 hours |
| cat_1c_suggested_effort_20 | Suggests 20 hours |
| cat_1d_suggested_effort_30 | Suggests 30 hours |
| cat_1e_suggested_effort_40 | Suggests 40 hours |
| cat_1f_ambiguous_suggestion | Positive about effort but no specific number |
| cat_2_explanation_for_effort | Explains why to choose effort level |
| cat_3_trust_statements | Trust / teamwork appeals |
| cat_4_positive_feedback | Praise for past performance |
| cat_5_negative_feedback | Criticism of past performance |
| cat_6_social_banter | Off-topic chat |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Required keys: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`.

### Data file

Each script reads `data_encoding_template.csv` (the manager messages to code). A copy of the message template is included under `llm_coding/Legitimacy/llm_code_new_sessions/`; the final merged labels for all coders are in the repository's `data/master_dataset.csv`.

## Usage

```bash
export TEST_MODE=true        # first 10 rows only
python gpt_coding_replication.py
python gemini_coding_replication.py
python deepseek_coding_replication.py

export TEST_MODE=false       # full data set
```

Each script writes `<model>_classifications_no_examples.csv` (and a Stata `.dta`) into a `results/` folder it creates next to itself.

## Prompt Structure

Experimental instructions + the 11 category descriptions (no examples) + a single message to classify, per API call.

## Files

```
llm_code_no_examples/
├── gpt_coding_replication.py
├── gemini_coding_replication.py
├── deepseek_coding_replication.py
├── requirements.txt
└── .env.example
```

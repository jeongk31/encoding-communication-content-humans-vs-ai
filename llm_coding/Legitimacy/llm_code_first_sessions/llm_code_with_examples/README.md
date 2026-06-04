# LLM Coding Replication — WITH EXAMPLES VERSION
## Legitimacy, Communication, and Leadership in the Turnaround Game

Scripts to replicate human coding of Turnaround Game manager messages with three LLMs, where the prompt embeds worked YES/NO **examples** alongside the category descriptions.

**VERSION: WITH EXAMPLES** — Same per-message classification as the `no_examples` variant, but the coding instructions include example messages for each category.

## Coding Categories (11, multi-label binary)

| Category | Description | Example (YES) |
|----------|-------------|----------------|
| cat_1a_suggested_effort_0 | Suggests 0 hours | "0..im out" |
| cat_1b_suggested_effort_10 | Suggests 10 hours | "Everyone select 10 hours for this one!" |
| cat_1c_suggested_effort_20 | Suggests 20 hours | "let's all choose 20 this round" |
| cat_1d_suggested_effort_30 | Suggests 30 hours | "put in a minimum of 30 hours" |
| cat_1e_suggested_effort_40 | Suggests 40 hours | "Keep picking 40!" |
| cat_1f_ambiguous_suggestion | Positive about effort, no number | "let's go hard this round" |
| cat_2_explanation_for_effort | Explains why | "we'll get 400 ECUs" |
| cat_3_trust_statements | Trust / teamwork | "trust me, work together" |
| cat_4_positive_feedback | Praise | "great job!" |
| cat_5_negative_feedback | Criticism | "we need to do better" |
| cat_6_social_banter | Off-topic | jokes, casual chat |

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

Each script writes `<model>_classifications_with_examples.csv` (and a Stata `.dta`) into a `results/` folder it creates next to itself.

## Prompt Structure

Experimental instructions + the 11 category descriptions **with examples** + a single message to classify, per API call.

## Files

```
llm_code_with_examples/
├── gpt_coding_replication.py
├── gemini_coding_replication.py
├── deepseek_coding_replication.py
├── requirements.txt
└── .env.example
```

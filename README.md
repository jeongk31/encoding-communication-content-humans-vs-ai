# Encoding of Communication Content in Experiments: Humans versus AI

Replication code and data.

---

## Repository layout

```
.
├── llm_coding/                 # Code that called the LLM APIs to produce the codings
│   ├── Legitimacy/
│   │   ├── llm_code_first_sessions/   # original sessions; variants: baseline, RA consensus, guidance, meta-prompt
│   │   └── llm_code_new_sessions/     # additional sessions; same four variants
│   ├── Promises/                      # variants: baseline, RA consensus, meta-prompt
│   └── Timing/                        # variants: baseline, RA consensus, guidance, meta-prompt
├── data/
│   ├── master_dataset.csv             # final merged long-format dataset — all studies/coders (Git LFS)
│   └── master_dataset_README.txt      # data dictionary (columns + per-study category definitions)
└── analysis/                          # Stata cross-study comparison tables + rendered outputs
    ├── LLM_Baseline/{simplified,extended}/    # LLM column = baseline prompt
    └── LLM_Guidance/{simplified,extended}/    # LLM column = guidance prompt (Promises falls back to baseline)
```

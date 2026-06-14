# AIary SFT Data Release

This folder contains only the JSONL datasets used for the round1~5 KoBART SFT flow and the final realistic daily diary SFT flow.

## Contents

| Folder | Files | Rows | Notes |
| --- | ---: | ---: | --- |
| `round1/` | 4 | 2,000 | GPT teacher anchor data used to train `kobart_student_round1`. |
| `round2/` | 10 | 4,692 | `train_round2_for_finetune_*.jsonl`. Training used this data plus `round1/` anchors. |
| `round3/` | 10 | 4,532 | `train_round3_for_finetune_*.jsonl`. Training used this data plus `round1/` anchors. |
| `round4/` | 10 | 4,529 | `train_round4_for_finetune_*.jsonl`. Training used this data plus `round1/` anchors. |
| `round5/` | 13 | 6,234 | `train_round5_for_finetune_*.jsonl`. Training used this data plus `round1/` anchors. |
| `realistic_sft/` | 2 | 1,153 | Final train/eval data for `kobart_student_round5_realistic_daily`. |
| `meta/` | 2 | - | Dataset stats/config snapshots for traceability. |

Total JSONL rows: 23,140.

## Training Inputs

- Round1: `round1/*.jsonl`
- Round2: `round1/*.jsonl` + `round2/*.jsonl`
- Round3: `round1/*.jsonl` + `round3/*.jsonl`
- Round4: `round1/*.jsonl` + `round4/*.jsonl`
- Round5: `round1/*.jsonl` + `round5/*.jsonl`
- Realistic SFT: `realistic_sft/final_train.jsonl` and `realistic_sft/final_eval.jsonl`

## Excluded

This release intentionally excludes model weights, checkpoints, logs, generated comparison reports, smoke-test outputs, and intermediate `merged_full_*` / `student_gen_*` / `gpt_rewritten_*` shards that were not directly used as final SFT input files.

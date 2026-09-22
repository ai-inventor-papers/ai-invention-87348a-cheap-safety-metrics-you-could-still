# SEALED

Written once at construction time. Nothing in this repository reads `sealed/sealed_items.jsonl` after
`scripts/build_items.py` wrote it (checked by grep in `scripts/acceptance.py`).

## Sealed item pool
- file: `sealed/sealed_items.jsonl`
- sha256: `bd077329e58dac431ae4bacbd035cd17d4394c22294a809c5c09072912c9c16c`
- rows: 672 (236 matched pairs + 200 unpaired OR-Bench-hard benign-alarming reserve)
- rows per source|side: {"XSTest|benign_twin": 168, "XSTest|harmful": 168, "JBB-Behaviors|harmful": 68, "JBB-benign|benign_twin": 68, "OR-Bench-hard-1k|benign_alarming_reserve": 200}
- construction code (`scripts/build_items.py`) sha256: `b279df8d0974979dd59f8d4dac555a6f879fa7349048db828b4d95105f413182`
- disjointness (normalised text; strip+casefold+collapse whitespace): {"screen_outcome": 0, "screen_sealed": 0, "outcome_sealed": 0, "sealed_in_substrate": 0}

## Sealed checkpoint list
- file: `sealed/sealed_checkpoints.json`, sha256 `ec3aad9556828f40a35dcf1e71da9dfad5e928ccf650ef284e25a9222d7390c7`
- repos (checked by Hub METADATA only, HfApi.model_info; no config, tokenizer or weight download): ibm-granite/granite-3.3-2b-instruct, ibm-granite/granite-4.0-micro, huihui-ai/Huihui-granite-4.0-micro-abliterated, stabilityai/stablelm-2-zephyr-1_6b, stabilityai/stablelm-zephyr-3b

## Leak note
Five checkpoints of the sealed families were already behaviour-graded in iteration 2
(`iter_2/gen_art/gen_art_experiment_3/results/graded/`: extD__ibm-granite__granite-3.1-2b-instruct,
extE__Damien420__granite-3.2-2b-instruct-abliterated, extE__ibm-granite__granite-3.2-2b-instruct,
extE__hereticness__heretic_stablelm-2-1_6b-chat, extE__stabilityai__stablelm-2-1_6b-chat).
Those five are EXCLUDED from confirmation; the sealed list above names FRESH repos only. The granite /
stablelm FAMILIES are therefore not behaviour-naive at the family level, only at the repo level.

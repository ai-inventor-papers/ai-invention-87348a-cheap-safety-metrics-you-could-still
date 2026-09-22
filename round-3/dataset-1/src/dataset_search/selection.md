# Dataset selection — LLM safety evaluation panel

Context: panel already holds local copies of XSTest, JailbreakBench JBB-Behaviors
(harmful+benign), StrongREJECT, OR-Bench-hard-1k. This search ran 48 broad HF
queries (`dataset_search/searches.json`, 174 unique repos surfaced), narrowed to
24 candidates (`dataset_search/candidates.json`, full provenance per entry),
downloaded the 12 KEEP picks to `temp/datasets/<org>__<name>/`.

## KEPT (12) — downloaded to temp/datasets/

| repo id | rows (downloaded) | size on disk | adds to panel |
|---|---|---|---|
| `PKU-Alignment/BeaverTails` | 27,186 (30k_train) | 29MB | **harmful-side**: 14-category harm labels + safe/unsafe judgment on prompt+response pairs |
| `PKU-Alignment/PKU-SafeRLHF` | 73,907 (train) | 202MB | **harmful-side**: response-pair preference w/ per-response harm category + severity level |
| `stanford-crfm/air-bench-2024` | 5,694 (test) | 7.5MB | **harmful-side**: regulation-grounded (EU AI Act/US policy) risk taxonomy, broad category coverage |
| `toxigen/toxigen-data` | 8,960 (annotated/train) | 6.7MB | **toxicity dimension**: implicit hate speech, target-group + stereotyping labels (ACL 2022) |
| `nvidia/Aegis-AI-Content-Safety-Dataset-2.0` | 30,007 (train) | 24MB | **harmful-side / grader**: NAACL 2025, fine-grained violated-category labels on prompt+response |
| `ai-safety-institute/AgentHarm` | 176 harmful + 176 harmless_benign (test_public, twin configs) | 1.2MB | **capability + pair-matched twins**: agentic/tool-use harm, harmful vs. harmless_benign are explicit twin task variants |
| `allenai/coconot` | 11,477 original/train + 379 contrast/test (twin configs) | 8.6MB | **benign-alarming with twins**: original vs. contrast configs are pair-matched same-topic comply/noncomply items across a broader noncompliance taxonomy than XSTest |
| `LibrAI/do-not-answer` | 939 (train) | 6.1MB | **grader calibration**: ships pre-graded GPT-4/ChatGPT/Claude/ChatGLM2 responses w/ harmfulness+action labels |
| `AmazonScience/FalseReject` | 14,624 (train) | 75MB | **benign-alarming (over-refusal)**: 44 categories of adversarially-generated benign prompts + CoT responses, 2025 paper |
| `allenai/real-toxicity-prompts` | 99,442 (train) | 71MB | **toxicity dimension**: classic prompt-continuation degeneration benchmark, real Perspective-API scores (EMNLP 2020) |
| `furonghuang-lab/PHTest` | 3,269 (train) | 1.8MB | **benign-alarming (over-refusal)**: AutoDAN-generated pseudo-harmful-but-benign prompts, distinct generation methodology from XSTest/OR-Bench |
| `truthfulqa/truthful_qa` | 817 x 2 configs (generation + multiple_choice, validation) | 3.1MB | **capability item**: knowledge/truthfulness control, separates misinformation-avoidance from safety refusal |

Total on disk: ~436MB across 12 dirs (each individually under the 300MB cap;
`PKU-Alignment/PKU-SafeRLHF` is the largest at 202MB).

### Which add what (per the task's three categories)
- **Harmful-side items**: BeaverTails, PKU-SafeRLHF, AIR-Bench-2024, Aegis-2.0,
  AgentHarm (harmful config), do-not-answer.
- **Benign-alarming items with twins**: coconot (original vs. contrast, same
  topic/comply-vs-not), AgentHarm (harmful vs. harmless_benign, same task
  templates), FalseReject and PHTest (benign-but-alarming-phrased, no explicit
  per-item twin but extend the XSTest/OR-Bench over-refusal side with new
  generation methods and categories).
- **Capability items**: TruthfulQA (knowledge/truthfulness control, both
  generation and multiple_choice forms so it can be scored either way).
- **Toxicity dimension** (new axis beyond refusal/jailbreak framing): ToxiGen,
  RealToxicityPrompts.

## DISCARDED (12)

**Gated, access failed (6)** — HF marks these `gated:"auto"`; our `HF_TOKEN`
is valid (`whoami-v2` confirms `canReadGatedRepos: true`) but `load_dataset`
and the datasets-server `/rows` and `/splits` endpoints all return
`DatasetNotFoundError` / "private or gated" for these specific repos — the
account has not been individually granted access to each gate. Per the task
rule ("Gated datasets: skip unless HF_TOKEN works"), all six are skipped:
- `walledai/AdvBench` — real GCG-paper mirror (arXiv:2307.15043), but its
  content is available ungated via `mlabonne/harmful_behaviors` (also
  discarded below, for redundancy with JBB/StrongREJECT).
- `allenai/wildguardmix` — WildGuard (arXiv:2406.18495), would have been a
  strong pick (moderation tool training data) if accessible.
- `walledai/HarmBench` — HarmBench (arXiv:2402.04249).
- `allenai/wildjailbreak` — WildTeaming (arXiv:2406.18510); also 540.9MB,
  over our 300MB cap even had access worked.
- `sorry-bench/sorry-bench-202503` — SORRY-Bench (arXiv:2406.14598).
- `allenai/xstest-response` — graded responses on top of XSTest prompts we
  already hold; would have been nice-to-have, not essential.

**Non-gated but not selected (6)** — real provenance, judged lower marginal
value than the 12 kept:
- `LLM-LAT/harmful-dataset` — no dataset card, no license, no dedicated
  paper (used informally in LAT/refusal-representation research); redundant
  chosen/rejected structure vs. BeaverTails/PKU-SafeRLHF which have real
  provenance.
- `Bertievidgen/SimpleSafetyTests` — real paper (arXiv:2311.08370) but only
  100 prompts across 5 extreme-severity areas; heavily overlaps with
  StrongREJECT/JBB-harmful already in the panel.
- `declare-lab/HarmfulQA` — real paper (arXiv:2308.09662) but payload is
  multi-turn "blue/red" conversation trees, adding integration complexity
  for a single-turn refusal panel; topic coverage overlaps BeaverTails/AIR-Bench.
- `textdetox/multilingual_toxicity_dataset` — real PAN shared-task
  provenance, non-gated, but multilingual binary toxic/non-toxic
  classification; our panel is English-focused and ToxiGen already covers
  toxicity in English with richer annotation.
- `Anthropic/hh-rlhf` — the canonical RLHF preference dataset
  (arXiv:2204.05862), but generic helpfulness/harmlessness chat preferences
  without structured harm-category labels; PKU-SafeRLHF/BeaverTails give the
  same chosen/rejected structure with safety-specific annotation.
- `mlabonne/harmful_behaviors` — no card/license/arXiv tag of its own; a bare
  ungated re-upload of the GCG-paper `harmful_behaviors.csv`. Noted here as
  the accessible alternative to gated `walledai/AdvBench`, but its 520
  single-line behavior strings substantially duplicate JBB-Behaviors and
  StrongREJECT already in the panel.

## Process notes
- Ran 48 parallel HF searches (`dataset_search/raw/*.txt` → compiled into
  `dataset_search/searches.json`), surfacing 174 unique repo ids.
- Previewed all 24 candidates with sample rows (`dataset_search/previews/`).
  The shared `.ability_client_venv` lacked the `datasets` package
  (`ModuleNotFoundError`), so a local venv was created in the session
  scratchpad (outside W, per task's "write only under W" rule) with
  `datasets>=4.0.0`, `huggingface-hub`, `pandas`, etc., and used to run the
  skill's own preview/download scripts directly (bypassing the ability
  server, per the skill's documented fallback path).
- Several previews initially errored with "Bad split: train" because the
  default `--split train` doesn't exist for every repo (e.g. BeaverTails
  splits are `330k_train`/`30k_train`/etc., AgentHarm is `test_public`,
  TruthfulQA is `validation`); re-ran each with its real split name.
- Verified per-repo gating status and on-disk size via `HfApi.dataset_info`
  (`files_metadata=True`) for all 24 before downloading.
- Web-verified provenance (paper, arXiv id, license) for every KEEP and every
  DISCARD via `aii-web-tools` search; no invented citations — see
  `candidates.json` `paper` fields for exact arXiv ids / venues found.

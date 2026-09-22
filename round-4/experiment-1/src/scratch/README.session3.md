# Causal-gain safety screen: live tier (iteration 4, CPU fallback)

This repository is the **live / intervention tier** of the iteration-4 cheap-safety screen. It loads one
checkpoint at a time and reads its hidden states, attention and gradients on the 16 frozen SCREEN16 prompts:
8 harmful / benign-twin pairs, seed 20260921. From those reads it measures eight single-model internal
candidates. It also recomputes the two logit-only baselines on the same inputs. Every value is then
correlated with a two-sided graded safety target.

| candidate | what it measures | role |
|---|---|---|
| C1 | finite-difference harm→refusal gain: push the last prompt token along a cross-fitted harm direction at mid depth; the slope of the first-token refuse-vs-comply margin | primary |
| C2 | two-sided self-ablation: project the harm direction out at mid depth; harmful-minus-twin margin drop | primary |
| C3 | twin-patching flip: patch the harmful last-token residual with the twin's, per depth band | primary |
| C7 | attention mass from the last prompt token onto the tokens where a pair differs | primary |
| C8 | grad×input share of those tokens | primary |
| C9 | template-site share (Leong 2502.13946) | replication row |
| C11 | 8-token early-response commitment along the readout-free refusal axis | primary |
| C16 | steering-dose slope (Li 2603.24543) | comparator only |
| logit_gap, refusal_mass | first-token logit gap and refusal-token mass, harmful minus twin | black-box bars |

A side arm regenerates the iteration-2 ROSI reversal cells at 128 tokens instead of 20.

**Read `RESULTS.md` first.** It holds the verdict tables, n / families / MDE, and the explicit negative
statements. `posthoc_live.md` holds the exploratory, not pre-registered, diagnostics.

## What actually ran (read this before any number)

- **No CUDA: named failure `LIVE_TIER_NO_CUDA`.** There is no `/dev/nvidia*`, no `nvidia-smi`, and
  `torch.cuda.is_available()` is false. The container is 2 hyperthreads with a 16 GB cgroup.
  - As the plan's fallback prescribes, the full candidate set (poles, k=8, direction nulls, oracle rows,
    constant-offset control) runs on the 21-model `CPU_SUBPANEL`, every model ≤ 2 B parameters.
  - The graded Qwen3-4B anchor quartet (Qwen3-4B, Qwen3-4B-SafeRL, mlabonne/Qwen3-4B-abliterated,
    DreamFast/qwen3-4b-heretic) runs afterwards in **`ANCHOR_LITE`** mode, with the time caps raised
    (`TIME_CAP_OVERRIDE`). ANCHOR_LITE keeps plain-condition candidates, oracle rows C1/C2 and the logit bars;
    it drops nulls, k8, pole-condition values and the offset control.
  - `Qwen/Qwen3-4B-Base` runs last, in the separate base stratum. It uses a plain `User: …\nAssistant:`
    renderer and is excluded from every correlation.
  - Every other 2–4 B panel model is listed in `skips.json` as `NOT_IN_CPU_SUBPANEL`.
  - S5 (under 120 s per 4 B model on a GPU) is not measurable.
- **bf16 for every model (`CPU_DTYPE_BF16_ALL`).** The first-token margin is computed in float32 from
  the final-norm hidden state and float32 copies of the REFUSE/COMPLY unembedding rows.
- **Two sessions, one code version for all rows.**
  - Session 1 built the pipeline and pre-registered it. `PREREG.json` was hashed at 15:59:59 UTC, before any
    panel model was scored. Session 1 then measured 12 models before a pod restart killed the loop
    (`POD_RESTART_RESUME`).
  - Session 2 ran an independent code review. It found no error in any primary plain-condition value, but it
    fixed 3 major and 4 minor issues (`CODE_FIXES_POST_REVIEW_V2`): the offset-control stale KV cache, C3 never
    patching the final layer, the C9 AtP-reliability rule with true patching under the poles, same-shape bf16
    references for C9, a noise-robust C1 linearity check, and an oracle ≥2-per-class gate.
  - **Every row in `rows/` was re-measured with the v2 code.** The v1 rows and code are kept in
    `scratch/rows_v1_pre_review/` and `scratch/code_v1_pre_review/`.
- **Exact CPU shortcuts, no approximations.**
  - Last-token interventions (C1, C3) reuse the KV cache of the T−1 prefix.
  - All-position interventions that start at layer j (C2, C16, C9 true patching) feed the base pass's
    captured output of layer j−1, so layers 0…j−1 are skipped.
  - Reference margins always come from the same numerical path and batch shape as their intervened
    counterparts.
- **Labels.**
  - BALANCED = S2_core: CORE-94, 64-token greedy, gemini-2.5-flash stance judge.
  - PRODUCT = P2 = harm_refusal × benign_compliance, computed from components. The iteration-3 `J2` is 2·S2−1
    and is never used.
  - Two checkpoints finished grading after the iteration-3 snapshot (`LABELS_EXTENDED_POST_SNAPSHOT`).
- Every deviation is in `DEVIATIONS.json`. Every panel repo is either in `rows/` or in `skips.json`.

## Layout

| path | what |
|---|---|
| `PREREG.json`, `PREREG_hash.txt` | Pre-registration: the verbatim S1–S6 text (hypothesis section d) and its separate `S_text_sha256`, orientations, bands, eps grid, seeds, random-direction definition, variance floor and time caps. `method.py` refuses to run if the hash does not match. |
| `prereg.py` | Writes `PREREG.json`, `screen16_ids.json` (per-prompt sha256 and file sha) and `labels_map.json` (explicit key mapping; P2 from components). |
| `live_lib.py` | Model plumbing: seal guard, guarded loader, chat rendering (plus the base-stratum plain renderer), left-padded batches with content/suffix spans, differing tokens, hook and layer-skip context managers, readouts. |
| `method.py` | **The per-checkpoint measurement** (the plan's `live_screen.py`): base passes under 3 presentations; cross-fitted directions h / r^(a) / r^(b) / r^(o); anisotropy-matched random directions; all candidates with nulls, k=8, poles and oracle rows; the constant-offset control. Resumable, with one atomic `rows/<slug>.json` per model. CLI: `--repos`, `--lite`, `--soft-cap/--hard-cap`, `--allow-base`, `--smoke`. |
| `run_panel_v2.sh` | Session-2 driver: graded sub-panel → anchor quartet (lite) → ungraded sub-panel → base stratum. |
| `judge_lib.py` | Stance judge (rubric and parser copied verbatim from iteration-3 `scripts/judge.py`), per-arm budgets, $3 global cap, per-call ledger (`spend_ledger.jsonl`, `spend.json`). |
| `analyze_live.py` | Pure-CPU analysis → `candidates_live.json` (rho under both targets and both aggregation units, partial rho with the one-sided lineage-bootstrap bound, S1–S6 applied mechanically, MDE, poles, timing, oracle comparison, offset control, ATP_UNRELIABLE switch), `candidate_values_live.json` (join-ready long format) and `analysis_tables.md`. |
| `posthoc_live.py` | Exploratory diagnostics (never feed S1–S6): C3 saturation, readout validity, harm-direction quality, pole ordering, and the model's own judged SCREEN16 behaviour as a black-box baseline → `posthoc_live.json` / `.md`. |
| `rosi_lib.py`, `rosi128.py` | ROSI side arm. Functions are copied from iteration 2 with source path and line citations. `rosi128.py --mode full` regenerates and grades; `--analyze-only` recomputes the report from saved grades with no API or model calls. Output: `rosi_128tok.json` and `results/rosi128/`. |
| `make_results.py` | Composes `RESULTS.md` from the JSON outputs. Every number is generated, none hand-typed. |
| `make_outputs.py` | Writes `method_out.json` (exp_gen_sol_out) and its full/mini/preview variants. |
| `stage_b.py` | Stage B/D smoke checks: batched vs unbatched margins, pole ordering. |
| `tests/test_live.py` | Stage A unit tests: planted gain recovered within 5 %, zero readout, constant-offset invariance on a linear toy, cross-fit leakage, seal guard, non-empty differing tokens. |
| `rows/` | Raw per-model rows: the main measured artifact. |
| `skips.json`, `DEVIATIONS.json`, `spend.json`, `spend_ledger.jsonl` | Bookkeeping. |
| `results/judge_cache.jsonl`, `results/rosi128/` | Judge cache (append-only) and the ROSI generations and grades. |
| `scratch/` | Smoke rows, Stage B/D/F checks, pre-review v1 rows and code, review notes. |
| `.aii/plan_spec.md` | The artifact plan, copied verbatim. |
| `logs/` | Run logs. |

## How to run

```bash
UV_PROJECT_ENVIRONMENT=venv_live uv sync                          # torch CPU wheel, transformers 4.57
venv_live/bin/python prereg.py                                     # once; refuses to overwrite
venv_live/bin/python -m pytest -c pytest.ini -q tests/test_live.py
venv_live/bin/python method.py --repos Qwen/Qwen2.5-0.5B-Instruct --smoke && venv_live/bin/python stage_b.py
nohup bash run_panel_v2.sh > logs/panel_v2_driver.log 2>&1 &      # resumable panel (all 4 stages)
venv_live/bin/python rosi128.py --mode full                        # ROSI 128-token arm (paid judge calls)
venv_live/bin/python analyze_live.py && venv_live/bin/python posthoc_live.py
venv_live/bin/python make_results.py && venv_live/bin/python make_outputs.py
```

## Restoring removed files

- `venv_live/`: `UV_PROJECT_ENVIRONMENT=venv_live uv sync` (uses `pyproject.toml` and `uv.lock`).
- `__pycache__/`, `tests/__pycache__/`, `.pytest_cache/`: regenerated automatically on the next import
  or pytest run.
- Model weights are never stored here. They live in the run's shared HF cache and can be re-fetched with
  `huggingface-cli download <repo>`, where `<repo>` is any id in `PREREG.json:cpu_subpanel` or the anchor list
  in `run_panel_v2.sh`.

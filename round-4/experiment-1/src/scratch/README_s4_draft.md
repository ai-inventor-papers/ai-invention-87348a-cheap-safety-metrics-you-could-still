# Causal-gain safety screen, live tier (iteration 4)

This repository is the **live / intervention tier** of the iteration-4 cheap-safety screen. It asks whether
one model's internal reads can predict its graded two-sided safety. There is no parent model and no reference
model, and the reads use only 16 fixed prompts.

For each chat model it loads the checkpoint once and reads hidden states, attention and gradients on the
**16 frozen SCREEN16 prompts**: 8 harmful / benign-twin pairs, seed 20260921, file sha256 in
`screen16_ids.json`. From those reads it measures eight single-model internal candidates. It also recomputes
the two logit-only baselines on the same inputs. Every value is then correlated with a graded two-sided safety
target from the iteration-3 panel.

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

**Read `RESULTS.md` first.** It holds the verdict tables, n / families / MDE and the explicit negative
statements. It is generated from the JSON outputs, so no number in it is hand-typed. `posthoc_live.md` holds the
exploratory diagnostics, which were not pre-registered.

## Headline

All numbers below are generated in `RESULTS.md`, `candidates_live.json` and `method_out.json → metadata.headline_findings`.

- **Panel.** 36 checkpoints were measured on an NVIDIA L4 GPU (35 chat + `Qwen/Qwen3-4B-Base`). The graded set is
  **n = 23**: 8 families, 11 lineages, 2 blanket refusers. The one-sided MDE_rho is 0.531.
- **Cost.** The whole live screen of a 4B model takes about 16 s after load. S5 (<120 s per 4B model) is met by
  every candidate.
- **No internal candidate passes all six pre-registered rules (S1–S6), so nothing ships from this screen.**
- **The strongest single-model internal read is C2**, two-sided harm-direction self-ablation at mid depth.
  - Checkpoint-level ρ = **0.900** [0.793, 0.971] with the BALANCED target. The first-token logit gap reaches 0.772
    [0.441, 0.902].
  - Family-level ρ = 0.881 (8 family means).
  - PRODUCT target: ρ = 0.884.
  - Partial ρ given the logit gap and log size = **0.746**, with a one-sided 5 % lineage-bootstrap bound of 0.440,
    so it **passes S1**.
  - It is significant **within each of the three families** that have ≥3 graded checkpoints: Qwen2.5 1.00,
    Qwen3 0.95, and TinyLlama 1.00, where the logit gap has ρ = 0.00.
  - It fails **S2(b)**: it exceeds its own random-direction null on only 7/23 models, and ≥60 % is required. Those
    7 exceedances fall on 7/11 upper-half-safety models and 0/12 lower-half models (exploratory §4c). The
    pre-registered rule therefore penalises the read for sitting at its null on the unsafe models.
  - It fails **S3**: an always-refuse system wrapper does not lower it on every honest model (15/24 checks hold).
- **C1** (finite-difference harm→refusal gain) also passes S1: partial ρ 0.491, bound 0.242. It fails S2(b) and
  S3.
- **Step 1: the Qwen3-4B lineage** (RESULTS §3c-bis).
  - BALANCED order: SafeRL 0.929 > instruct 0.906 > heretic 0.553 > mlabonne-abliterated 0.515.
  - **C1 reproduces that order exactly**: 3.37 > 3.15 > 1.81 > 0.19.
  - C2 (1.23 vs 0.75) and the logit gap (15.7 vs 5.0) both put the instruct model above SafeRL.
  - SafeRL puts essentially no first-token probability on the refusal-word set (refusal mass 0.000), so every
    first-token readout under-rates it.
  - Both abliterated models are the lowest on C1, C2 and the logit gap.
- **Negative reads.**
  - Attention, gradient and patching reads carry no signal: C3 −0.20, C7 0.05, C8 0.08, and the C9 Leong
    replication 0.14.
  - C11 (8-token commitment) and C16 (steering-dose slope, comparator) are significant in Qwen2.5 only, so they are
    labelled **works within one family only: NEGATIVE**.
- **Exploratory: the behavioural probe is stronger.** The model's own judged behaviour on the same 16 prompts
  (16 generations + 16 judge calls) reaches ρ = 0.931. Beyond it, C2 adds partial ρ 0.315 (bound −0.122). C2
  needs no generation and no judge, but on this panel it does not beat 16 judged generations.
- **Cross-hardware.** 12 models were re-measured on CPU and GPU.
  - Forward and intervention reads reproduce: Spearman(CPU, GPU) is 1.00 for C1, C7 and the logit gap, and 0.92
    for C2.
  - Generation- and threshold-dependent reads move: C11 changes by a median 41 %, because 15/16 greedy replies
    diverge. C9 changes by 15 %, because a pair crosses the 0.25-logit informativeness gate.
- **ROSI side arm.** At 128 tokens the iteration-2 ROSI x4 reversal **shrinks and is not significant** under the
  balanced target (dD2 −0.070 [−0.172, 0.031]). It **persists** under the product target (−0.177 [−0.339, −0.020]).
  The hidden-direction control is null.
- **Spend.** OpenRouter spend is $0.14 in total, under the $3 cap.
DEPTH_SWEEP_PLACEHOLDER

## What actually ran (read this before any number)

The artifact ran across **four pods**, because the pod restarted three times. Every restart is logged in
`DEVIATIONS.json` under `POD_RESTART_RESUME`, and `env.json` keeps one entry per session.

- **Sessions 1–3 (CPU only, `LIVE_TIER_NO_CUDA`).**
  - Session 1 built and pre-registered the pipeline. `PREREG.json` was hashed at 15:59:59 UTC, before any
    panel model was scored.
  - Session 2 ran an independent code review (`CODE_FIXES_POST_REVIEW_V2`) and re-measured every row with the
    reviewed v2 code.
  - Session 3 re-measured 12 models on 4 CPU threads.
  - All three sessions ran on 2–4 CPU threads, so they could only cover the ≤2B `CPU_SUBPANEL`.
- **Session 4 (this pod: NVIDIA L4 GPU, 23 GB): the final rows.** The GPU made the plan's primary branch
  possible, so the whole panel was re-measured on CUDA (`GPU_SESSION4_FULL_PANEL`):
  - every non-sealed chat checkpoint of the iteration-3 `panel.json`, graded or not, plus `Qwen/Qwen3-4B-Base`
    in its separate base stratum;
  - bf16 throughout;
  - the 9.3 GB VRAM cap (`torch.cuda.set_per_process_memory_fraction`);
  - the PREREG's GPU-branch constants: 20 anisotropy-matched random directions, and all 5 C16 alphas in every
    variant;
  - S5 timing measured on the GPU.
- **The measurement code is unchanged apart from device plumbing.**
  - `method.py`/`live_lib.py` were made device-agnostic: model and batches on the device, `.cpu()` before numpy,
    and hook vectors on the hidden state's device.
  - `torch.cuda.synchronize()` runs in the block timers, so the timings measure completed GPU work.
  - Other plumbing changes: no `RLIMIT_AS` under CUDA; the thread count follows the cgroup CPU quota; and a
    `GRAD_CHUNKED` fallback halves the backward pass when it would exceed the VRAM cap.
  - `TORCH_DISABLE_NATIVE_JIT=1` is set because torch 2.14 routes the RoPE outer product through a Triton kernel
    that needs a C toolchain this pod lacks. The standard ATen kernels are used instead.
  - The pre-port code is in `scratch/code_v3_cpu_pre_gpu/`.
- **The 12 session-3 CPU rows are kept as a cross-hardware check** in `scratch/rows_cpu_v3/`. They are compared
  with their GPU re-measurement in `candidates_live.json → cross_hardware` and in RESULTS §3d. That check is
  descriptive only and never enters S1–S6.
- **Labels.**
  - BALANCED = S2_core: CORE-94 items, 64-token greedy replies, gemini-2.5-flash stance judge.
  - PRODUCT = P2 = harm_refusal × benign_compliance, computed from components, so a blanket refuser scores 0.
    The iteration-3 `J2` is 2·S2−1 and is never used.
  - 23 of the 35 chat checkpoints are graded.
- Every deviation is in `DEVIATIONS.json`. Every panel repo is either in `rows/` or in `skips.json`.

## Layout

| path | what |
|---|---|
| `PREREG.json`, `PREREG_hash.txt` | Pre-registration: the verbatim S1–S6 text (hypothesis section d) and its separate `S_text_sha256`, orientations, bands, eps grid, seeds, random-direction definition (CPU 8 / GPU 20), variance floor and time caps. `method.py` refuses to run if the hash does not match. |
| `prereg.py` | Writes `PREREG.json`, `screen16_ids.json` (per-prompt sha256 and file sha) and `labels_map.json` (explicit key mapping; P2 from components). |
| `live_lib.py` | Model plumbing: seal guard, device selection, guarded loader, chat rendering (plus the base-stratum plain renderer), left-padded batches with content/suffix spans, differing tokens, hook and layer-skip context managers, readouts. |
| `method.py` | **The per-checkpoint measurement** (the plan's `live_screen.py`). It runs base passes under 3 presentations; fits cross-fitted directions h / r^(a) / r^(b) / r^(o); draws anisotropy-matched random directions; computes every candidate with nulls, k=8, poles and oracle rows; and runs the constant-offset control. It is resumable, with one atomic `rows/<slug>.json` per model. CLI: `--repos`, `--smoke`, `--allow-base`, `--lite`, `--soft-cap/--hard-cap`. |
| `run_panel_gpu.sh` | **Session-4 driver (the production run)**: 23 graded → 12 ungraded → base stratum, resumable. |
| `run_panel_v2.sh`, `run_panel_v3.sh` | Session-2/3 CPU drivers, kept for provenance. |
| `judge_lib.py` | Stance judge (rubric and parser copied verbatim from iteration-3 `scripts/judge.py`), per-arm budgets, $3 global cap, per-call ledger (`spend_ledger.jsonl`, `spend.json`). |
| `analyze_live.py` | Pure-CPU analysis → `candidates_live.json`, `candidate_values_live.json` (join-ready long format) and `analysis_tables.md`. `candidates_live.json` holds: rho under both targets and both aggregation units; partial rho with the one-sided lineage-bootstrap bound; S1–S6 applied mechanically, with S5 from the GPU seconds; MDE; poles; timing; oracle comparison; offset control; the ATP_UNRELIABLE switch; cross-hardware. |
| `posthoc_live.py` | Exploratory diagnostics that never feed S1–S6 → `posthoc_live.json` / `.md`: C3 saturation, readout validity, harm-direction quality, pole ordering, and the model's own judged SCREEN16 behaviour as a black-box baseline. |
| `rosi_lib.py`, `rosi128.py` | ROSI side arm. Functions are copied from iteration 2 with source path and line citations. It ran in sessions 1–2 on CPU in fp32 (`ROSI_ARM_CPU_FP32`). Output: `rosi_128tok.json`, `results/rosi128/`. |
| `make_results.py` | Composes `RESULTS.md` from the JSON outputs. |
| `make_outputs.py` | Writes `method_out.json` (exp_gen_sol_out) and its full/mini/preview variants. |
| `stage_b.py` | Stage B/D checks: batched vs unbatched margins, r^(b) steering sign, C1 eps agreement, C2 vs null, logit gap sign, pole ordering. Outputs: `scratch/stage_b_*.json`. |
| `tests/test_live.py` | Stage A unit tests: planted gain recovered within 5 %, zero readout, constant-offset invariance on a linear toy, cross-fit leakage, seal guard, non-empty differing tokens. |
| `write_env.py`, `env.json` | Per-session compute environment (sessions 1–3 reconstructed from the deviation log, session 4 measured). |
| `s3_bookkeeping.py`, `s4_bookkeeping.py` | Idempotent DEVIATIONS/skips bookkeeping per session. |
| `install.sh`, `pyproject.toml`, `uv.lock`, `requirements_gpu.txt` | Environment rebuild (CPU venv via `uv sync`, CUDA venv via pinned requirements). |
| `rows/` | Raw per-model GPU rows: the main measured artifact. |
| `skips.json`, `skips_superseded.json`, `DEVIATIONS.json`, `spend.json`, `spend_ledger.jsonl` | Bookkeeping. |
| `results/judge_cache.jsonl`, `results/rosi128/` | Judge cache (append-only) and the ROSI generations and grades. |
| `scratch/` | CPU rows of session 3 (`rows_cpu_v3/`), pre-port code, smoke rows, Stage B/D/F checks, v1 rows and code before the review, review notes, analysis fixtures. |
| `.aii/plan_spec.md` | The artifact plan, copied verbatim. |
| `logs/` | Run logs (`panel_gpu_*.log` for the production run). |

## How to run

```bash
./install.sh                                                       # venv_live (CPU) + venv_gpu (CUDA 13.0 wheel)
venv_live/bin/python prereg.py                                     # once; refuses to overwrite the hashed PREREG
venv_gpu/bin/python -m pytest -c pytest.ini -q tests/test_live.py
venv_gpu/bin/python method.py --smoke --repos Qwen/Qwen3-4B        # anchor timing check (writes scratch/smoke_*.json)
nohup bash run_panel_gpu.sh > logs/panel_gpu_driver.log 2>&1 &     # resumable production panel on the GPU
venv_gpu/bin/python stage_b.py Qwen/Qwen2.5-0.5B-Instruct rows/Qwen__Qwen2.5-0.5B-Instruct.json
venv_live/bin/python rosi128.py --analyze-only                     # ROSI arm report from saved grades (no API calls)
venv_live/bin/python s4_bookkeeping.py
venv_live/bin/python analyze_live.py && venv_live/bin/python posthoc_live.py
venv_live/bin/python make_results.py && venv_live/bin/python make_outputs.py
```

Without a GPU, `method.py` runs the same code on CPU (`LIVE_DEVICE=cpu` forces it). It then uses the PREREG CPU
constants: 8 random directions and the 3-alpha C16 variant grid.

## Restoring removed files

- `venv_live/`: `UV_PROJECT_ENVIRONMENT=venv_live uv sync` (uses `pyproject.toml` and `uv.lock`), or
  `./install.sh cpu`.
- `venv_gpu/`: `./install.sh gpu`. This installs torch 2.14.0 from the cu130 index plus `requirements_gpu.txt`.
- `__pycache__/`, `tests/__pycache__/`, `.pytest_cache/`: regenerated automatically on the next import or
  pytest run.
- Model weights are never stored here. They live in the run's shared HF cache and can be re-fetched with
  `huggingface-cli download <repo>`. The repo ids are the `--repos` lists in `run_panel_gpu.sh`.

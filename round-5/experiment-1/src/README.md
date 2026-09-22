# iteration-5 GPU tier — C1n random-steer control, five new activation reads, and the AMS incumbent, measured blind on Set A

**Result in one line: of 28 measured reads, exactly one — C12, the twin d-prime along a cross-fitted harm axis — passes all six pre-registered gates (rho 0.607 [0.360, 0.868]); C1 survives the norm-matched random-steer control almost unchanged (rho(C1, C1n_cd) = 0.995); and the published AMS incumbent is beaten by both of our bars while its shipped implementation reads PAD activations.**

*(Full numbers in `RESULTS.md`; this file is the repository guide. Run `bash install.sh` first — the virtual
environment has already been deleted, see "Restoring removed files"; the analysis and tables re-run
without it on a plain Python 3.12 with numpy and scipy.)*

One GPU pass over the SAME 36 checkpoints iteration 4 measured — 23 **graded**, 12 **Set A** (measured and
hashed *before* any Set A label exists; 11 of the 12 succeeded, `microsoft/Phi-3.5-mini-instruct` exceeded the
10.5 GB VRAM budget and is a recorded skip) and `Qwen/Qwen3-4B-Base` in its own stratum — on the SAME frozen
SCREEN16 substrate (8 harmful/benign-twin pairs, 16 prompts, seed 20260921,
sha256 `9380e30e…fa3775`). It answers three questions the iteration-4 screen could not:

1. **Is C1 (finite-difference harm→refusal gain) anything more than the content-free pull toward refusal that
   Malla et al. (2609.06951) report for *any* steer?** C1 is measured against 20 **norm-matched random steers**
   drawn from the layer's own activation span, at eps ∈ {0.02, 0.05, 0.10}, two ways: the central difference
   (the odd part — the exact C1 functional form, which cancels the even pull by construction) and the one-sided
   difference plus the even `pull_even` term, which is where Malla's effect lives. Reported, not assumed.
2. **Do five never-run activation reads beat the logit-only bars?** C6 (DLA concentration), C10 (area between
   harm-decodability and refusal-drive depth curves), C12 (twin d′ on a cross-fitted harm axis), C13
   (presentation invariance, declared sign NEGATIVE) and C15-act (late-layer effective rank and dispersion),
   each cross-fitted on 4 twin-grouped folds.
3. **How does the published incumbent do on the same models?** AMS Tier-1 (`ams-scanner` 0.1.3, Apache-2.0,
   GoogleCloudPlatform/activation-model-scanner) as published *and* cross-fitted, with the in-sample gap.

Everything is judged by the pre-registration in `PREREG.json`, hashed into `PREREG_hash.txt` **before any value
was computed**, and applied mechanically by `analyze_gpu.py` — the S1–S6 rule with the repaired S2(b) and S3.

## Layout

| path | what it is |
|---|---|
| `PREREG.json`, `PREREG_hash.txt` | the frozen rule, orientations, definitions, seeds and panel lists. Every row carries the hash; the analysis refuses to run against a different one. |
| `method.py` | the per-checkpoint measurement: base passes, C1, C2, the logit bars, the C1n random-steer block, C6/C10/C12/C13/C15-act, both wrapped poles, the k=8 subset, the offset controls, the 64-token generation and the judged oracle rows. Resumable: a checkpoint whose row matches the PREREG hash and the code hash is skipped. |
| `live_lib.py` | model loading, chat-template rendering, hooks, the sealed-repo guard (shared with iteration 4). |
| `ams_lib.py` | the AMS incumbent: the package in-process on our own bf16 model, plus our cross-fitted variants and its nulls. |
| `blind_guard.py` | the Set A blindness guard: an audit hook that raises `BlindnessViolation` on any open of the Set A grading workspace. |
| `analyze_gpu.py`, `make_candidate_values.py` | the frozen rule applied to the 23 graded checkpoints; the long join-ready value list. |
| `freeze_setA.py` | the blindness freeze: `values_setA.json` + `values_setA.sha256` + `freeze_certificate.json`. |
| `check_invariants.py`, `collect_ams_and_coverage.py`, `make_outputs.py` | row sanity checks, `ams_tier1.json` + `coverage_gpu5.json`, and `method_out.json` (exp_gen_sol_out) with its mini/preview variants. |
| `rows/<slug>.json` | one row per checkpoint — every candidate, every variant, every null, timings, VRAM peak, flags. |
| `tests/` | the unit tests (T1–T7 plus the six inherited iteration-4 tests). `logs/pytest.log` holds the run. |
| `run_panel_gpu5.sh` | the resumable driver (stages: graded → Set A → base), PID file `logs/driver.pid`. |
| `run_oom_retry.sh` | re-measures a checkpoint that hit the 10.0 GB operating cap, one per fresh process at the declared 10.5 GB budget. |
| `RESULTS.md`, `analysis_tables_gpu.md`, `analysis_gpu.json`, `candidates_gpu.json` | the findings, the full tables, the machine-readable analysis and the per-candidate verdicts. |
| `DEVIATIONS.json`, `skips.json`, `coverage_gpu5.json`, `spend.json`, `env.json` | what differed from the plan, what was skipped and why, join coverage, OpenRouter spend, the machine. |
| `it4_ref/` | read-only copies of the iteration-4 `prereg.py` and `analyze_live.py` (provenance only; never run here). |
| `.aii/manifest.yaml`, `.aii/upload_ignore_regexes.json` | which heavy paths are kept vs. regenerable, and the paths excluded from the public repo (the virtualenv and bytecode caches only — every deliverable is published). |

## How to run

```bash
bash install.sh                      # rebuilds venv_gpu (see below)
export TORCH_DISABLE_NATIVE_JIT=1    # torch 2.14's Triton RoPE kernel needs a C toolchain this box lacks
venv_gpu/bin/python -m pytest        # T1-T7 + the inherited tests
venv_gpu/bin/python method.py --smoke --repos Qwen/Qwen2.5-0.5B-Instruct
nohup bash run_panel_gpu5.sh > logs/driver.log 2>&1 & echo $! > logs/driver.pid   # the whole panel, resumable
venv_gpu/bin/python freeze_setA.py           # BEFORE any analysis, once the 12 Set A rows exist
venv_gpu/bin/python make_candidate_values.py && venv_gpu/bin/python analyze_gpu.py
venv_gpu/bin/python collect_ams_and_coverage.py && venv_gpu/bin/python make_outputs.py
venv_gpu/bin/python make_results.py          # RESULTS.md, counts first
venv_gpu/bin/python check_invariants.py rows/*.json   # independent per-row sanity checks
```

Monitor the panel by PID only (`kill -0 $(cat logs/driver.pid)`); several pipeline runs share this machine, so
never match processes by name.

## Restoring removed files

`venv_gpu/` was **already removed inside this round**: it held three third-party torch/triton `.so`
files above the 100 MB per-file publication limit (`libtorch_cuda.so` 480 MB, `libtriton.so` 479 MB,
`libtorch_cpu.so` 426 MB), and its `bin/` and `pyvenv.cfg` had already been reaped by a pod restart,
so it was an unusable corpse rather than a working environment. Deleting it took the workspace from
5.1 GB to 31 MB; nothing that remains exceeds 6.8 MB. No result, figure, log or code file was
removed, and `.aii/manifest.yaml` marks only the bytecode caches for deletion after the round.

| path | restore with |
|---|---|
| `venv_gpu/` | `bash install.sh` (equivalently `bash scratch/make_venv_gpu.sh`, then `uv pip install --python venv_gpu/bin/python 'ams-scanner[cli]==0.1.3' --no-deps`) |
| `**/__pycache__/` | nothing to do — regenerated on the next import |

You do **not** need `venv_gpu/` to reproduce the analysis or the tables: `analyze_gpu.py`,
`make_candidate_values.py`, `collect_ams_and_coverage.py` and `make_outputs.py` run on a plain
Python 3.12 with numpy and scipy (verified on numpy 2.5.3 / scipy 1.18.1, the versions used here).
The environment is only needed to re-measure checkpoints on a GPU with `method.py`.

Model weights are **not** stored here: every checkpoint is pulled from the shared HuggingFace cache
(`HF_HUB_CACHE`) at its pinned `resolved_sha`, which each row records.

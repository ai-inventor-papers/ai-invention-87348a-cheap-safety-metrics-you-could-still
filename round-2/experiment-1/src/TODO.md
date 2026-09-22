# TODO (session 2, started 2026-09-21 07:03 UTC; deadline ~12:55 UTC)

- [x] TODO 1. Read and STRICTLY follow these skills: aii-python, aii-long-running-tasks, aii-json, aii-file-size-limit, aii-use-hardware, aii-parallel-computing.
- [x] TODO 2. Read preview files from dependencies to understand data structure. Use ALL datasets provided — do not skip or select a subset. Read domain handbook if applicable (see <available_domain_handbooks>). Test basic functionality with 'uv run'.
- [x] TODO 3. Fully implement our method AND baseline (comparison) as described in artifact plan in './method.py'. Use exp_gen_sol_out.json schema in aii-json skill for output format validation. Include everything specified in the artifact plan, but you may also implement additional relevant methods or analysis beyond what's listed. Be very attentive to meticulously and exhaustively fix any errors in your code.

## Session-2 working notes
- Session 1 (03:18-04:47) harvested 30 ckpts (17 tier-I inherited + 13 tier-W weights-only), graded 1040 items
  (stance + StrongREJECT framings), ran a partial score pass. It did NOT emit race_table / class_trend /
  prompt_budget / poles / summary / full_method_out / analysis_out. `.venv` was reaped (cleanup) -> rebuilt.
- Hardware now: NO GPU, cpuset = 2 logical CPUs (1 physical Zen4 core + SMT, avx512_bf16), 16 GB cgroup,
  host load ~2 (was ~290 in session 1).

## Session-3 working notes (started 07:18 UTC; hard deadline ~13:10 UTC, target finish 12:45)
- `.venv` was REAPED again at ~07:16 (killed the session-2 tier-G harvest mid-checkpoint). Env now lives
  in `venv_exp1/` (UV_PROJECT_ENVIRONMENT=venv_exp1 uv sync). CPU is fast again (eigh1536 0.65 s).
- [x] relaunch tier-G harvest (run_harvest_g2.sh: Qwen2.5 pair + CensorTune-0.5B full; Phi-4 pair, gemma, OLMo, SmolLM2, CensorTune-1.5B lite)
- [x] trial score run (--tag s3pre) -> fix every crash (4 smoke/trial runs; 10+ faults fixed)
- [x] tier-W harvest of the 2 gemma-2 safety siblings + Qwen2.5-1.5B base
- [x] judge the tier-G generations (stage judge; cache makes old grades free)
- [x] pole battery: orient each metric by its own safe direction; all metrics, not just weights
- [ ] final score run (barrier must PASS), output stage, aii-json validation, mini/preview
- [ ] README.md + RESULTS.md refresh + .aii/manifest.yaml (venv_exp1/ delete:regenerable)
- 11:39 final run launched (run_final.sh). Tier G done: CensorTune-0.5B (full), Qwen2.5-1.5B-Instruct
  (full, 124 min), Josiefied-Qwen2.5-1.5B-abliterated (OOM-killed 10:32, re-run min profile, 48-token gen,
  deviation D12). Instruct-only families skipped by the G7 clock gate. G2 fires -> primary holdout = LOLO.
- 12:03 FINAL_OK (run_final.sh, 2nd pass after the budget-BA and effective-inputs fixes); README/RESULTS/manifest written 12:10.

## Finalisation TODOs (verbatim from the prompt)
- [x] TODO 1. Use aii-json skill's format script with `--input method_out.json` to generate full, mini, and preview versions. If not in your workspace (see <workspace> above), copy them there. Run 'ls -lh' to verify these three files exist (DO NOT read them).
- [x] TODO 2. Apply aii-file-size-limit skill's file size check procedure (100MB limit) to method_out.json and full_method_out.json.
- [x] TODO 3. Ensure a `pyproject.toml` exists in your workspace with ALL dependencies pinned to the exact versions installed in your .venv (run `.venv/bin/pip freeze` to get them). This is required for reproducibility. The [project] section must include name, version, requires-python, and a dependencies list with pinned versions (e.g. `numpy==2.0.2`, not `numpy>=2.0`).
- finalisation: full/mini/preview regenerated (3.5M/9.4K/7.7K); method_out.json + full_method_out.json 3.5 MB each, far under the 100 MB limit (no split); pyproject.toml pins all 55 installed packages, uv lock OK, `uv sync --dry-run` against venv_exp1 -> 'Would make no changes'.

# TODO (tracked in-file: no todo tool available in this session)
- [x] TODO 1. Read and STRICTLY follow these skills: aii-python, aii-long-running-tasks, aii-json, aii-file-size-limit, aii-use-hardware, aii-parallel-computing. (session 1; session 2 re-reads)
- [x] TODO 2. Read preview files from dependencies to understand data structure. Use ALL datasets provided — do not skip or select a subset. Read domain handbook if applicable (see <available_domain_handbooks>). Test basic functionality with 'uv run'. (session 1)
- [x] TODO 3. Fully implement our method AND baseline (comparison) as described in artifact plan in './method.py'. Use exp_gen_sol_out.json schema in aii-json skill for output format validation. Include everything specified in the artifact plan, but you may also implement additional relevant methods or analysis beyond what's listed. Be very attentive to meticulously and exhaustively fix any errors in your code.

## Session 2 (started 17:05 UTC, pod was restarted ~16:48 and killed the panel loop at model 10/21)
- [x] restart panel loop (PID in logs/panel_s2.pid, log logs/panel_s2.log)
- [x] independent code review: method.py/live_lib.py, analyze_live.py, rosi arm (session 2; see DEVIATIONS CODE_FIXES_POST_REVIEW_V2)
- [~] anchor quartet: session 3 switched to FULL mode (4 CPUs) via run_panel_v3.sh
- [ ] final analysis, RESULTS.md, method_out.json (+mini/preview), validation, README, manifest

## Session 3 (started 17:53 UTC; a 2nd pod restart ~17:37 killed the v2 driver after 4/19 v2 rows)
- [x] relaunch panel: run_panel_v3.sh (PID logs/panel_v3_driver.pid) waits for the v2 stage-1 python, then anchors FULL, ungraded sub, base lite, 10 ungraded 2-4B extras
- [x] session-2 2-thread rows moved to scratch/rows_v2_session2_2threads/ (re-measured on 4 threads by v3 stage 1)
- [ ] audit A: analyze_live.py statistics (subagent)
- [ ] audit B: make_results.py / make_outputs.py + exp_gen_sol_out validation (subagent)
- [ ] DEVIATIONS: 2nd restart, ANCHOR full mode, extras, hardware change; skips cleanup for repos with rows
- [ ] final analysis after stage 2 (graded set complete); final candidate_values_live.json after stage 5
- [ ] RESULTS.md, method_out.json (+mini/preview), README, manifest, file-size check, final checks

## Session 4 (started 18:24 UTC; a 3rd pod restart killed the v3 driver after 12 v3 CPU rows; NEW POD HAS AN NVIDIA L4 GPU)
- [x] 12 v3 CPU rows moved to scratch/rows_cpu_v3/ (cross-hardware check); code backups in scratch/code_v3_cpu_pre_gpu/, scratch/analysis_pre_gpu/
- [x] venv_gpu (torch 2.14.0+cu130) via scratch/make_venv_gpu.sh -> install.sh + requirements_gpu.txt
- [x] GPU port of method.py/live_lib.py (device plumbing; TORCH_DISABLE_NATIVE_JIT=1; cgroup threads; GRAD_CHUNKED); smoke Qwen3-0.6B vs CPU row; Qwen3-4B 17.8 s after load
- [x] analyze_live/make_results/make_outputs for GPU rows (S5 = own + 3 shared base passes; cross_hardware; full panel); within-family label bug in make_results fixed
- [x] env.json (write_env.py), run_panel_gpu.sh 36/36 rows (retry: VRAM cap 12 GB x2, tokenizer-from-lineage x1), Stage B/D on GPU
- [x] s4_bookkeeping.py (DEVIATIONS/skips), analyze_live.py, posthoc_live.py, posthoc_s4_extra.py, make_results.py, make_outputs.py (+headline_findings)
- [x] aii-json validation + mini/preview; .aii/manifest.yaml (venv_gpu added)
- [x] exploratory C2 depth sweep (exact repro; peak at the pre-registered 50% band) -> c2_depth_sweep.json/md (RESULTS 4d)
- [x] exploratory variance-matched null (exact repro of production null; C2 7/23 -> 11/23, S2(b) still fails) -> matched_null.json/md (RESULTS 4e)
- [x] README.md final, final checks, memory

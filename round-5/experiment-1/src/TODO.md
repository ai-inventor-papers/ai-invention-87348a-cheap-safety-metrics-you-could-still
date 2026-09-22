# TODO (verbatim from the task prompt) — ALL DONE

- [x] TODO 1. Read and STRICTLY follow these skills: aii-python, aii-long-running-tasks, aii-json, aii-file-size-limit, aii-use-hardware, aii-parallel-computing.
- [x] TODO 2. Read preview files from dependencies to understand data structure. Use ALL datasets provided — do not skip or select a subset. Read domain handbook if applicable (see <available_domain_handbooks>). Test basic functionality with 'uv run'.
- [x] TODO 3. Fully implement our method AND baseline (comparison) as described in artifact plan in './method.py'. Use exp_gen_sol_out.json schema in aii-json skill for output format validation. Include everything specified in the artifact plan, but you may also implement additional relevant methods or analysis beyond what's listed. Be very attentive to meticulously and exhaustively fix any errors in your code.

## Plan steps (gen_plan_experiment_2_idx2)
- [x] S0 env (L4, cgroup 15.3 CPU / 71 GB, TORCH_DISABLE_NATIVE_JIT=1, venv_gpu, env.json)
- [x] S1 PREREG.json frozen + hashed 21:52:31Z (46accdd6...), SIBLING_PREREG_ABSENT recorded
- [x] S2-3 IT4 code ported, dead candidates (C3/C7/C8/C9/C16) and the backward pass removed; C1n + C6/C10/C12/C13/C15-act added
- [x] S4 26 tests pass (T1-T7 + 6 inherited); smoke reproduces IT4 C1/C2/logit_gap/refusal_mass BIT-EXACTLY
- [x] S5 AMS Tier-1 in-process (ams-scanner 0.1.3) + cross-fitted variants + nulls; padding bug isolated
- [x] S6 panel: 35/36 rows (1 recorded skip), coverage 0 incomplete / 0 missing
- [x] S7 blindness freeze BEFORE analysis: 11/12 Set A, sha256 95d97ac3..., certificate written
- [x] S8 analysis on the 23 graded, frozen rule applied mechanically; C12 passes S1-S6
- [x] S9 outputs: method_out (validated) + full/mini/preview, candidate_values_gpu, candidates_gpu, ams_tier1,
      analysis_tables_gpu, RESULTS.md, README, DEVIATIONS (12), skips, spend ($0), env, manifest, struct_out

# TODO TRACKER (copied verbatim from prompt)

TODO 1. Read and STRICTLY follow these skills: aii-python, aii-long-running-tasks, aii-json, aii-file-size-limit, aii-use-hardware, aii-parallel-computing.
TODO 2. Read preview files from dependencies to understand data structure. Use ALL datasets provided — do not skip or select a subset. Read domain handbook if applicable (see <available_domain_handbooks>). Test basic functionality with 'uv run'.
TODO 3. Fully implement our method AND baseline (comparison) as described in artifact plan in './method.py'. Use exp_gen_sol_out.json schema in aii-json skill for output format validation. Include everything specified in the artifact plan, but you may also implement additional relevant methods or analysis beyond what's listed. Be very attentive to meticulously and exhaustively fix any errors in your code.

## STATUS (session 2, 2026-09-21 07:17 UTC -> )
- [x] TODO 1 skills: aii-python, aii-long-running-tasks, aii-json, aii-file-size-limit (pending final size check), aii-use-hardware, aii-parallel-computing -- read and applied (cgroup-aware limits, uv-only env, loguru, staged smoke -> full runs, background PIDs)
- [x] TODO 2 deps: gen_art_research_1/research_out.json (title/summary/answer/sources/follow_up_questions; incumbents folded into make_outputs.INCUMBENTS); inherited item sets items_160 / items_inherited / items_exp3; `uv run`-equivalent smoke tests passed (pyenv/bin/python)
- [x] TODO 3 method.py (single entry point, --stages all) + behave2.py + judge2.py + bcell_acts.py + adversary.py + make_outputs2.py -> full_method_out.json / mini_ / preview_ (exp_gen_sol_out; all three VALIDATED 11:37 UTC), out/analysis_out.json, out/RESULTS.md, README.md, .aii/manifest.yaml

## FOLLOW-UP TODOS (copied verbatim)
TODO 1. Use aii-json skill's format script with `--input method_out.json` to generate full, mini, and preview versions. If not in your workspace (see <workspace> above), copy them there. Run 'ls -lh' to verify these three files exist (DO NOT read them).
TODO 2. Apply aii-file-size-limit skill's file size check procedure (100MB limit) to method_out.json and full_method_out.json.
TODO 3. Ensure a `pyproject.toml` exists in your workspace with ALL dependencies pinned to the exact versions installed in your .venv (run `.venv/bin/pip freeze` to get them). This is required for reproducibility. The [project] section must include name, version, requires-python, and a dependencies list with pinned versions (e.g. `numpy==2.0.2`, not `numpy>=2.0`).
- [x] FOLLOW-UP 1: method_out.json -> aii-json format script -> full/mini/preview regenerated (11:42 UTC); all four validate as exp_gen_sol_out; ls -lh verified.
- [x] FOLLOW-UP 2: aii-file-size-limit check: method_out.json 162K, full_method_out.json 162K -- far below 100MB, no split needed.
- [x] FOLLOW-UP 3: pyproject.toml pins all 59 installed packages exactly (`uv pip freeze --python pyenv/bin/python`; the env is pyenv/ because the reaper deleted .venv/bin, and the repo forbids pip).

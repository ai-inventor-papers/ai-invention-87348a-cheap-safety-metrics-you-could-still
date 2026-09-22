#!/usr/bin/env bash
# Final sequence: inspect -> grade -> analyse -> bonus -> render -> assemble -> validate.
# Every step is resumable and reads only what is already on disk, so this can be re-run safely.
set -uo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
run() { echo "### $* ###"; timeout "$1" $PY "${@:2}" 2>&1 | tail -6; echo "--- rc=$? ---"; }

# 0. close the join gap FIRST: every graded checkpoint must have a recipe vector, or the primary
#    endpoint silently drops it.
run 300  make_graded_panel.py
run 2100 stage1_weights.py --panel results/panel_graded_gap.json --minutes 30 --byte-budget-mb 1500

run 600  gate3_inspect.py
run 2400 stage2b_grade.py --minutes 35
run 900  stage3_analysis.py
run 2400 stage5_bonus.py
run 600  make_results_md.py
run 900  method.py --stage assemble

SKILL_DIR=/ai-inventor/.claude/skills/aii-json
"$SKILL_DIR/../.ability_client_venv/bin/python" \
  "$SKILL_DIR/scripts/aii_json_validate_schema.py" \
  --format exp_gen_sol_out --file "$(pwd)/method_out.json" 2>&1 | tail -4
ls -lh method_out.json RESULTS.md

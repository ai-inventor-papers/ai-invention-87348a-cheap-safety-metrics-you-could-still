#!/bin/bash
# Final assembly: regression check -> analysis -> method_out.json -> RESULTS.md -> schema validation -> mini/preview.
set -uo pipefail
cd "$(dirname "$0")"
PY=venv_lanec/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
$PY regression_v2_vs_harvest.py > logs/regression_v2.out 2>&1 || echo "regression script failed"
$PY method.py --stage analyse 2>&1 | grep -v -i warn | tail -3
$PY make_results_md_v2.py
SK=/ai-inventor/.claude/skills/aii-json
$SK/../.ability_client_venv/bin/python $SK/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/method_out.json" | tail -2
$SK/../.ability_client_venv/bin/python $SK/scripts/aii_json_format_mini_preview.py --input "$(pwd)/method_out.json" 2>&1 | tail -4
ls -lh method_out.json full_method_out.json mini_method_out.json preview_method_out.json 2>/dev/null

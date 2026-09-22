#!/bin/bash
# FINAL scoring + outputs. Launch ONLY after every harvest process has ended: the barrier inside
# `--stage score` refuses to treat a START record as done and would stamp PARTIAL_PANEL.
#   ./run_final.sh            (judge -> score -> deviations -> output -> mini/preview -> validate)
cd "$(dirname "$0")"
set -o pipefail
PY=venv_exp1/bin/python
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONUNBUFFERED=1
SKILL_DIR=/ai-inventor/.claude/skills/aii-json
JPY=$SKILL_DIR/../.ability_client_venv/bin/python
$PY -u method.py --stage judge || exit 1          # new generations only; the cache makes old grades free
$PY -u method.py --stage score --n-perm 1000 --n-boot 2000 --n-null-draws 1000 || exit 2
$PY scripts/record_deviations.py || exit 3
$PY -u method.py --stage env || exit 4             # the env report analysis_out.json quotes
$PY -u method.py --stage output || exit 4
$PY scripts/digest.py > results/DIGEST.md || exit 7
$JPY $SKILL_DIR/scripts/aii_json_format_mini_preview.py --format exp_gen_sol_out --input "$(pwd)/method_out.json" || exit 5
$JPY $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$(pwd)/full_method_out.json" || exit 6
echo "FINAL_OK"

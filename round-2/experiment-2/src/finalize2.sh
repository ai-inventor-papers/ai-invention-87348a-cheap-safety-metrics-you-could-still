#!/bin/bash
# analysis -> activation battery -> outputs -> schema validation -> mini/preview -> sizes
set -u
cd "$(dirname "$0")"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
pyenv/bin/python bcell_acts.py || echo "bcell_acts failed"
pyenv/bin/python make_outputs2.py || { echo "make_outputs2 FAILED"; exit 1; }
pyenv/bin/python update_readme.py
SKILL_DIR=/ai-inventor/.claude/skills/aii-json
PY=$SKILL_DIR/../.ability_client_venv/bin/python
$PY $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$PWD/full_method_out.json"
cp full_method_out.json method_out.json
$PY $SKILL_DIR/scripts/aii_json_format_mini_preview.py --input "$PWD/method_out.json"
for f in full_method_out.json mini_method_out.json preview_method_out.json; do
  $PY $SKILL_DIR/scripts/aii_json_validate_schema.py --format exp_gen_sol_out --file "$PWD/$f" | tail -1
done
rm -f method_out.json
ls -lh full_method_out.json mini_method_out.json preview_method_out.json out/analysis_out.json out/RESULTS.md
head -1 out/RESULTS.md

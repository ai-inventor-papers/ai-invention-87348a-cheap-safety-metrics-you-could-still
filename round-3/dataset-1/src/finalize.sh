#!/bin/bash
# Rebuild labels, acceptance and the final data_out files from results/ (no model or API calls unless grading is pending).
set -e
cd "$(dirname "$0")"
venv_ds/bin/python scripts/grade.py
venv_ds/bin/python scripts/summarize.py
venv_ds/bin/python scripts/acceptance.py > /dev/null
uv run --no-project data.py
S=/ai-inventor/.claude/skills/aii-json
$S/../.ability_client_venv/bin/python $S/scripts/aii_json_validate_schema.py --format exp_sel_data_out --file "$PWD/full_data_out.json"
$S/../.ability_client_venv/bin/python $S/scripts/aii_json_format_mini_preview.py --input "$PWD/full_data_out.json"
mv full_full_data_out.json full_data_out.json
mv mini_full_data_out.json mini_data_out.json
mv preview_full_data_out.json preview_data_out.json
rm -f data_out.json
ls -lh full_data_out.json mini_data_out.json preview_data_out.json

#!/usr/bin/env bash
# Final packaging: analysis -> the four tables -> schema validation -> mini/preview.
# Safe to re-run; every step reads from disk and overwrites its own output.
set -uo pipefail
cd "$(dirname "$0")"

SKILL_DIR="/ai-inventor/.claude/skills/aii-json"
PY="$SKILL_DIR/../.ability_client_venv/bin/python"

echo "== 1. analysis + the four tables =="
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python make_outputs.py 2>&1 \
  | grep -E "INFO|ERROR" | tail -12

echo
echo "== 2. schema validation (exp_gen_sol_out) =="
"$PY" "$SKILL_DIR/scripts/aii_json_validate_schema.py" \
  --format exp_gen_sol_out --file "$(pwd)/method_out.json" 2>&1 | tail -6

echo
echo "== 3. mini / preview variants =="
"$PY" "$SKILL_DIR/scripts/aii_json_format_mini_preview.py" \
  --input "$(pwd)/method_out.json" 2>&1 | tail -6

echo
echo "== 4. sizes =="
ls -lh method_out.json full_method_out.json mini_method_out.json \
       preview_method_out.json out/analysis_out.json out/RESULTS.md 2>/dev/null \
  | awk '{print "   ", $5, $9}'

echo
echo "== 5. counts on disk =="
printf "    panel rows      : %s\n" "$(ls out/panel/*.json 2>/dev/null | wc -l)"
printf "    acts panel rows : %s\n" "$(ls out/acts_panel/*.json 2>/dev/null | grep -vc diag)"
printf "    ladder cells    : %s\n" "$(ls out/cells/*.json 2>/dev/null | wc -l)"
printf "    behaviour cells : %s\n" "$(ls out/bcells/*.json 2>/dev/null | wc -l)"
printf "    judge spend USD : %s\n" \
  "$(python3 -c "
import json,pathlib
p=pathlib.Path('out/spend.jsonl')
print(round(sum(json.loads(l).get('usd',0) for l in p.read_text().splitlines() if l.strip()),5) if p.exists() else 0.0)
" 2>/dev/null)"

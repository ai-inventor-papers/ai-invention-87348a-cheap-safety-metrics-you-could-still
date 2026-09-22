#!/bin/bash
# Full pipeline, end to end.
#
# Stages are SEPARATE process invocations and are NEVER run concurrently: the
# barrier inside `--stage score` is the thing iteration 1 lacked, and running a
# scorer beside a live harvest is exactly how it produced a race table of n/a.
#
# Process management is PID-based throughout. `stop_harvest.sh` selects workers
# by /proc/<pid>/cwd resolving to this workspace, never by process name --
# several pipeline runs share this machine.
set -u
cd "$(dirname "$0")"
export OMP_NUM_THREADS=${OMP:-2} OPENBLAS_NUM_THREADS=${OMP:-2} MKL_NUM_THREADS=${OMP:-2}
export PYTHONUNBUFFERED=1
PY=venv_exp1/bin/python   # a `.venv` here is reaped by a box-wide cleaner (session 3)
SKILL_DIR="/ai-inventor/.claude/skills/aii-json"
JPY="$SKILL_DIR/../.ability_client_venv/bin/python"

step () { echo; echo "======== $* ========"; }

step "0. stop any live harvest worker (scoring must not race the harvest)"
./stop_harvest.sh

step "1. environment + inheritance integrity"
$PY -u method.py --stage inherit & PID=$!; wait $PID; echo "inherit exit=$?"

step "2. structural isolation checks (must all PASS)"
OMP_NUM_THREADS=1 $PY -u tests/test_isolation.py & PID=$!; wait $PID; echo "isolation exit=$?"

step "3. judge (idempotent -- cached grades cost nothing and are keyed by rubric)"
OMP_NUM_THREADS=1 $PY -u method.py --stage judge & PID=$!; wait $PID; echo "judge exit=$?"

step "4. score (runs the BARRIER first, then every analysis)"
$PY -u method.py --stage score --n-perm "${NPERM:-300}" --n-boot "${NBOOT:-400}" \
     --n-null-draws "${NNULL:-200}" & PID=$!; wait $PID; echo "score exit=$?"

step "5. assemble the four datasets + analysis_out.json"
$PY -u method.py --stage output & PID=$!; wait $PID; echo "output exit=$?"

step "6. schema validation + mini/preview variants"
"$JPY" "$SKILL_DIR/scripts/aii_json_validate_schema.py" \
  --format exp_gen_sol_out --file "$(pwd)/method_out.json"
# the formatter PREFIXES the basename -> full_/mini_/preview_method_out.json
"$JPY" "$SKILL_DIR/scripts/aii_json_format_mini_preview.py" \
  --input "$(pwd)/method_out.json"
"$JPY" "$SKILL_DIR/scripts/aii_json_validate_schema.py" \
  --format exp_gen_sol_out --file "$(pwd)/full_method_out.json"

step "7. sizes and the honest counts"
ls -lh method_out.json full_method_out.json mini_method_out.json \
       preview_method_out.json analysis_out.json 2>/dev/null
$PY - <<'PYEOF'
import json
s = json.load(open("results/summary.json"))
for k in ("n_checkpoints_harvested", "n_families_harvested",
          "n_families_with_instruct_abliterated_pair", "FAMILY_AXIS_DEGRADED",
          "harvest_tiers", "PARTIAL_PANEL", "n_safety_lineages", "readout_chosen",
          "readout_bar_met", "think_trap_confirmed", "crossover_k",
          "n_metrics_beating_null_p95", "judge_spend_usd", "gates_fired"):
    print(f"  {k:46s} {s.get(k)}")
PYEOF

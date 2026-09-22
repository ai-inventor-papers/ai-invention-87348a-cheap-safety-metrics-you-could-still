#!/usr/bin/env bash
# P8 close-out: digest -> schema validation -> mini/preview variants -> size check.
set -uo pipefail
cd "$(dirname "$0")"
SKILL_DIR="/ai-inventor/.claude/skills/aii-json"
PY="$SKILL_DIR/../.ability_client_venv/bin/python"

echo "== results digest =="
OMP_NUM_THREADS=8 .venv/bin/python -u analyze.py

echo "== schema validation (method_out.json) =="
"$PY" "$SKILL_DIR/scripts/aii_json_validate_schema.py" --format exp_gen_sol_out \
      --file "$PWD/method_out.json"

echo "== mini / preview variants =="
OMP_NUM_THREADS=8 .venv/bin/python - <<'PYEOF'
import json, copy
from pathlib import Path
root = Path(".")
full = json.loads((root / "method_out.json").read_text())

def shrink(obj, n_ds, n_ex, trunc=None):
    out = {"metadata": obj.get("metadata", {}),
           "datasets": [dict(d, examples=d["examples"][:n_ex]) for d in obj["datasets"][:n_ds]]}
    if trunc:
        def _t(v):
            if isinstance(v, str):
                return v[:trunc] + ("..." if len(v) > trunc else "")
            if isinstance(v, dict):
                return {k: _t(x) for k, x in v.items()}
            if isinstance(v, list):
                return [_t(x) for x in v]
            return v
        out = _t(out)
    return out

(root / "full_method_out.json").write_text(json.dumps(full, indent=2, ensure_ascii=False))
(root / "mini_method_out.json").write_text(json.dumps(shrink(full, 3, 3), indent=2, ensure_ascii=False))
(root / "preview_method_out.json").write_text(
    json.dumps(shrink(full, 3, 3, trunc=200), indent=2, ensure_ascii=False))
n = sum(len(d["examples"]) for d in full["datasets"])
print(f"full: {len(full['datasets'])} datasets / {n} examples")
PYEOF

echo "== schema validation (all four) =="
for f in method_out.json full_method_out.json mini_method_out.json preview_method_out.json; do
  printf '%-28s ' "$f"
  "$PY" "$SKILL_DIR/scripts/aii_json_validate_schema.py" --format exp_gen_sol_out \
        --file "$PWD/$f" 2>&1 | grep -E "PASSED|FAILED|Error" | head -3 | tr '\n' ' '
  echo
done

echo "== size check (limit 100 MB per file) =="
ls -lh method_out.json full_method_out.json mini_method_out.json preview_method_out.json 2>/dev/null | awk '{print $5, $9}'
find . -path ./.venv -prune -o -type f -size +90M -print 2>/dev/null | sed 's/^/  OVERSIZE: /'
echo "== done =="

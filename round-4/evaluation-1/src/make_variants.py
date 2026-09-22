#!/usr/bin/env python3
"""Write full/mini/preview variants of eval_out.json (exp_eval_sol_out is an object, not a top-level array)."""
import copy
import json
from pathlib import Path

WS = Path(__file__).resolve().parent


def trunc(o, n=200):
    if isinstance(o, str):
        return o if len(o) <= n else o[:n] + "..."
    if isinstance(o, list):
        return [trunc(v, n) for v in o]
    if isinstance(o, dict):
        return {k: trunc(v, n) for k, v in o.items()}
    return o


d = json.loads((WS / "eval_out.json").read_text())
(WS / "full_eval_out.json").write_text(json.dumps(d, indent=2))
mini = copy.deepcopy(d)
for ds in mini["datasets"]:
    ds["examples"] = ds["examples"][:3]
(WS / "mini_eval_out.json").write_text(json.dumps(mini, indent=2))
(WS / "preview_eval_out.json").write_text(json.dumps(trunc(mini), indent=2))
print("wrote full/mini/preview_eval_out.json")

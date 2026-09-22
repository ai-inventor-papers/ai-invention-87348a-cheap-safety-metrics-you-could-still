"""core_items.json (outcome items covered by the stored iter-2 96-token harvests) and pole_items.json."""
import json
from pathlib import Path

import numpy as np

W = Path(__file__).resolve().parent.parent
H = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_1/harvest")
out = [json.loads(l) for l in (W / "outcome_items.jsonl").open()]
scr = [json.loads(l) for l in (W / "screen16.jsonl").open()]
import re
norm = lambda s: re.sub(r"\s+", " ", s.strip().casefold())  # noqa: E731
gj = json.loads((H / "Qwen__Qwen3-4B" / "generations.json").read_text())
idx = set(gj["gen_item_idx"])
probe = {norm(p) for p in gj["probe_prompts"]}
core = [r["item_id"] for r in out if (r["substrate_id"] is not None and r["substrate_id"] in idx) or norm(r["prompt"]) in probe]
roles = {}
for r in out:
    if r["item_id"] in core:
        roles[r["outcome_role"]] = roles.get(r["outcome_role"], 0) + 1
json.dump({"item_ids": core, "n": len(core), "per_role": roles,
           "definition": "OUTCOME items covered by every stored iter-2 harvest: substrate id in gen_item_idx, or prompt equal to one of the 24 probe_prompts (XSTest contrast)"},
          open(W / "results" / "core_items.json", "w"), indent=1)
rng = np.random.default_rng(20260921)
harm = [r for r in out if r["outcome_role"] == "harmful" and r["item_id"] in core]
ben = [r for r in out if r["outcome_role"] == "benign_alarming" and r["item_id"] in core]
pick = [harm[i] for i in rng.choice(len(harm), 4, replace=False)] + [ben[i] for i in rng.choice(len(ben), 4, replace=False)]
items = [{"item_id": f"s16_{r['pair_id']}_{r['side']}", "prompt": r["prompt"], "role": "harmful" if r["side"] == "harmful" else "benign_alarming", "from": "screen16"} for r in scr]
items += [{"item_id": r["item_id"], "prompt": r["prompt"], "role": r["outcome_role"], "from": "outcome"} for r in pick]
json.dump({"items": items, "n": len(items), "note": "CPU fallback: poles on 24 items = SCREEN16 + 4 harmful + 4 benign-alarming outcome items (seed 20260921)"},
          open(W / "results" / "pole_items.json", "w"), indent=1)
print(len(core), roles, len(items))

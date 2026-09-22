#!/usr/bin/env python3
"""Build results/weights_queue.json: every checkpoint whose safetensors are already in the run-shared cache,
ordered so the checkpoints that carry a GRADED outcome are read first (edited-first, small-first), then the
known-kappa CONSTRUCTED calibration grid, then the rest of the panel (edited first), then the 4B models
(which also have a full-layer sibling harvest as a fallback)."""
import json
from pathlib import Path
from huggingface_hub import snapshot_download

WS = Path(__file__).resolve().parent
panel = {r["repo_id"]: r for r in json.loads((WS / "results/panel.json").read_text())["checkpoints"]}
genq = json.loads((WS / "results/gen_queue.json").read_text())
HARV = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_1/harvest")
harvest_meta = {}
for d in sorted(HARV.iterdir()):
    m = d / "meta.json"
    if m.exists():
        mj = json.loads(m.read_text())
        harvest_meta[mj["repo_id"]] = mj


def cached(repo):
    try:
        p = Path(snapshot_download(repo, local_files_only=True))
        return any(p.glob("*.safetensors"))
    except Exception:
        return False


def arm_of(repo):
    if repo in panel:
        return panel[repo]["arm"]
    low = repo.lower()
    if any(t in low for t in ("abliterat", "heretic", "uncensor", "decensor", "amoral")):
        return "edited"
    return "honest"


def entry(repo):
    p = panel.get(repo, {})
    hm = harvest_meta.get(repo, {})
    sig = p.get("family_signature") or (f"{hm.get('architecture')}|h{hm.get('hidden_size')}|L{hm.get('n_layers')}" if hm else None)
    return {"id": repo.replace("/", "__"), "repo_id": repo, "kind": "real", "arm": arm_of(repo),
            "family_signature": sig, "n_params_est": p.get("n_params_est") or hm.get("n_params") or 0}

order, seen = [], set()
def add(e):
    if e["id"] in seen:
        return
    seen.add(e["id"]); order.append(e)

# 1) graded-outcome checkpoints: CPU generation queue (real + constructed) in generation order
for q in genq:
    if q["kind"] == "real" and not cached(q["repo_id"]):
        continue
    add(q)
# 2) sibling-harvest checkpoints that carry generations (small first; 4B deferred to the end)
small_h = ["Qwen/Qwen3-0.6B", "huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2", "huihui-ai/Huihui-Qwen3-1.7B-abliterated-v2",
           "Qwen/Qwen3-1.7B", "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "AIPlans/TinyLlama-1.1B-IPO-PKU-SafeRLHF",
           "AIPlans/TinyLlama-1.1B-ORPO-PKU-SafeRLHF", "AIPlans/tinyllama-1.1b-dpo-pku-saferlhf",
           "Shortmund09/MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf"]
for r in small_h:
    if cached(r):
        e = entry(r)
        if not e["n_params_est"]:
            e["n_params_est"] = 1.1e9 if "inyLlama" in r or "inyllama" in r else (0.6e9 if "0.6B" in r else 1.7e9)
        add(e)
# 3) known-kappa CONSTRUCTED calibration grid (weights only; generation covers a subset)
for k in (0.1, 0.25, 0.5, 0.75, 0.9, 1.1, 1.25, 1.5, 2.0):
    add({"id": f"constructed__Qwen3-0.6B__mlabonne-abl__k{k}", "repo_id": None, "kind": "constructed", "arm": "constructed",
         "parent": "Qwen/Qwen3-0.6B", "edited": "mlabonne/Qwen3-0.6B-abliterated", "kappa": k,
         "family_signature": "Qwen3ForCausalLM|h1024|L28", "n_params_est": 596042752})
# 4) rest of the panel, edited first then honest, small first (<= 3.3B here; 4B last)
rest = [r for r in panel if r.replace("/", "__") not in seen]
rest.sort(key=lambda r: (panel[r]["arm"] != "edited", panel[r].get("n_params_est") or 0))
big = []
for r in rest:
    if (panel[r].get("n_params_est") or 0) > 3.35e9:
        big.append(r); continue
    if cached(r):
        add(entry(r))
# 5) the 4B checkpoints (graded ones first) - sibling full-layer harvests exist as fallback
for r in ["mlabonne/Qwen3-4B-abliterated", "DreamFast/qwen3-4b-heretic", "Qwen/Qwen3-4B", "Qwen/Qwen3-4B-SafeRL", "Qwen/Qwen3-4B-Base"] + big:
    if cached(r):
        e = entry(r)
        if not e["n_params_est"]:
            e["n_params_est"] = 4.02e9
        add(e)
(WS / "results/weights_queue.json").write_text(json.dumps(order, indent=1))
print(len(order), "queued;", sum(o["arm"] == "edited" for o in order), "edited;", sum(o["kind"] == "constructed" for o in order), "constructed")
for o in order:
    print(f"  {o['arm'][:6]:6s} {(o.get('n_params_est') or 0)/1e9:4.2f}B {o['id'][:70]}")

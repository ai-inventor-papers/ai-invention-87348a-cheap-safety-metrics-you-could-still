#!/usr/bin/env python3
"""Append the external-run panel (results/ext_gen/_inventory.json, non-base) to results/weights_queue.json:
edited checkpoints first, then honest siblings, smallest first, <= 3.4B params, safetensors only.
Uncached repos are marked download=True (safetensors+json only; deleted right after the read)."""
import json
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download, snapshot_download

WS = Path(__file__).resolve().parent
inv = json.loads((WS / "results/ext_gen/_inventory.json").read_text())["files"]
wq = json.loads((WS / "results/weights_queue.json").read_text())
have = {q["id"] for q in wq}
api = HfApi()
cands = {}
for e in inv:
    if e["arm_guess"] == "base":
        continue
    r = e["repo_id"]
    cands.setdefault(r, {"repo_id": r, "arm": "edited" if e["arm_guess"] == "edited" else "honest", "sources": []})
    cands[r]["sources"].append(e["source"])
rows = []
for r, c in cands.items():
    cid = r.replace("/", "__")
    if cid in have:
        continue
    info = {"id": cid, "repo_id": r, "kind": "real", "arm": c["arm"], "ext_sources": c["sources"]}
    try:
        cached = False
        try:
            p = Path(snapshot_download(r, local_files_only=True))
            cached = any(p.glob("*.safetensors"))
        except Exception:
            cached = False
        cfgp = hf_hub_download(r, "config.json")
        cfg = json.loads(Path(cfgp).read_text())
        tc = cfg.get("text_config") or cfg
        L, h = tc.get("num_hidden_layers"), tc.get("hidden_size")
        ff, V = tc.get("intermediate_size"), tc.get("vocab_size")
        n = None
        if L and h and ff and V:
            n = L * (4 * h * h + 3 * h * ff) + V * h
        mi = api.model_info(r, files_metadata=False)
        sib = [s.rfilename for s in (mi.siblings or [])]
        info.update({"n_params_est": n, "architecture": (cfg.get("architectures") or ["?"])[0],
                     "family_signature": f"{(cfg.get('architectures') or ['?'])[0]}|h{h}|L{L}",
                     "has_safetensors": any(s.endswith(".safetensors") for s in sib),
                     "gated": getattr(mi, "gated", None), "cached": cached, "download": not cached,
                     "quant": cfg.get("quantization_config") is not None})
    except Exception as ex:  # noqa: BLE001
        info.update({"error": repr(ex)[:200]})
    rows.append(info)
ok = [x for x in rows if not x.get("error") and x.get("has_safetensors") and not x.get("quant")
      and (x.get("n_params_est") or 9e9) <= 3.4e9]
ok.sort(key=lambda x: (x["arm"] != "edited", x["n_params_est"]))
(WS / "results/ext_weights_candidates.json").write_text(json.dumps(rows, indent=1))
wq = wq + ok
(WS / "results/weights_queue.json").write_text(json.dumps(wq, indent=1))
print(f"{len(rows)} external candidates, {len(ok)} queued (<=3.4B, safetensors, unquantised)")
for x in rows:
    print(f"  {'Q' if x in ok else '-'} {x['arm'][:6]:6s} {(x.get('n_params_est') or 0)/1e9:5.2f}B cached={x.get('cached')} gated={x.get('gated')} {x['repo_id'][:55]} {x.get('error','')[:60]}")

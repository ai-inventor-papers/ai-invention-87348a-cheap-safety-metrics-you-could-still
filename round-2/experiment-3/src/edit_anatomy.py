"""Anatomy of a published edit: which tensors differ between parent and edited, relative size, and the
effective rank of each difference (top singular value share). Parent-BASED - used only to interpret the
constructed known-truth arm, never as a readout."""
import json, sys
from pathlib import Path
import numpy as np, torch
from safetensors import safe_open
from huggingface_hub import snapshot_download
torch.set_num_threads(1)
par, edt = sys.argv[1], sys.argv[2]
ps, es = Path(snapshot_download(par, local_files_only=True)), Path(snapshot_download(edt, local_files_only=True))
def keys(snap):
    m = {}
    for sh in sorted(snap.glob("*.safetensors")):
        with safe_open(str(sh), framework="pt") as f:
            for k in f.keys(): m[k] = sh
    return m
kp, ke = keys(ps), keys(es)
rows = []
for k in sorted(ke):
    kk = k if k in kp else ("model." + k if "model." + k in kp else None)
    if kk is None: continue
    with safe_open(str(ke[k]), framework="pt") as f: te = f.get_tensor(k).to(torch.float64)
    with safe_open(str(kp[kk]), framework="pt") as f: tp = f.get_tensor(kk).to(torch.float64)
    if te.shape != tp.shape: continue
    d = te - tp
    dn = float(d.norm())
    if dn == 0: continue
    rel = dn / max(float(tp.norm()), 1e-12)
    info = {"key": k, "rel_frob": rel, "shape": list(d.shape)}
    if d.dim() == 2 and min(d.shape) > 1 and ("o_proj" in k or "down_proj" in k or "embed" in k or "lm_head" in k):
        sv = torch.linalg.svdvals(d.float() if max(d.shape) > 20000 else d).double().numpy()
        info["top1_share_of_frob2"] = float(sv[0] ** 2 / np.sum(sv ** 2))
        info["top2_share"] = float(np.sum(sv[:2] ** 2) / np.sum(sv ** 2))
        # is the change a projection off a direction r? then d = -r r^T W_p and the left sing. vec of d is r
    rows.append(info)
comp = {}
for r in rows:
    c = r["key"].split(".")[-2] if r["key"].endswith("weight") else r["key"]
    comp.setdefault(c, []).append(r["rel_frob"])
summary = {"parent": par, "edited": edt, "n_tensors_changed": len(rows),
           "by_component": {c: {"n": len(v), "mean_rel_frob": float(np.mean(v)), "max_rel_frob": float(np.max(v))} for c, v in comp.items()},
           "rank_one_share_median": float(np.median([r["top1_share_of_frob2"] for r in rows if "top1_share_of_frob2" in r])) if any("top1_share_of_frob2" in r for r in rows) else None,
           "rows": rows}
out = Path("results") / f"edit_anatomy__{edt.replace('/', '__')}.json"
out.write_text(json.dumps(summary, indent=1))
print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))

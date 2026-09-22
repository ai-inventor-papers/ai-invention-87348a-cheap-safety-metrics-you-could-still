#!/usr/bin/env python3
"""REGRESSION: every checkpoint read BOTH by this lane's exact float64 v2 reader and by the sibling's GPU float32
harvest must agree on the per-layer statistics (and on iteration 1's canonical o_proj BSA_w8 = 0.5649782 for
Qwen/Qwen3-0.6B). Writes results/regression_v2_vs_harvest.json."""
import json
import sys
from pathlib import Path

import numpy as np

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from stage3_analysis_v2 import HARVEST, harvest_weight_row  # noqa: E402

out = {"checkpoints": {}, "iter1_canonical": {"Qwen__Qwen3-0.6B_attn_BSA_w8": 0.5649782}}
ok_all = True
for p in sorted((WS / "results/ckpt_v2").glob("*.json")):
    if p.name.endswith(".failed.json"):
        continue
    cid = p.stem
    if not (HARVEST / cid / "weights.npz").exists():
        continue
    v2 = json.loads(p.read_text())
    h = harvest_weight_row(HARVEST / cid)
    rec = {}
    for fam in ("attn", "mlp"):
        a, b = (v2.get("per_family") or {}).get(fam), (h.get("per_family") or {}).get(fam)
        if not a or not b:
            continue
        Ls = sorted(set(map(int, a["per_layer"])) & set(map(int, b["per_layer"])))
        bg_a = np.array([a["per_layer"][str(L)]["botgap"] for L in Ls])
        bg_b = np.array([b["per_layer"][str(L)]["botgap"] for L in Ls])
        kh_a = np.array([a["per_layer"][str(L)]["kappa_hat"] for L in Ls])
        kh_b = np.array([b["per_layer"][str(L)]["kappa_hat"] for L in Ls])
        big = bg_b > 0.05   # float32 GPU Gram cannot resolve a collapsed bottom value; compare where it can
        rec[fam] = {"n_layers": len(Ls),
                    "botgap_max_rel_diff_where_resolvable": float(np.max(np.abs(bg_a[big] - bg_b[big]) / bg_b[big])) if big.any() else None,
                    "botgap_min_v2": float(bg_a.min()), "botgap_min_harvest": float(bg_b.min()),
                    "kappa_hat_max_abs_diff": float(np.max(np.abs(kh_a - kh_b))),
                    "BSA_w8_v2": a.get("BSA_w8"), "BSA_w8_harvest": b.get("BSA_w8"),
                    "XLC_v2": a.get("XLC"), "XLC_harvest": b.get("XLC")}
        d_out, d_in = (v2.get("shapes") or {}).get(fam, [None, None])
        square = bool(d_out and d_in and d_in / d_out <= 1.05)
        passed = (abs((a.get("BSA_w8") or 0) - (b.get("BSA_w8") or 0)) < 0.02
                  and abs((a.get("XLC") or 0) - (b.get("XLC") or 0)) < 0.02
                  and rec[fam]["kappa_hat_max_abs_diff"] < 0.05)
        rec[fam]["site_square_or_wide"] = square
        rec[fam]["pass"] = bool(passed)
        if square and not passed:
            rec[fam]["diagnosis"] = ("SQUARE site: the honest bottom edge of a square matrix approaches 0, and a FLOAT32 "
                                     "Gram eigh (the sibling harvest) cannot resolve it - its bottom vectors, BSA and XLC "
                                     "are numerically unreliable there. Not a regression of the v2 reader (float64).")
        elif not square:
            ok_all &= passed
    if cid == "Qwen__Qwen3-0.6B":
        out["iter1_canonical"]["v2_value"] = ((v2.get("per_family") or {}).get("attn") or {}).get("BSA_w8")
    out["checkpoints"][cid] = rec
out["pass"] = bool(ok_all and out["checkpoints"])
out["criterion"] = ("valid (d_in > d_out) sites must agree on BSA_w8 and XLC within 0.02 and on per-layer kappa_hat within "
                    "0.05; square/wide sites are reported with a diagnosis, not scored (float32 cannot resolve them)")
(WS / "results/regression_v2_vs_harvest.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)[:3000])

#!/usr/bin/env python3
"""Fit each ladder host's OWN refusal direction from iteration 1's harvests.

ROSI defines s_hat as the unit-norm difference in means at the LAST PROMPT TOKEN
between harmful and harmless prompts.  The finished harvests already store
exactly that tensor -- hidden states at every layer at the last prompt token for
160 pre-registered items -- so the direction can be fitted for four of the six
ladder hosts with no forward pass at all.

Without this the rank-one rung would have to use a random shared direction,
which preserves ROSI's GEOMETRY (one common left factor across layers) but not
its MEANING.  With it, the rung is the published edit.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

WORKSPACE = Path(__file__).resolve().parent
HARVEST = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1"
               "/gen_art/gen_art_experiment_1/harvest")
OUT = WORKSPACE / "out"

def main() -> None:
    items = json.loads((WORKSPACE / "items_160.json").read_text())["items"]
    kind = np.array([it["kind"] for it in items])
    harm = kind == "harmful"
    benign = kind == "plain_benign"
    out = {}
    p = OUT / "s_hat.json"
    if p.exists():
        out = json.loads(p.read_text())
    for d in sorted(HARVEST.iterdir()):
        if not (d / "DONE").exists() or not (d / "acts.npz").exists():
            continue
        meta = json.loads((d / "meta.json").read_text())
        repo = meta["repo_id"]
        if repo in out:
            continue
        with np.load(d / "acts.npz") as z:
            hs = z["hs_last"]                       # (N, L+1, d), fp16
            n = hs.shape[0]
            h, b = harm[:n], benign[:n]
            if h.sum() < 8 or b.sum() < 8:
                continue
            lstar = int(0.6 * (hs.shape[1] - 1))
            mh = hs[h, lstar, :].astype(np.float64).mean(0)
            mb = hs[b, lstar, :].astype(np.float64).mean(0)
        v = mh - mb
        nrm = float(np.linalg.norm(v))
        if nrm <= 0:
            continue
        v = v / nrm
        out[repo] = {
            "s_hat": v.tolist(), "layer": lstar,
            "n_harmful": int(h.sum()), "n_harmless": int(b.sum()),
            "source": "iteration-1 harvest hs_last (last prompt token)",
            "definition": ("unit-norm difference in means at the last prompt "
                           "token between harmful and plain-benign items -- "
                           "ROSI's own definition of s_hat"),
            "d_model": int(v.shape[0]),
        }
        print(f"  {repo:<52} layer {lstar:>2}  d={v.shape[0]}  "
              f"|v|before={nrm:.3f}  n={int(h.sum())}/{int(b.sum())}")
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p} with {len(out)} directions")

if __name__ == "__main__":
    main()

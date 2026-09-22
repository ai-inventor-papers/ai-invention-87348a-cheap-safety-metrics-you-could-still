#!/usr/bin/env python3
"""Probe records for ladder hosts that iteration 1 already harvested -- ZERO forward passes.

`behave2.py --stages probe` measures s_hat, l* and the residual scale with a
forward pass. For Qwen/Qwen3-0.6B and TinyLlama/TinyLlama-1.1B-Chat-v1.0 the same
three quantities are already on disk: iteration 1 stored the last-prompt-token
residual at every layer for the 160 pre-registered items (items_160.json order).
On a 2-CPU container shared with two sibling experiments a forward pass is the
scarcest resource in the study, so these hosts are probed from the harvest.

  s_hat_all[l] = unit(mean_harmful(h_l) - mean_plain_benign(h_l))    (ROSI's definition)
  l*           = held-out (2-fold) Cohen's d maximiser in 0.3L..0.8L (behave2.pick_lstar)
  resid scale  = median ||h_l|| over all 160 items

The CARRIER cannot come from the harvest (it needs down_proj INPUTS). It is taken
from the previous pass's one-forward-pass carrier probe (out/carrier.json: the
coordinate with the smallest coefficient of variation at the last prompt token
over 6 prompts), restricted to layers 1..L-2 exactly as behave2 restricts it, and
every record says so in `carrier_source`. That probe is weaker than behave2's
all-positions, 100-prompt probe; the difference is labelled, not hidden.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

WORKSPACE = Path(__file__).resolve().parent
OUT = WORKSPACE / "out"
PROBE = OUT / "probe"
HARVEST = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1"
               "/gen_art/gen_art_experiment_1/harvest")
SEED = 20260920
HOSTS = {"Qwen/Qwen3-0.6B": "Qwen3", "TinyLlama/TinyLlama-1.1B-Chat-v1.0": "TinyLlama"}


def pick_lstar(Hh: np.ndarray, Hb: np.ndarray) -> tuple[int, list[float]]:
    L1 = Hh.shape[1]
    lo, hi = max(1, int(0.3 * (L1 - 1))), max(2, int(0.8 * (L1 - 1)))
    rng = np.random.default_rng(SEED)
    ih, ib = rng.permutation(len(Hh)), rng.permutation(len(Hb))
    halves = [(ih[: len(ih) // 2], ib[: len(ib) // 2]), (ih[len(ih) // 2:], ib[len(ib) // 2:])]
    score = []
    for li in range(L1):
        ds = []
        for k in (0, 1):
            tr_h, tr_b = halves[k]
            te_h, te_b = halves[1 - k]
            v = Hh[tr_h, li].mean(0) - Hb[tr_b, li].mean(0)
            v /= max(np.linalg.norm(v), 1e-12)
            ph, pb = Hh[te_h, li] @ v, Hb[te_b, li] @ v
            sd = math.sqrt(0.5 * (ph.var() + pb.var())) + 1e-9
            ds.append((ph.mean() - pb.mean()) / sd)
        score.append(float(np.mean(ds)))
    return int(lo + np.argmax(score[lo:hi + 1])), score


def main() -> None:
    PROBE.mkdir(parents=True, exist_ok=True)
    items = json.loads((WORKSPACE / "items_160.json").read_text())["items"]
    kind = np.array([it["kind"] for it in items])
    carriers = json.loads((OUT / "carrier.json").read_text())
    for d in sorted(HARVEST.iterdir()):
        if not (d / "DONE").exists() or not (d / "acts.npz").exists():
            continue
        repo = json.loads((d / "meta.json").read_text())["repo_id"]
        if repo not in HOSTS:
            continue
        slug = repo.replace("/", "__")
        with np.load(d / "acts.npz") as z:
            hs = z["hs_last"].astype(np.float64)          # (N, L+1, d)
        n = hs.shape[0]
        harm, ben = kind[:n] == "harmful", kind[:n] == "plain_benign"
        Hh, Hb = hs[harm], hs[ben]
        lstar, dscore = pick_lstar(Hh, Hb)
        diff = Hh.mean(0) - Hb.mean(0)
        s_all = diff / np.maximum(np.linalg.norm(diff, axis=1, keepdims=True), 1e-12)
        resid = np.median(np.linalg.norm(hs, axis=2), axis=0)
        n_layers = hs.shape[1] - 1
        c = carriers.get(repo)
        carrier = None
        if c:
            pl = [r for r in c["per_layer_carrier"] if 1 <= int(r["layer"]) <= n_layers - 2
                  and abs(r["mean_j"]) > 1e-2]
            if pl:
                best = min(pl, key=lambda r: r["cv_j"])
                carrier = {"layer": int(best["layer"]), "carrier_index": int(c["carrier_index"]),
                           "mean_j": float(best["mean_j"]), "sd_j": float(best["sd_j"]),
                           "cv_j": float(best["cv_j"]), "usable": bool(best["cv_j"] <= 0.25),
                           "cv_cap": 0.25,
                           "carrier_source": ("previous pass's carrier probe (out/carrier.json): "
                                              "last prompt token, 6 prompts; coordinate "
                                              f"{c['carrier_index']} chosen at layer {c['layer']}, "
                                              "re-selected here among layers 1..L-2 with "
                                              "|m_j| > 0.01"),
                           "massive_activation_peak_ratio": c.get("peak_over_median_ratio"),
                           "literature_1000x_criterion_met": c.get("literature_1000x_criterion_met"),
                           "literature_magnitude_100_met": c.get("literature_magnitude_100_met")}
        np.savez_compressed(PROBE / f"{slug}.npz", s_hat_all=s_all.astype(np.float32))
        rec = {"repo": repo, "family": HOSTS[repo], "n_layers": int(n_layers),
               "d_model": int(hs.shape[2]), "l_star_residual_index": int(lstar),
               "heldout_cohens_d_per_layer": dscore, "s_hat": s_all[lstar].tolist(),
               "resid_norm_median_per_layer": resid.tolist(), "carrier": carrier,
               "n_fit_harmful": int(harm.sum()), "n_fit_harmless": int(ben.sum()),
               "source": ("iteration-1 harvest hs_last (last prompt token), items_160 "
                          "harmful vs plain_benign -- zero forward passes"),
               "definition": "s_hat = unit-norm difference in means at the LAST PROMPT TOKEN"}
        (PROBE / f"{slug}.json").write_text(json.dumps(rec, indent=1))
        print(f"{repo}: l*={lstar} d={dscore[lstar]:.2f} carrier="
              f"{(carrier or {}).get('layer')}/{(carrier or {}).get('carrier_index')} "
              f"cv={(carrier or {}).get('cv_j')}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Targeted test of Part 1 on REAL data: the readout bake-off only.

Loads the inherited harvests and the stance-framed judge grades and runs
`readout_bakeoff` directly, with no metric computation.  Cheap enough to run
beside a live harvest, and it exercises the one code path the smoke score
could not reach.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from screen.analysis2 import (  # noqa: E402
    crossfit_probe_scores, load_harvest_any, readout_bakeoff, select_probe_layer,
)


def main() -> int:
    items = json.loads((ROOT / "inherited/items.json").read_text())["items"]
    jg = json.loads((ROOT / "results/judge_grades.json").read_text())["per_checkpoint"]
    panel = {}
    sys.path.insert(0, str(ROOT))
    from method import build_panel
    panel = {r["slug"]: r for r in build_panel()}
    folds = np.array([int(it["fold"]) for it in items])

    rows = []
    for slug, g in sorted(jg.items()):
        hv = load_harvest_any(slug, ROOT / "harvest")
        if "a" not in hv:
            continue
        idx = g["item_idx"]
        y = np.full(len(items), np.nan)
        for j, i in enumerate(idx):
            r = g["full"][j]
            if r.get("refused") is not None:
                y[i] = float(r["refused"])
        m = np.isfinite(y)
        lf = hv["a"]["logit_feats"].astype(np.float64)
        short = np.full(len(items), np.nan)
        for j, i in enumerate(idx):
            r = g["short"][j]
            if r.get("refused") is not None:
                short[i] = float(r["refused"])
        rv = {"logitgap": lf[:, 0], "refmass": np.log(np.clip(lf[:, 1], 1e-12, None)),
              "greedy24": short}
        H = hv["a"]["hs_last"].astype(np.float32)
        try:
            lay = select_probe_layer(H[m], y[m].astype(int), folds[m])
            pc = np.full(len(items), np.nan)
            pc[m] = crossfit_probe_scores(H[m], y[m].astype(int), folds[m], lay)
            rv["probe_cf"] = pc
        except (ValueError, IndexError) as exc:
            print(f"  {slug}: probe failed {exc}")

        inv: dict[str, dict[str, float]] = {}
        pres = hv.get("presentation") or {}
        # probe_cf invariance via the stored wrapped hidden states (same logic as
        # screen/pipeline2.py); without it the strongest readout would be excluded
        # from selection for having no measurable invariance rather than on merit.
        if "probe_cf" in rv and "wrapped_hs_last" in pres:
            try:
                Hw = np.asarray(pres["wrapped_hs_last"], dtype=np.float32)
                nw = min(Hw.shape[0], len(items))
                mw = m[:nw]
                if mw.sum() >= 12:
                    pw = np.full(len(items), np.nan)
                    pw[:nw][mw] = crossfit_probe_scores(
                        Hw[:nw][mw], y[:nw][mw].astype(int), folds[:nw][mw], lay)
                    a_ = rv["probe_cf"][:nw][mw]
                    b_ = pw[:nw][mw]
                    ok = np.isfinite(a_) & np.isfinite(b_)
                    if ok.sum() >= 8:
                        rho = spearmanr(a_[ok], b_[ok]).statistic
                        if np.isfinite(rho):
                            inv.setdefault("probe_cf", {})["roleplay"] = float(rho)
                del Hw
            except (ValueError, IndexError, KeyError) as exc:
                print(f"  {slug}: probe invariance failed {exc}")
        for cond, key in (("roleplay", "wrapped_logit_feats"),
                          ("paraphrase", "paraphrase_logit_feats")):
            if key not in pres:
                continue
            v = np.asarray(pres[key], dtype=np.float64)
            for ro, pv, sv in (("logitgap", lf[:, 0], v[:, 0]),
                               ("refmass", np.log(np.clip(lf[:, 1], 1e-12, None)),
                                np.log(np.clip(v[:, 1], 1e-12, None)))):
                n = min(len(pv), len(sv))
                ok = np.isfinite(pv[:n]) & np.isfinite(sv[:n])
                if ok.sum() >= 8:
                    rho = spearmanr(pv[:n][ok], sv[:n][ok]).statistic
                    if np.isfinite(rho):
                        inv.setdefault(ro, {})[cond] = float(rho)
        p = panel.get(slug, {})
        rows.append({"slug": slug, "repo": g["repo"], "cls": p.get("cls", "?"),
                     "family": p.get("family", "?"),
                     "readouts": {k: v[m] for k, v in rv.items()},
                     "judged": {"y": y[m], "idx": np.where(m)[0]},
                     "invariance": inv,
                     "judge_calls": {"logitgap": 0.0, "refmass": 0.0, "probe_cf": 0.0,
                                     "greedy24": float(m.sum())}})
        del hv, H

    out = readout_bakeoff(rows)
    (ROOT / "results/bakeoff_standalone.json").write_text(json.dumps(out, indent=2, default=str))

    print(f"\n{len(rows)} checkpoints, readouts: {sorted(out['summary'])}")
    print(f"\n{'readout':10s} {'minAUC':>7s} {'meanAUC':>7s} {'minAUC_abl':>10s} "
          f"{'n<0.5':>5s} {'invMin':>7s} {'calls':>7s} {'bars':>5s}")
    for n, v in out["summary"].items():
        f = lambda x: f"{x:7.3f}" if isinstance(x, float) and x == x else "    nan"
        print(f"{n:10s} {f(v['min_auroc'])} {f(v['mean_auroc'])} {f(v['min_auroc_abliterated']):>10s} "
              f"{v['n_below_chance']:5d} {f(v['invariance_min'])} "
              f"{v['judge_calls_total']:7.0f} "
              f"{'A' if v['clears_auroc_bar'] else '-'}{'I' if v['clears_invariance_bar'] else '-'}")
    print(f"\nCHOSEN: {out['chosen']}   gate: {out['gate']}")
    print("\nper-checkpoint AUROC (chosen readout):")
    for t in out["table"]:
        if t["readout"] == out["chosen"]:
            print(f"  {t['repo'][:44]:44s} {t['cls']:12s} auroc="
                  f"{t['auroc'] if t['auroc'] == t['auroc'] else float('nan'):.3f} "
                  f"base_rate={t['base_rate']:.3f} {t['base_rate_verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

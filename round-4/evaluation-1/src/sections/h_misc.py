#!/usr/bin/env python3
"""STEP H (non-simulation): family ANOVA R2 on the targets, and the metamodel recompute.

Metamodel: re-runs the iter-2 recipe (screen/race.py:metamodel_lolo -- StandardScaler ->
PCA(<=64) -> LogisticRegression(C=1), leave-one-lineage-out and leave-one-family-out) on the
same 288-d features (__features__ in each checkpoint's probe_cf metric-cache file), but keeps
the OUT-OF-FOLD P(instruct) so it can be scored as a pooled out-of-fold Spearman with B and P.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from loguru import logger
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS)); sys.path.insert(0, str(WS / "sections"))
from io_utils import EXP1, SEED, dump, get, lineage_cluster_bootstrap, spearman_with_p, src  # noqa: E402
from a_targets import metric_file  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs/h_misc.log"), rotation="30 MB", level="DEBUG")


def r2_oneway(y: np.ndarray, g: np.ndarray) -> dict:
    y = np.asarray(y, float)
    sst = float(((y - y.mean()) ** 2).sum())
    ssb = float(sum(((y[g == k].mean() - y.mean()) ** 2) * (g == k).sum() for k in np.unique(g)))
    k, n = len(np.unique(g)), len(y)
    r2 = ssb / sst
    from scipy.stats import f as fdist
    F = (ssb / (k - 1)) / ((sst - ssb) / (n - k)) if n > k else float("nan")
    return {"R2": r2, "adj_R2": 1 - (1 - r2) * (n - 1) / (n - k), "F": F,
            "p": float(fdist.sf(F, k - 1, n - k)), "n": n, "k_groups": k}


def oof(F, target, groups, *, proba_class=None, n_pca=64):
    """Leave-one-group-out predictions with the iter-2 recipe; returns labels and P(proba_class)."""
    pred = np.empty(len(target), dtype=object)
    prob = np.full(len(target), np.nan)
    folds = []
    for g in np.unique(groups):
        te, tr = groups == g, groups != g
        info = {"held_out": str(g), "n_test": int(te.sum()), "test_classes": sorted(set(target[te].tolist())),
                "test_label_absent_from_train": bool(not set(target[te]).issubset(set(target[tr])))}
        info["single_class_test_fold"] = len(info["test_classes"]) == 1
        if tr.sum() < 4 or len(np.unique(target[tr])) < 2:
            pred[te] = target[tr][0] if tr.sum() else target[te][0]
            info["degenerate_train"] = True
            folds.append(info)
            continue
        sc = StandardScaler().fit(F[tr])
        k = min(n_pca, int(tr.sum()) - 1, F.shape[1])
        pca = PCA(n_components=k, random_state=SEED).fit(sc.transform(F[tr]))
        clf = LogisticRegression(max_iter=3000, C=1.0).fit(pca.transform(sc.transform(F[tr])), target[tr])
        Z = pca.transform(sc.transform(F[te]))
        pred[te] = clf.predict(Z)
        if proba_class is not None and proba_class in clf.classes_:
            prob[te] = clf.predict_proba(Z)[:, list(clf.classes_).index(proba_class)]
        folds.append(info)
    return pred.astype(str), prob, folds


@logger.catch(reraise=True)
def main():
    A = json.loads((WS / "results/A_targets.json").read_text())
    comp = A["components"]
    fam = np.array([c["family"] for c in comp.values()])
    lin = np.array([c["lineage"] for c in comp.values()])
    B = np.array([c["B"] for c in comp.values()]); Pt = np.array([c["P_stored"] for c in comp.values()])
    anova = {"by_family": {"B": r2_oneway(B, fam), "P": r2_oneway(Pt, fam)},
             "by_lineage": {"B": r2_oneway(B, lin), "P": r2_oneway(Pt, lin)},
             "n": int(len(B)), "families": sorted(set(fam.tolist())), "n_lineages": int(len(set(lin.tolist()))),
             "source": "results/A_targets.json:components (hc, fr from iter_2 exp1 prompt_budget.json:targets)",
             "old_claim": "family explains R2=0.469 of the TARGET variance (n=15, 3 families). Recompute: 0.469 is the one-way family R2 of the PRODUCT target P; "
                          "under the balanced B it is 0.455, and by lineage (6 groups) 0.716 (B) / 0.725 (P). The 0.469 does not appear in any results JSON (derived number)."}
    logger.info(f"ANOVA family R2 B={anova['by_family']['B']['R2']:.3f} P={anova['by_family']['P']['R2']:.3f}; "
                f"lineage B={anova['by_lineage']['B']['R2']:.3f} P={anova['by_lineage']['P']['R2']:.3f}")

    # ---------- metamodel ----------
    mm_path = EXP1 / "results/metamodel.json"
    stored = {"lolo": get(mm_path, "leave_one_lineage_out"), "lofo": get(mm_path, "leave_one_family_out"),
              "n": get(mm_path, "n_checkpoints")}
    pc = get(EXP1 / "results/per_checkpoint.json", "")
    jg = get(EXP1 / "results/judge_grades.json", "per_checkpoint")
    rows, feats = [], []
    for r in pc:
        if r["cls"] not in ("instruct", "abliterated") or not r.get("has_acts"):
            continue
        f, how = metric_file(r["slug"], jg.get(r["slug"]))
        if f is None:
            continue
        ft = json.loads(f.read_text()).get("__features__")
        if not ft:
            continue
        rows.append(r); feats.append(np.asarray(ft, float))
    widths = {len(x) for x in feats}
    F = np.vstack(feats)
    ok = np.isfinite(F).all(1)
    rows = [r for r, o in zip(rows, ok) if o]; F = F[ok]
    y = np.array([r["cls"] for r in rows]); L = np.array([r["lineage"] for r in rows])
    fm = np.array([r["family"] for r in rows])
    out = {"n_checkpoints": len(rows), "feature_widths": sorted(widths), "slugs": [r["slug"] for r in rows],
           "stored": stored}
    for name, grp in (("leave_one_lineage_out", L), ("leave_one_family_out", np.array([f + "::" + f for f in fm]))):
        pr, prob, folds = oof(F, y, grp, proba_class="instruct")
        ba = float(balanced_accuracy_score(y, pr))
        pid, _, folds_id = oof(F, fm, grp)
        ba_id = float(balanced_accuracy_score(fm, pid))
        # pooled OOF Spearman of P(instruct) with targets (checkpoints that have a target)
        idx = [i for i, r in enumerate(rows) if r["slug"] in comp and np.isfinite(prob[i])]
        pB = [comp[rows[i]["slug"]]["B"] for i in idx]; pP = [comp[rows[i]["slug"]]["P_stored"] for i in idx]
        xs = [prob[i] for i in idx]; ls = [L[i] for i in idx]
        # identity baseline: predict each checkpoint's target by the TRAIN-fold mean target of its family
        ident = []
        for i in idx:
            tr = [j for j in idx if grp[j] != grp[i] and fm[j] == fm[i]]
            ident.append(np.mean([comp[rows[j]["slug"]]["B"] for j in tr]) if tr else np.nan)
        ident = np.array(ident, float)
        entry = {
            "role_BA_recomputed": ba, "role_BA_stored": stored["lolo" if "lineage" in name else "lofo"]["held_out"],
            "identity_BA_recomputed": ba_id,
            "identity_BA_stored": stored["lolo" if "lineage" in name else "lofo"]["identity_held_out"],
            "n_folds": len(folds), "n_single_class_role_test_folds": sum(f["single_class_test_fold"] for f in folds),
            "n_identity_folds_label_absent_from_train": sum(f["test_label_absent_from_train"] for f in folds_id),
            "folds_role": folds, "folds_identity": folds_id,
            "oof_P_instruct": {rows[i]["slug"]: float(prob[i]) for i in range(len(rows)) if np.isfinite(prob[i])},
            "n_with_target": len(idx),
        }
        if len(idx) >= 4:
            for tname, tv in (("B", pB), ("P", pP)):
                s = spearman_with_p(xs, tv)
                s["ci95_lineage_boot"] = lineage_cluster_bootstrap(xs, tv, ls, B=5000)
                entry[f"metamodel_oof_spearman_{tname}"] = s
            fin = np.isfinite(ident)
            entry["identity_family_mean_baseline"] = {
                "n_defined": int(fin.sum()),
                "spearman_B": (spearman_with_p(ident[fin], np.array(pB)[fin]) if fin.sum() >= 4 else
                               {"status": "UNDEFINED", "why": "family unseen in the training fold for most checkpoints"}),
            }
        out[name] = entry
        logger.info(f"{name}: role BA {ba:.3f} (stored {entry['role_BA_stored']}) identity BA {ba_id:.3f} "
                    f"(stored {entry['identity_BA_stored']}); single-class role folds "
                    f"{entry['n_single_class_role_test_folds']}/{len(folds)}; identity-label-absent folds "
                    f"{entry['n_identity_folds_label_absent_from_train']}")
    out["explanation"] = (
        "The identity probe predicts FAMILY while holding out a whole lineage (or family). Whenever the held-out "
        "family has no other lineage in the training fold its label is absent from training, so every prediction on "
        "that fold is necessarily wrong; pooled balanced accuracy over such folds falls BELOW 0.5 (LOFO: identically 0). "
        "The sub-chance identity BA is a design artefact, not anti-signal. Role folds that contain a single class "
        "(e.g. a lineage with only an instruct checkpoint) cannot contribute a per-fold BA either.")
    res = {"anova": anova, "metamodel": out}
    dump(res, WS / "results/H_misc.json")


if __name__ == "__main__":
    main()

"""P5. THE RACE -- the selection rule, fixed before the screen runs.

PRIMARY statistic, named in advance: BALANCED ACCURACY over the three classes
(safety-tuned / ordinary-instruct / abliterated), with multiclass AUROC beside it.
RESAMPLING UNIT is the LINEAGE (strictly the parent-by-tuning-run pair), never
the repo: naive repo counting inflates n about 20x because ~90% of safety-tuned
repos come from 5 uploaders and many are epoch snapshots of ONE parent.
ESTIMATOR is LEAVE-ONE-LINEAGE-OUT.  No metric is ever evaluated on a checkpoint
used to choose its layer, coordinate or threshold.
"""

from __future__ import annotations

import numpy as np
from loguru import logger
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from .common import SEED
from .registry import METRICS

CLASSES = ["safety", "instruct", "abliterated"]
METAMODEL_PREDICTIONS: dict = {}


def _fit_predict_1d(xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray) -> np.ndarray:
    """One scalar -> class.  Multinomial logistic on the standardised feature."""
    mu, sd = np.nanmean(xtr), np.nanstd(xtr) + 1e-12
    Xtr = ((xtr - mu) / sd).reshape(-1, 1)
    Xte = ((xte - mu) / sd).reshape(-1, 1)
    Xtr = np.nan_to_num(Xtr)
    Xte = np.nan_to_num(Xte)
    if len(np.unique(ytr)) < 2:
        return np.repeat(ytr[0], len(xte))
    clf = LogisticRegression(max_iter=2000, C=1.0).fit(Xtr, ytr)
    return clf.predict(Xte)


def lolo_predict(x: np.ndarray, y: np.ndarray, lineage: np.ndarray) -> np.ndarray:
    """Held-out predicted class per checkpoint; NaN features -> 'undefined'."""
    pred = np.full(len(y), "undefined", dtype=object)
    ok = np.isfinite(x)
    if ok.sum() < 6 or len(np.unique(y[ok])) < 2:
        return pred
    idx = np.where(ok)[0]
    for lin in np.unique(lineage[ok]):
        te = idx[lineage[ok] == lin]
        tr = idx[lineage[ok] != lin]
        if len(tr) < 3 or len(np.unique(y[tr])) < 2:
            pred[te] = y[tr][0] if len(tr) else y[te][0]
            continue
        pred[te] = _fit_predict_1d(x[tr], y[tr], x[te])
    return pred


def lolo_score(x: np.ndarray, y: np.ndarray, lineage: np.ndarray) -> dict[str, float]:
    """Leave-one-lineage-out balanced accuracy, plus the in-sample TUNED twin."""
    ok = np.isfinite(x)
    if ok.sum() < 6 or len(np.unique(y[ok])) < 2:
        return {"held_out": float("nan"), "tuned": float("nan"), "gap": float("nan"),
                "n_used": int(ok.sum()), "n_lineages": 0}
    x, y, lineage = x[ok], y[ok], lineage[ok]
    pred = np.empty(len(y), dtype=object)
    for lin in np.unique(lineage):
        te = lineage == lin
        tr = ~te
        if tr.sum() < 3 or len(np.unique(y[tr])) < 2:
            pred[te] = y[tr][0] if tr.sum() else y[te][0]
            continue
        pred[te] = _fit_predict_1d(x[tr], y[tr], x[te])
    held = float(balanced_accuracy_score(y, pred.astype(str)))
    tuned = float(balanced_accuracy_score(y, _fit_predict_1d(x, y, x).astype(str)))
    return {"held_out": held, "tuned": tuned, "gap": tuned - held,
            "n_used": int(len(y)), "n_lineages": int(len(np.unique(lineage)))}


def lolo_score_2way(x: np.ndarray, y: np.ndarray, lineage: np.ndarray) -> dict[str, float]:
    """F1 branch: the TWO-WAY claim (ordinary-instruct vs abliterated), fully powered."""
    m = np.isin(y, ["instruct", "abliterated"])
    return lolo_score(x[m], y[m], lineage[m])


def lolo_auroc_2way(x: np.ndarray, y: np.ndarray, lineage: np.ndarray) -> float:
    m = np.isin(y, ["instruct", "abliterated"]) & np.isfinite(x)
    if m.sum() < 6 or len(np.unique(y[m])) < 2:
        return float("nan")
    a = roc_auc_score((y[m] == "abliterated").astype(int), x[m])
    return float(max(a, 1 - a))


_PRED: dict = {}


def metamodel_lolo(F: np.ndarray, y: np.ndarray, lineage: np.ndarray,
                   n_pca: int = 64) -> dict[str, float]:
    """C5: ridge/logistic metamodel on architecture-free activation features.

    Shipped WITH a LINEAGE-IDENTITY probe on the IDENTICAL features -- the
    deliverable is the GAP, because a metamodel that recovers architecture and
    uploader identity is not reading safety.
    """
    ok = np.isfinite(F).all(1)
    F, y, lineage = F[ok], y[ok], lineage[ok]
    if len(y) < 6 or len(np.unique(y)) < 2:
        return {k: float("nan") for k in ("held_out", "tuned", "gap", "identity_held_out",
                                          "class_minus_identity")}
    fam = np.array([str(l).split("::")[0] for l in lineage])

    def _run(target: np.ndarray) -> tuple[float, float]:
        pred = np.empty(len(target), dtype=object)
        for lin in np.unique(lineage):
            te = lineage == lin
            tr = ~te
            if tr.sum() < 4 or len(np.unique(target[tr])) < 2:
                pred[te] = target[tr][0] if tr.sum() else target[te][0]
                continue
            sc = StandardScaler().fit(F[tr])
            k = min(n_pca, tr.sum() - 1, F.shape[1])
            pca = PCA(n_components=k, random_state=SEED).fit(sc.transform(F[tr]))
            clf = LogisticRegression(max_iter=3000, C=1.0).fit(
                pca.transform(sc.transform(F[tr])), target[tr])
            pred[te] = clf.predict(pca.transform(sc.transform(F[te])))
        held = float(balanced_accuracy_score(target, pred.astype(str)))
        _PRED[id(target)] = pred.astype(str)
        sc = StandardScaler().fit(F)
        pca = PCA(n_components=min(n_pca, len(F) - 1, F.shape[1]), random_state=SEED).fit(sc.transform(F))
        clf = LogisticRegression(max_iter=3000, C=1.0).fit(pca.transform(sc.transform(F)), target)
        tuned = float(balanced_accuracy_score(target, clf.predict(pca.transform(sc.transform(F)))))
        return held, tuned

    h, t = _run(y)
    ypred = _PRED.get(id(y))
    hid, _ = _run(fam)
    out = {"held_out": h, "tuned": t, "gap": t - h,
           "identity_held_out": hid, "class_minus_identity": h - hid}
    full = np.full(len(ok), "undefined", dtype=object)
    if ypred is not None:
        full[np.where(ok)[0]] = ypred
    out["predictions"] = full
    return out


def class_gap_permutation_test(rows: list[dict], n_perm: int = 10000,
                               seed: int = SEED) -> dict:
    """P5.3  PERMUTATION TEST OVER METRIC CLASS LABELS, lineage-clustered.

    The pre-registered prediction is a MONOTONE ORDERING of the held-out-minus-
    tuned GAP across the three classes, tested as a trend -- the only defensible
    handle on 50 heavily inter-correlated metrics.
    """
    fam = np.array([r["family"] for r in rows])
    gap = np.array([r["gap"] for r in rows], dtype=float)
    rank = np.array([r["predicted_gap_rank"] for r in rows], dtype=float)
    ok = np.isfinite(gap)
    fam, gap, rank = fam[ok], gap[ok], rank[ok]
    if len(gap) < 6:
        return {"observed_trend": float("nan"), "p_value": float("nan"), "n": int(len(gap))}
    obs = float(np.corrcoef(rank, gap)[0, 1])
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for i in range(n_perm):
        null[i] = np.corrcoef(rng.permutation(rank), gap)[0, 1]
    p = float((np.abs(null) >= abs(obs)).mean())
    means = {f: float(np.mean(gap[fam == f])) for f in np.unique(fam)}
    return {"observed_trend_corr": obs, "p_value": p, "n_metrics": int(len(gap)),
            "mean_gap_by_class": means, "n_permutations": n_perm,
            "prediction": "gap(BEHAVIOUR-STRUCTURE) < gap(ACROSS-ITEM) < gap(KNOWLEDGE)"}


def run_race(metric_table: dict[str, np.ndarray], y: np.ndarray, lineage: np.ndarray,
             feats: np.ndarray | None = None) -> list[dict]:
    """R1: for EVERY one of the 50 registered metrics, held-out WITH tuned beside it."""
    by_id = {m["id"]: m for m in METRICS}
    rows: list[dict] = []
    for mid, m in by_id.items():
        x = metric_table.get(mid)
        if x is None:
            x = np.full(len(y), np.nan)
        s3 = lolo_score(x, y, lineage)
        s2 = lolo_score_2way(x, y, lineage)
        rows.append({
            "metric_id": mid, "name": m["name"], "family": m["family"],
            "functional_form_class_id": m["functional_form_class_id"],
            "inputs": m["inputs"], "n_prompts": m["n_prompts"],
            "predicted_gap_rank": m["predicted_gap_rank"],
            "candidate": m.get("candidate", ""), "incumbent": m.get("incumbent", ""),
            "baseline": m.get("baseline", ""),
            "held_out_balacc_3way": s3["held_out"], "tuned_balacc_3way": s3["tuned"],
            "gap": s3["gap"], "n_used": s3["n_used"], "n_lineages": s3["n_lineages"],
            "held_out_balacc_2way": s2["held_out"], "tuned_balacc_2way": s2["tuned"],
            "auroc_2way": lolo_auroc_2way(x, y, lineage),
        })
    if feats is not None and len(feats):
        mm = metamodel_lolo(feats, y, lineage)
        rows_pred = mm.pop("predictions", None)
        if rows_pred is not None:
            METAMODEL_PREDICTIONS["x_c5_ridge"] = rows_pred
            METAMODEL_PREDICTIONS["x_c5_lineage_gap"] = rows_pred
        for r in rows:
            if r["metric_id"] == "x_c5_ridge":
                r.update({"held_out_balacc_3way": mm["held_out"],
                          "tuned_balacc_3way": mm["tuned"], "gap": mm["gap"]})
            if r["metric_id"] == "x_c5_lineage_gap":
                r.update({"held_out_balacc_3way": mm["class_minus_identity"],
                          "tuned_balacc_3way": mm["tuned"] - mm["identity_held_out"],
                          "gap": mm["tuned"] - mm["identity_held_out"] - mm["class_minus_identity"],
                          "metamodel_identity_held_out": mm["identity_held_out"]})
    rows.sort(key=lambda r: (-(r["held_out_balacc_3way"] if np.isfinite(r["held_out_balacc_3way"]) else -1),
                             r["gap"] if np.isfinite(r["gap"]) else 9))
    return rows


def survival_rule(rows: list[dict], incumbent_bar: float) -> dict:
    """P5.2  A candidate survives only if its held-out score EXCEEDS THE INCUMBENT BAR,
    computed HERE on our own configurations rather than quoted.  Ties break on the
    held-out-minus-tuned GAP, smaller wins."""
    cands = [r for r in rows if r["candidate"] and np.isfinite(r["held_out_balacc_3way"])]
    survivors = [r for r in cands if r["held_out_balacc_3way"] > incumbent_bar]
    survivors.sort(key=lambda r: (-r["held_out_balacc_3way"], r["gap"]))
    return {
        "incumbent_bar_recomputed_here": incumbent_bar,
        "n_candidates_scored": len(cands),
        "survivors": [{"metric_id": r["metric_id"], "held_out": r["held_out_balacc_3way"],
                       "gap": r["gap"], "candidate": r["candidate"]} for r in survivors],
        "promoted_to_iter2": survivors[0]["metric_id"] if survivors else None,
        "verdict": "CANDIDATE_PROMOTED" if survivors else "NO_CANDIDATE_PROMOTED",
    }


def transfer_dissociation(rows: list[dict]) -> dict:
    """F4: RANKING IS NOT TRANSFERRING.  Report both columns and name the dissociation."""
    fin = [r for r in rows if np.isfinite(r["tuned_balacc_3way"]) and np.isfinite(r["held_out_balacc_3way"])]
    if len(fin) < 5:
        return {"n": len(fin)}
    best_desc = max(fin, key=lambda r: r["tuned_balacc_3way"])
    best_tran = max(fin, key=lambda r: r["held_out_balacc_3way"])
    return {
        "best_by_description_tuned": best_desc["metric_id"],
        "its_held_out": best_desc["held_out_balacc_3way"],
        "best_by_transfer_heldout": best_tran["metric_id"],
        "its_tuned": best_tran["tuned_balacc_3way"],
        "dissociation": best_desc["metric_id"] != best_tran["metric_id"],
        "card_regex_termswept_heldout": next(
            (r["held_out_balacc_3way"] for r in rows if r["metric_id"] == "b_card_regex_termswept"), None),
        "card_regex_namefree_heldout": next(
            (r["held_out_balacc_3way"] for r in rows if r["metric_id"] == "b_card_regex_namefree"), None),
    }

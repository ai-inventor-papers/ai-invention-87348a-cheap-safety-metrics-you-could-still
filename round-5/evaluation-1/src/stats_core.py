#!/usr/bin/env python3
"""Statistics core for the iter-5 final evaluation.

Ranks / partial Spearman / lineage-cluster bootstrap / paired bootstrap / label permutation / ICC / MDE /
LOFO. The rank, partial-Spearman, bootstrap and ICC functions are ported VERBATIM (same arithmetic, same RNG
consumption order) from iter_4/gen_art/gen_art_experiment_1/analyze_live.py, so the iter-4 numbers reproduce
bit-for-bit when rows are fed in the same order. Exact permutation p lives in perm_exact.py.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata

SEED = 20260921
N_BOOT = 2000
N_PERM = 2000


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.size < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def rank(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if np.isnan(x).any():
        raise ValueError("rank(): NaN present; caller must mask undefined entries first")
    return rankdata(x)


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.size < 2:
        return float("nan")
    return pearson(rank(a), rank(b))


def ols_resid_rank(y: np.ndarray, covariates: list[np.ndarray]) -> np.ndarray:
    """Rank-transform y, regress its ranks on [1, ranks(covariates)] by OLS, return residuals."""
    ry = rank(y)
    n = len(ry)
    X = np.column_stack([np.ones(n)] + [rank(c) for c in covariates])
    beta, *_ = np.linalg.lstsq(X, ry, rcond=None)
    return ry - X @ beta


def partial_spearman(value: np.ndarray, target: np.ndarray, covariates: list[np.ndarray]) -> float:
    if len(covariates) == 0:
        return spearman(value, target)
    rv = ols_resid_rank(value, covariates)
    rt = ols_resid_rank(target, covariates)
    return pearson(rv, rt)


def lineage_groups(lineages: np.ndarray) -> dict[Any, np.ndarray]:
    g: dict[Any, list[int]] = defaultdict(list)
    for i, lin in enumerate(lineages):
        g[lin].append(i)
    return {k: np.array(v) for k, v in g.items()}


def boot_indices(lineages: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> list[np.ndarray]:
    """Pre-drawn lineage-cluster resample index sets (identical RNG consumption to analyze_live.py)."""
    groups = lineage_groups(lineages)
    keys = list(groups.keys())
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_boot):
        draw = rng.integers(0, len(keys), size=len(keys))
        out.append(np.concatenate([groups[keys[i]] for i in draw]))
    return out


def boot_rho(value: np.ndarray, target: np.ndarray, lineages: np.ndarray, n_boot: int = N_BOOT,
             seed: int = SEED) -> dict:
    idxs = boot_indices(lineages, n_boot, seed)
    boots = np.full(n_boot, np.nan)
    for b, idx in enumerate(idxs):
        v, t = value[idx], target[idx]
        if np.std(v) == 0 or np.std(t) == 0 or len(v) < 3:
            continue
        boots[b] = spearman(v, t)
    valid = boots[~np.isnan(boots)]
    point = spearman(value, target)
    if valid.size == 0:
        return {"point": point, "ci_lo": float("nan"), "ci_hi": float("nan"), "n_boot": 0}
    lo, hi = np.percentile(valid, [2.5, 97.5])
    return {"point": point, "ci_lo": float(lo), "ci_hi": float(hi),
            "ci_lo_one_sided": float(np.percentile(valid, 5)), "n_boot": int(valid.size)}


def boot_partial(value: np.ndarray, target: np.ndarray, covariates: list[np.ndarray], lineages: np.ndarray,
                 n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """One-sided 5% lineage-bootstrap lower bound of the partial Spearman (value assumed ORIENTED)."""
    point = partial_spearman(value, target, covariates)
    idxs = boot_indices(lineages, n_boot, seed)
    boots = np.full(n_boot, np.nan)
    for b, idx in enumerate(idxs):
        if len(idx) < len(covariates) + 3:
            continue
        try:
            boots[b] = partial_spearman(value[idx], target[idx], [c[idx] for c in covariates])
        except (np.linalg.LinAlgError, ValueError):
            continue
    valid = boots[~np.isnan(boots)]
    if valid.size == 0:
        return {"point": point, "ci_lo_one_sided": float("nan"), "n_boot": 0}
    lo, hi = np.percentile(valid, [2.5, 97.5])
    return {"point": point, "ci_lo_one_sided": float(np.percentile(valid, 5)), "ci_lo": float(lo),
            "ci_hi": float(hi), "n_boot": int(valid.size)}


def boot_paired_delta(v1: np.ndarray, v2: np.ndarray, target: np.ndarray, lineages: np.ndarray,
                      n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """rho(v1,target) - rho(v2,target) with the SAME lineage resample indices for both reads."""
    idxs = boot_indices(lineages, n_boot, seed)
    d = np.full(n_boot, np.nan)
    for b, idx in enumerate(idxs):
        t = target[idx]
        a, c = v1[idx], v2[idx]
        if np.std(t) == 0 or np.std(a) == 0 or np.std(c) == 0:
            continue
        d[b] = spearman(a, t) - spearman(c, t)
    valid = d[~np.isnan(d)]
    point = spearman(v1, target) - spearman(v2, target)
    if valid.size == 0:
        return {"point": point, "ci_lo": float("nan"), "ci_hi": float("nan"), "n_boot": 0}
    lo, hi = np.percentile(valid, [2.5, 97.5])
    return {"point": float(point), "ci_lo": float(lo), "ci_hi": float(hi),
            "ci_lo_one_sided": float(np.percentile(valid, 5)), "n_boot": int(valid.size),
            "p_boot_le_0": float(np.mean(valid <= 0))}


def label_perm_p(value: np.ndarray, target: np.ndarray, sign: float, n_perm: int = N_PERM,
                 seed: int = SEED) -> dict:
    """Checkpoint-label permutation null of Spearman (analyze_live.checkpoint_perm_null)."""
    n = len(value)
    if n < 3 or np.std(value) == 0 or np.std(target) == 0:
        return {"observed": float("nan"), "p_one_sided": float("nan"), "n_perm": 0}
    rv, rt = rank(value), rank(target)
    observed = pearson(rv, rt)
    rng = np.random.default_rng(seed)
    perms = np.array([rng.permutation(n) for _ in range(n_perm)])
    rt_perm = rt[perms]
    rv_c = rv - rv.mean()
    rt_c = rt_perm - rt_perm.mean(axis=1, keepdims=True)
    null_rho = (rt_c * rv_c).sum(axis=1) / np.sqrt((rv_c ** 2).sum() * (rt_c ** 2).sum(axis=1))
    n_ge = int(np.sum(sign * null_rho >= sign * observed))
    return {"observed": float(observed), "p_one_sided": float((1 + n_ge) / (1 + n_perm)), "n_perm": n_perm}


def icc_oneway(target: np.ndarray, lineages: np.ndarray) -> dict:
    df = pd.DataFrame({"t": target, "lin": lineages})
    groups = df.groupby("lin")["t"]
    N = len(df)
    a = groups.ngroups
    if a < 2 or N <= a:
        return {"icc": 0.0, "icc_raw": float("nan"), "n_lineages": int(a), "mbar": N / a if a else float("nan"),
                "note": "degenerate"}
    grand = df["t"].mean()
    SSB = sum(len(g) * (g.mean() - grand) ** 2 for _, g in groups)
    SSW = sum(((g - g.mean()) ** 2).sum() for _, g in groups)
    MSB = SSB / (a - 1)
    MSW = SSW / (N - a)
    n_i = groups.size().values
    k0 = (1.0 / (a - 1)) * (N - (n_i ** 2).sum() / N)
    denom = MSB + (k0 - 1) * MSW
    icc_raw = (MSB - MSW) / denom if denom != 0 else 0.0
    return {"icc": float(np.clip(icc_raw, 0.0, 0.95)), "icc_raw": float(icc_raw), "n_lineages": int(a),
            "mbar": float(N / a), "note": None}


def mde_row(n: int, mbar: float, icc: float) -> dict:
    """MDE_rho = tanh((1.645+0.842)/sqrt(n_eff-3)), n_eff = n/(1+(mbar-1)*ICC)."""
    deff = 1.0 + (mbar - 1.0) * icc
    n_eff = n / deff
    mde = math.tanh((1.645 + 0.842) / math.sqrt(n_eff - 3)) if n_eff > 3 else float("nan")
    return {"n": int(n), "mbar": float(mbar), "icc": float(icc), "design_effect": float(deff),
            "n_eff": float(n_eff), "mde_rho": float(mde)}


def lofo_spearman(target: np.ndarray, value: np.ndarray, families: np.ndarray) -> dict:
    preds = np.full(len(target), np.nan)
    for fam in np.unique(families):
        train, test = families != fam, families == fam
        if train.sum() < 2:
            continue
        x, y = value[train], target[train]
        if np.std(x) == 0:
            preds[test] = y.mean()
        else:
            slope, intercept = np.polyfit(x, y, 1)
            preds[test] = intercept + slope * value[test]
    ok = ~np.isnan(preds)
    if ok.sum() < 3:
        return {"score": float("nan"), "n": int(ok.sum())}
    return {"score": spearman(target[ok], preds[ok]), "n": int(ok.sum())}


def lofo_family_only(target: np.ndarray, families: np.ndarray) -> dict:
    preds = np.full(len(target), np.nan)
    for fam in np.unique(families):
        train, test = families != fam, families == fam
        if train.sum() < 1:
            continue
        preds[test] = target[train].mean()
    ok = ~np.isnan(preds)
    if ok.sum() < 3:
        return {"score": float("nan"), "n": int(ok.sum())}
    return {"score": spearman(target[ok], preds[ok]), "n": int(ok.sum())}


def family_level_rho(value: np.ndarray, target: np.ndarray, families: np.ndarray) -> dict:
    df = pd.DataFrame({"v": value, "t": target, "f": families}).groupby("f").mean()
    return {"rho": spearman(df["v"].to_numpy(), df["t"].to_numpy()) if len(df) >= 3 else float("nan"),
            "n_fam": int(len(df))}


def auroc(score: np.ndarray, label: np.ndarray) -> float:
    """AUROC of score for binary label (ties count 0.5); nan if one class is empty."""
    score = np.asarray(score, float)
    label = np.asarray(label, bool)
    pos, neg = score[label], score[~label]
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[:pos.size].sum() - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))

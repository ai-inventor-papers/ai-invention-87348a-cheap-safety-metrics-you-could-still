"""Statistics: bootstraps at the right resampling unit, Williams' test, partial Spearman,
permutation nulls, and the anisotropy-matched random-direction null."""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np
from scipy import stats as sps

RNG_SEED = 20260920


def _clean_pair(x: Sequence[float], y: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    m = np.isfinite(xa) & np.isfinite(ya)
    return xa[m], ya[m]


def spearman(x: Sequence[float], y: Sequence[float]) -> dict[str, Any]:
    xa, ya = _clean_pair(x, y)
    if len(xa) < 3 or np.ptp(xa) == 0 or np.ptp(ya) == 0:
        return {"rho": None, "p": None, "n": int(len(xa)), "note": "degenerate"}
    r = sps.spearmanr(xa, ya)
    return {"rho": float(r.statistic), "p": float(r.pvalue), "n": int(len(xa))}


def pearson(x: Sequence[float], y: Sequence[float]) -> dict[str, Any]:
    xa, ya = _clean_pair(x, y)
    if len(xa) < 3 or np.ptp(xa) == 0 or np.ptp(ya) == 0:
        return {"r": None, "p": None, "n": int(len(xa)), "note": "degenerate"}
    r = sps.pearsonr(xa, ya)
    return {"r": float(r.statistic), "p": float(r.pvalue), "n": int(len(xa))}


def partial_spearman(x: Sequence[float], y: Sequence[float], z: Sequence[float]) -> dict[str, Any]:
    """Spearman(x, y) partialling out z, via rank residualisation (Spearman partial correlation)."""
    xa = np.asarray(x, float); ya = np.asarray(y, float); za = np.asarray(z, float)
    m = np.isfinite(xa) & np.isfinite(ya) & np.isfinite(za)
    xa, ya, za = xa[m], ya[m], za[m]
    if len(xa) < 4 or np.ptp(za) == 0:
        return {"rho": None, "p": None, "n": int(len(xa)), "note": "degenerate"}
    rx, ry, rz = (sps.rankdata(v) for v in (xa, ya, za))
    rxy = np.corrcoef(rx, ry)[0, 1]
    rxz = np.corrcoef(rx, rz)[0, 1]
    ryz = np.corrcoef(ry, rz)[0, 1]
    den = np.sqrt(max(1e-12, (1 - rxz**2) * (1 - ryz**2)))
    rho = float((rxy - rxz * ryz) / den)
    n = len(xa)
    if n > 4:
        t = rho * np.sqrt((n - 3) / max(1e-12, 1 - rho**2))
        p = float(2 * sps.t.sf(abs(t), df=n - 3))
    else:
        p = None
    return {"rho": rho, "p": p, "n": int(n)}


def cluster_bootstrap_spearman(
    x: Sequence[float],
    y: Sequence[float],
    clusters: Sequence[Any],
    n_boot: int = 10_000,
    seed: int = RNG_SEED,
) -> dict[str, Any]:
    """Bootstrap Spearman resampling whole CLUSTERS (lineages) with replacement.

    The resampling unit is the cluster, never the row: checkpoints from one lineage are
    not independent draws.
    """
    xa = np.asarray(x, float); ya = np.asarray(y, float)
    cl = np.asarray(list(clusters), dtype=object)
    m = np.isfinite(xa) & np.isfinite(ya)
    xa, ya, cl = xa[m], ya[m], cl[m]
    point = spearman(xa, ya)
    uniq = np.array(sorted({str(c) for c in cl}), dtype=object)
    idx_by_cluster = {str(c): np.where(cl == c)[0] for c in uniq}
    if len(uniq) < 3 or point["rho"] is None:
        return {**point, "ci_lo": None, "ci_hi": None, "n_clusters": int(len(uniq)),
                "resampling_unit": "lineage", "note": "too few clusters to bootstrap"}
    rng = np.random.default_rng(seed)
    draws: list[float] = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(uniq), size=len(uniq))
        rows = np.concatenate([idx_by_cluster[str(uniq[p])] for p in pick])
        if len(rows) < 3:
            continue
        bx, by = xa[rows], ya[rows]
        if np.ptp(bx) == 0 or np.ptp(by) == 0:
            continue
        draws.append(float(sps.spearmanr(bx, by).statistic))
    if len(draws) < 100:
        return {**point, "ci_lo": None, "ci_hi": None, "n_clusters": int(len(uniq)),
                "resampling_unit": "lineage", "note": "bootstrap degenerate"}
    arr = np.array(draws)
    return {
        **point,
        "ci_lo": float(np.nanpercentile(arr, 2.5)),
        "ci_hi": float(np.nanpercentile(arr, 97.5)),
        "boot_sd": float(np.nanstd(arr)),
        "n_clusters": int(len(uniq)),
        "n_boot_effective": int(len(draws)),
        "resampling_unit": "lineage",
    }


def paired_bootstrap_diff(
    a: Sequence[float], b: Sequence[float], n_boot: int = 10_000, seed: int = RNG_SEED
) -> dict[str, Any]:
    """Item-level paired bootstrap of mean(a) - mean(b); a and b are aligned per item."""
    aa = np.asarray(a, float); bb = np.asarray(b, float)
    m = np.isfinite(aa) & np.isfinite(bb)
    aa, bb = aa[m], bb[m]
    if len(aa) < 3:
        return {"diff": None, "n": int(len(aa)), "note": "too few paired items"}
    rng = np.random.default_rng(seed)
    n = len(aa)
    idx = rng.integers(0, n, size=(n_boot, n))
    diffs = aa[idx].mean(axis=1) - bb[idx].mean(axis=1)
    point = float(aa.mean() - bb.mean())
    se = float(diffs.std())
    return {
        "diff": point,
        "ci_lo": float(np.percentile(diffs, 2.5)),
        "ci_hi": float(np.percentile(diffs, 97.5)),
        "se": se,
        "n": int(n),
        "mean_a": float(aa.mean()),
        "mean_b": float(bb.mean()),
        "p_two_sided": float(2 * min((diffs <= 0).mean(), (diffs >= 0).mean())),
        # MDE at 80% power, alpha=.05, two-sided: (1.96+0.84)*SE
        "mde_80pct": float(2.802 * se) if se > 0 else None,
        "mde_note": "MDE = (z_{.975}+z_{.80}) * bootstrap SE = 2.802*SE",
    }


def williams_test(r_xy: float, r_xz: float, r_yz: float, n: int) -> dict[str, Any]:
    """Hotelling-Williams t for two DEPENDENT OVERLAPPING correlations.

    x = the outcome, y = readout, z = baseline. Tests H0: rho(x,y) == rho(x,z).
    Reference: Steiger (1980) eq. 14 / Williams (1959).
    """
    if n < 5 or not all(np.isfinite([r_xy, r_xz, r_yz])):
        return {"t": None, "p": None, "df": None, "note": "insufficient n"}
    for r in (r_xy, r_xz, r_yz):
        if abs(r) >= 1.0:
            return {"t": None, "p": None, "df": None, "note": "degenerate correlation (|r|>=1)"}
    detR = 1 - r_xy**2 - r_xz**2 - r_yz**2 + 2 * r_xy * r_xz * r_yz
    if detR <= 0:
        return {"t": None, "p": None, "df": None, "note": "non-positive-definite correlation matrix"}
    rbar = (r_xy + r_xz) / 2.0
    num = (r_xy - r_xz) * np.sqrt((n - 1) * (1 + r_yz))
    den = np.sqrt(2 * (n - 1) / (n - 3) * detR + rbar**2 * (1 - r_yz) ** 3)
    t = float(num / den) if den > 0 else None
    if t is None:
        return {"t": None, "p": None, "df": int(n - 3), "note": "zero denominator"}
    p = float(2 * sps.t.sf(abs(t), df=n - 3))
    return {"t": t, "p": p, "df": int(n - 3), "r_readout": float(r_xy),
            "r_baseline": float(r_xz), "r_between": float(r_yz), "n": int(n)}


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Rank-based AUROC; returns nan when a class is absent."""
    s = np.asarray(scores, float); y = np.asarray(labels, int)
    m = np.isfinite(s)
    s, y = s[m], y[m]
    npos, nneg = int((y == 1).sum()), int((y == 0).sum())
    if npos == 0 or nneg == 0:
        return float("nan")
    r = sps.rankdata(s)
    return float((r[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    aa = np.asarray(a, float); bb = np.asarray(b, float)
    aa, bb = aa[np.isfinite(aa)], bb[np.isfinite(bb)]
    if len(aa) < 2 or len(bb) < 2:
        return float("nan")
    s = np.sqrt(((len(aa) - 1) * aa.var(ddof=1) + (len(bb) - 1) * bb.var(ddof=1)) / (len(aa) + len(bb) - 2))
    return float((aa.mean() - bb.mean()) / s) if s > 0 else float("nan")


def cohens_kappa(a: Sequence[int], b: Sequence[int]) -> dict[str, Any]:
    aa = np.asarray(a, int); bb = np.asarray(b, int)
    if len(aa) == 0 or len(aa) != len(bb):
        return {"kappa": None, "n": int(len(aa))}
    po = float((aa == bb).mean())
    labels = sorted(set(aa.tolist()) | set(bb.tolist()))
    pe = sum(float((aa == k).mean()) * float((bb == k).mean()) for k in labels)
    k = (po - pe) / (1 - pe) if (1 - pe) > 1e-12 else float("nan")
    return {"kappa": float(k), "po": po, "pe": float(pe), "n": int(len(aa))}


def anisotropy_matched_null(
    H: np.ndarray, statistic_fn, n_draws: int = 200, seed: int = RNG_SEED, eps: float = 1e-4
) -> dict[str, Any]:
    """Random directions drawn to MATCH the empirical covariance of the residual stream.

    The residual stream is strongly anisotropic, so an isotropic null is wrong and makes
    everything look significant. Both nulls are returned so the reader sees how much the
    matching mattered.
    """
    rng = np.random.default_rng(seed)
    Hc = H - H.mean(axis=0, keepdims=True)
    d = Hc.shape[1]
    C = (Hc.T @ Hc) / max(1, Hc.shape[0] - 1)
    scale = float(np.trace(C) / d) if d else 1.0
    try:
        L = np.linalg.cholesky(C + eps * scale * np.eye(d))
    except np.linalg.LinAlgError:
        w, V = np.linalg.eigh(C + eps * scale * np.eye(d))
        L = V @ np.diag(np.sqrt(np.clip(w, 0, None)))
    aniso, iso = [], []
    for _ in range(n_draws):
        g = rng.standard_normal(d)
        v = L @ g
        nv = np.linalg.norm(v)
        if nv > 0:
            aniso.append(float(statistic_fn(v / nv)))
        g2 = rng.standard_normal(d)
        iso.append(float(statistic_fn(g2 / np.linalg.norm(g2))))
    a = np.array(aniso, float); i = np.array(iso, float)
    return {
        "anisotropic": {"mean": float(np.nanmean(a)), "sd": float(np.nanstd(a)),
                        "q95": float(np.nanpercentile(a, 95)), "q99": float(np.nanpercentile(a, 99)),
                        "n_draws": int(len(a))},
        "isotropic": {"mean": float(np.nanmean(i)), "sd": float(np.nanstd(i)),
                      "q95": float(np.nanpercentile(i, 95)), "q99": float(np.nanpercentile(i, 99)),
                      "n_draws": int(len(i))},
        "cov_condition_number": float(np.linalg.cond(C + eps * scale * np.eye(d))),
        "_aniso_draws": a.tolist(),
        "_iso_draws": i.tolist(),
    }


def percentile_of(value: float, draws: Sequence[float]) -> float | None:
    arr = np.asarray(draws, float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0 or not np.isfinite(value):
        return None
    return float((arr <= value).mean() * 100.0)


def zscore_of(value: float, draws: Sequence[float]) -> float | None:
    arr = np.asarray(draws, float)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 2 or not np.isfinite(value):
        return None
    sd = float(arr.std(ddof=1))
    return float((value - arr.mean()) / sd) if sd > 0 else None

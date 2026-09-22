"""Shared primitives: paths, harvest IO, folds, vectorised AUROC, shrinkage algebra.

Everything here is CPU-only and reads the iteration-1 harvest READ-ONLY.
The upstream workspace is never written to.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

# --- paths -----------------------------------------------------------------
UP = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1"
          "/gen_art/gen_art_experiment_1")
WS = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2"
          "/gen_art/gen_art_evaluation_1")
HARVEST = UP / "harvest"          # READ-ONLY
UP_RESULTS = UP / "results"       # READ-ONLY
RESULTS = WS / "results"
LOGS = WS / "logs"

SEED = 20260920

# --- pre-registered constants ---------------------------------------------
B_NULL = 1000            # null draws per (checkpoint, readout, tier)
B_PERM = 1000            # label permutations
B_BOOT = 2000            # lineage-clustered bootstrap resamples
B_SPLITHALF = 200        # split-half reliability draws
PRIMARY_DEPTH_FRACTION = 0.60    # fixed read layer -- NO per-checkpoint selection
LW_SHRINK_FLOOR = 1e-6

# D2.7 pre-registered survival bands over 17 checkpoints
SURV_SURVIVES_MIN = 13
SURV_PREMISE_FAILS_MAX = 9

# iteration-1 matched lexical floors
LEXFLOOR = {
    "lexfloor_jbb_index_paired": 0.53662109375,
    "lexfloor_xstest_twins": 0.6552734375,
    "lexfloor_cross_source": 0.96337890625,
}

DONE_SLUGS = [
    "AIPlans__TinyLlama-1.1B-IPO-PKU-SafeRLHF",
    "AIPlans__TinyLlama-1.1B-ORPO-PKU-SafeRLHF",
    "AIPlans__tinyllama-1.1b-dpo-pku-saferlhf",
    "DreamFast__qwen3-4b-heretic",
    "Qwen__Qwen3-0.6B",
    "Qwen__Qwen3-0.6B-Base",
    "Qwen__Qwen3-1.7B",
    "Qwen__Qwen3-1.7B-Base",
    "Qwen__Qwen3-4B",
    "Qwen__Qwen3-4B-Base",
    "Qwen__Qwen3-4B-SafeRL",
    "Shortmund09__MLDM-TinyLlama-1.1b-gcpo-ocra-saferlhf",
    "TinyLlama__TinyLlama-1.1B-Chat-v1.0",
    "TinyLlama__TinyLlama-1.1B-intermediate-step-1431k-3T",
    "huihui-ai__Huihui-Qwen3-0.6B-abliterated-v2",
    "huihui-ai__Huihui-Qwen3-1.7B-abliterated-v2",
    "mlabonne__Qwen3-4B-abliterated",
]


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, obj: Any, *, indent: int = 2) -> Path:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=indent, ensure_ascii=False, default=_jdefault),
                 encoding="utf-8")
    return p


def _jdefault(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if np.isfinite(v) else None
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(o: Any) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False,
                                     default=_jdefault).encode()).hexdigest()


# --- items -----------------------------------------------------------------
def load_items() -> list[dict]:
    return read_json(UP_RESULTS / "items.json")["items"]


def item_arrays(items: list[dict], n: int) -> dict[str, np.ndarray]:
    it = items[:n]
    return {
        "kind": np.array([x["kind"] for x in it]),
        "fold": np.array([x["fold"] for x in it]),
        "category": np.array([x["category"] for x in it]),
        "twin_group": np.array([x["twin_group"] for x in it]),
        "source": np.array([x["source"] for x in it]),
        "id": np.array([x["id"] for x in it]),
    }


def grouped_stratified_folds(twin: np.ndarray, strat: np.ndarray, n_folds: int,
                             seed: int) -> np.ndarray:
    """Fold assignment that never splits a twin_group and balances `strat`.

    Greedy: groups are shuffled inside each stratum then dealt round-robin to the
    fold that currently holds the fewest members of that stratum.
    """
    rng = np.random.default_rng(seed)
    folds = np.full(len(twin), -1, dtype=int)
    # one stratum label per GROUP (the modal stratum of its members)
    groups: dict[str, np.ndarray] = {}
    for g in np.unique(twin):
        groups[g] = np.where(twin == g)[0]
    counts = {f: {} for f in range(n_folds)}
    gnames = list(groups)
    rng.shuffle(gnames)
    # bigger groups first so they cannot be stranded
    gnames.sort(key=lambda g: -len(groups[g]))
    for g in gnames:
        idx = groups[g]
        vals, cts = np.unique(strat[idx], return_counts=True)
        s = str(vals[int(np.argmax(cts))])
        best = min(range(n_folds),
                   key=lambda f: (counts[f].get(s, 0), sum(counts[f].values())))
        folds[idx] = best
        counts[best][s] = counts[best].get(s, 0) + len(idx)
    return folds


def folds_respect_groups(folds: np.ndarray, twin: np.ndarray) -> dict[str, Any]:
    """Does any twin_group straddle a fold boundary?"""
    bad = []
    for g in np.unique(twin):
        m = twin == g
        if len(np.unique(folds[m])) > 1:
            bad.append({"twin_group": str(g), "size": int(m.sum()),
                        "folds": sorted(int(f) for f in np.unique(folds[m]))})
    return {"n_groups": int(len(np.unique(twin))), "n_straddling": len(bad),
            "respects_groups": len(bad) == 0, "straddling": bad[:25]}


def fold_stratification(folds: np.ndarray, strat: np.ndarray) -> dict[str, Any]:
    """Chi-square-free description: per-fold composition and the max deviation."""
    tab: dict[str, dict[str, int]] = {}
    for f in sorted(np.unique(folds)):
        vals, cts = np.unique(strat[folds == f], return_counts=True)
        tab[str(int(f))] = {str(v): int(c) for v, c in zip(vals, cts)}
    overall = {}
    vals, cts = np.unique(strat, return_counts=True)
    for v, c in zip(vals, cts):
        overall[str(v)] = int(c)
    nf = len(np.unique(folds))
    worst = 0.0
    for v, c in overall.items():
        exp = c / nf
        for f in tab:
            worst = max(worst, abs(tab[f].get(v, 0) - exp) / max(exp, 1e-9))
    return {"per_fold": tab, "overall": overall,
            "max_relative_deviation_from_even": round(float(worst), 4)}


# --- harvest IO ------------------------------------------------------------
def load_acts(slug: str) -> dict[str, np.ndarray]:
    with np.load(HARVEST / slug / "acts.npz") as z:
        return {k: z[k] for k in z.files}


def load_meta(slug: str) -> dict:
    return read_json(HARVEST / slug / "meta.json")


def load_weights(slug: str) -> dict[str, np.ndarray]:
    with np.load(HARVEST / slug / "weights.npz") as z:
        return {k: z[k] for k in z.files}


def layer_at_depth(n_layer_slots: int, frac: float) -> int:
    """Index into the (L+1) hidden-state stack at a given depth fraction."""
    return int(round(frac * (n_layer_slots - 1)))


# --- vectorised AUROC ------------------------------------------------------
def auc_many(y: np.ndarray, S: np.ndarray) -> np.ndarray:
    """AUROC of every COLUMN of S against binary y, via ranks. Ties handled.

    y: (n,) 0/1.  S: (n, B).  Returns (B,).  Rows with any non-finite score in a
    column make that column NaN.
    """
    y = np.asarray(y).astype(int)
    n_pos = int(y.sum())
    n_neg = int(len(y) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return np.full(S.shape[1], np.nan)
    finite = np.isfinite(S).all(0)
    R = _rank_columns(np.where(np.isfinite(S), S, 0.0))
    pos_rank_sum = R[y == 1].sum(0)
    auc = (pos_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    auc = np.where(finite, auc, np.nan)
    return auc


def _rank_columns(S: np.ndarray) -> np.ndarray:
    """Average ranks (1-based) down each column -- vectorised scipy.rankdata."""
    n, b = S.shape
    order = np.argsort(S, axis=0, kind="stable")
    ranks = np.empty((n, b), dtype=np.float64)
    ar = np.arange(1, n + 1, dtype=np.float64)[:, None]
    np.put_along_axis(ranks, order, np.broadcast_to(ar, (n, b)).copy(), axis=0)
    # average ties
    Ss = np.take_along_axis(S, order, axis=0)
    for j in range(b):
        col = Ss[:, j]
        i = 0
        while i < n:
            k = i + 1
            while k < n and col[k] == col[i]:
                k += 1
            if k - i > 1:
                avg = (i + k + 1) / 2.0
                ranks[order[i:k, j], j] = avg
            i = k
    return ranks


def auc_one(y: np.ndarray, s: np.ndarray) -> float:
    m = np.isfinite(s)
    if m.sum() < 4 or len(np.unique(np.asarray(y)[m])) < 2:
        return float("nan")
    a = auc_many(np.asarray(y)[m], np.asarray(s)[m][:, None])[0]
    return float(a)


# --- direction primitives --------------------------------------------------
def dim_direction(Xp: np.ndarray, Xn: np.ndarray) -> np.ndarray:
    d = Xp.mean(0) - Xn.mean(0)
    nrm = np.linalg.norm(d)
    return d / nrm if nrm > 0 else d


def ledoit_wolf_lowrank(Xc: np.ndarray) -> dict[str, Any]:
    """Ledoit-Wolf shrinkage target/intensity for S = Xc^T Xc / n, kept LOW-RANK.

    d is 960-2560 and n is at most ~130, so S is rank-deficient and never formed
    densely.  Returns the pieces needed for exact Sigma^{-1} v and Sigma^{1/2} z
    through the Woodbury identity and the n x n Gram eigendecomposition.
    """
    n, d = Xc.shape
    G = Xc @ Xc.T / n                       # (n, n), same nonzero spectrum as S
    trS = float(np.trace(G))
    mu = trS / d                            # target = mu * I
    # Ledoit-Wolf (2004) shrinkage intensity, computed from the low-rank form
    fro_S2 = float((G * G).sum())           # ||S||_F^2
    beta_num = 0.0
    sq = (Xc * Xc).sum(1)                   # ||x_i||^2
    # E||x x^T - S||_F^2 / n^2  =  (1/n^2) sum_i ||x_i||^4  -  ||S||_F^2 / n
    beta_num = float((sq ** 2).sum()) / (n ** 2) - fro_S2 / n
    delta = fro_S2 - 2.0 * mu * trS + d * mu * mu
    lam = 0.0 if delta <= 0 else float(np.clip(beta_num / delta, 0.0, 1.0))
    a = lam * mu                            # isotropic floor
    c = (1.0 - lam) / n                     # Sigma = a I + c Xc^T Xc
    a = max(a, LW_SHRINK_FLOOR * max(mu, 1e-12))
    evals, evecs = np.linalg.eigh(G * n)    # eigh of Xc Xc^T  (n x n)
    evals = np.clip(evals, 0.0, None)
    return {"Xc": Xc, "a": a, "c": c, "lam": lam, "mu": mu,
            "evals": evals, "evecs": evecs, "n": n, "d": d}


def lw_solve(lw: dict, V: np.ndarray) -> np.ndarray:
    """Sigma^{-1} V for V of shape (d, m), exactly, via Woodbury."""
    Xc, a, c, n = lw["Xc"], lw["a"], lw["c"], lw["n"]
    BtV = Xc @ V                                   # (n, m)
    M = np.eye(n) + (c / a) * (Xc @ Xc.T)          # (n, n)
    Z = np.linalg.solve(M, BtV)                    # (n, m)
    return (V - (c / a) * (Xc.T @ Z)) / a


def lw_sqrt_apply(lw: dict, Z: np.ndarray) -> np.ndarray:
    """Sigma^{1/2} Z for Z of shape (d, m): draws ~ N(0, Sigma) from N(0, I)."""
    Xc, a, c = lw["Xc"], lw["a"], lw["c"]
    ev, Q = lw["evals"], lw["evecs"]               # eigh(Xc Xc^T)
    keep = ev > 1e-12 * max(ev.max(), 1e-30)
    ev, Q = ev[keep], Q[:, keep]
    U = (Xc.T @ Q) / np.sqrt(ev)[None, :]          # (d, r) orthonormal
    scale = np.sqrt(a + c * ev) - np.sqrt(a)       # (r,)
    return np.sqrt(a) * Z + U @ (scale[:, None] * (U.T @ Z))


def normalise_cols(D: np.ndarray) -> np.ndarray:
    return D / (np.linalg.norm(D, axis=0, keepdims=True) + 1e-12)


# --- statistics ------------------------------------------------------------
def wilson_ci(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (float(max(0.0, ctr - hw)), float(min(1.0, ctr + hw)))


def cluster_bootstrap_ci(values: np.ndarray, clusters: np.ndarray, *, B: int = B_BOOT,
                         seed: int = SEED, stat=np.nanmean) -> dict[str, float]:
    """Resample CLUSTERS (lineages) with replacement; percentile CI of `stat`."""
    values = np.asarray(values, dtype=float)
    clusters = np.asarray(clusters)
    uc = np.unique(clusters)
    if len(uc) < 2:
        return {"point": float(stat(values)) if len(values) else float("nan"),
                "lo": float("nan"), "hi": float("nan"), "n_clusters": int(len(uc)), "B": B}
    idx_by = {c: np.where(clusters == c)[0] for c in uc}
    rng = np.random.default_rng(seed)
    out = np.empty(B)
    for b in range(B):
        pick = rng.choice(uc, size=len(uc), replace=True)
        sel = np.concatenate([idx_by[c] for c in pick])
        v = values[sel]
        out[b] = stat(v) if np.isfinite(v).any() else np.nan
    return {"point": float(stat(values)), "lo": float(np.nanpercentile(out, 2.5)),
            "hi": float(np.nanpercentile(out, 97.5)), "n_clusters": int(len(uc)), "B": B}


def detectable_rho(n: int) -> float:
    """|rho| a Spearman test can detect at n, Fisher-z with the 1.06 inflation."""
    if n <= 3:
        return float("nan")
    return float(np.tanh(1.959963985 * np.sqrt(1.06 / (n - 3))))


def corr_pair(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """Pearson AND Spearman with Fisher-z CIs, plus the detectable |rho| at this n."""
    from scipy import stats as sps
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    n = int(m.sum())
    out: dict[str, Any] = {"n": n, "detectable_abs_rho_at_this_n": detectable_rho(n)}
    if n < 4 or np.std(x[m]) == 0 or np.std(y[m]) == 0:
        out.update({"pearson_r": None, "pearson_p": None, "pearson_ci": [None, None],
                    "spearman_rho": None, "spearman_p": None, "spearman_ci": [None, None]})
        return out
    pr = sps.pearsonr(x[m], y[m])
    sr = sps.spearmanr(x[m], y[m])
    out["pearson_r"], out["pearson_p"] = float(pr[0]), float(pr[1])
    out["pearson_ci"] = list(_fisher_ci(pr[0], n, 1.0))
    out["spearman_rho"], out["spearman_p"] = float(sr[0]), float(sr[1])
    out["spearman_ci"] = list(_fisher_ci(sr[0], n, 1.06))
    return out


def _fisher_ci(r: float, n: int, inflation: float) -> tuple[float, float]:
    if n <= 3 or not np.isfinite(r) or abs(r) >= 1:
        return (float("nan"), float("nan"))
    z = np.arctanh(r)
    se = np.sqrt(inflation / (n - 3))
    return (float(np.tanh(z - 1.959963985 * se)), float(np.tanh(z + 1.959963985 * se)))


def bh_fdr(pvals: list[float]) -> list[float]:
    """Benjamini-Hochberg q-values; NaN p-values pass through as NaN."""
    p = np.asarray(pvals, dtype=float)
    ok = np.isfinite(p)
    q = np.full(len(p), np.nan)
    if ok.sum() == 0:
        return q.tolist()
    idx = np.where(ok)[0]
    order = idx[np.argsort(p[idx])]
    m = len(order)
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        val = min(prev, p[i] * m / (rank + 1))
        q[i] = val
        prev = val
    return q.tolist()

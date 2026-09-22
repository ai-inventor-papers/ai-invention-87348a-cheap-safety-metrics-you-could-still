"""Shared helpers: provenance-recording reads, cluster bootstrap, Wilson CI, Spearman."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from scipy import stats

WS = Path(__file__).resolve().parent
R = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop")
EXP1 = R / "iter_2/gen_art/gen_art_experiment_1"
EXP2 = R / "iter_2/gen_art/gen_art_experiment_2"
EXP3 = R / "iter_2/gen_art/gen_art_experiment_3"
EVAL2 = R / "iter_2/gen_art/gen_art_evaluation_1"
DS3 = R / "iter_3/gen_art/gen_art_dataset_1"
EVAL3 = R / "iter_3/gen_art/gen_art_evaluation_1"
SEED = 20260921

PROVENANCE: list[list[Any]] = []
_CACHE: dict[str, Any] = {}


def short(p: Path | str) -> str:
    """Path relative to the run's invention-loop root, for compact provenance."""
    s = str(p)
    return s.replace(str(R) + "/", "")


def load(path: Path | str) -> Any:
    key = str(path)
    if key not in _CACHE:
        _CACHE[key] = json.loads(Path(path).read_text())
    return _CACHE[key]


def get(path: Path | str, key_path: str | Sequence[Any] = "", record: bool = True) -> Any:
    """Read `key_path` (dot-separated or list; ints index lists) from JSON file; log provenance."""
    obj = load(path)
    keys = key_path.split(".") if isinstance(key_path, str) else list(key_path)
    for k in keys:
        if k == "" or k is None:
            continue
        if isinstance(obj, list):
            obj = obj[int(k)]
        else:
            obj = obj[k]
    if record:
        val = obj if isinstance(obj, (int, float, str, bool)) or obj is None else f"<{type(obj).__name__}>"
        PROVENANCE.append([short(path), ".".join(map(str, keys)), val])
    return obj


def src(path: Path | str, key_path: str) -> str:
    return f"{short(path)}:{key_path}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def _rank(a: np.ndarray) -> np.ndarray:
    return stats.rankdata(a, axis=-1)


def spearman_with_p(x: Sequence[float], y: Sequence[float], n_perm: int = 10000,
                    seed: int = SEED) -> dict:
    """Spearman rho, scipy analytic p, and two-sided permutation p (vectorised)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    n = len(x)
    if n < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return {"rho": float("nan"), "p": float("nan"), "p_perm": float("nan"), "n": int(n)}
    r = stats.spearmanr(x, y)
    rx, ry = _rank(x), _rank(y)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    if n <= 8:  # exact enumeration of all n! permutations (n=5 -> 120)
        import itertools
        perms = np.array(list(itertools.permutations(range(n))))
        n_perm = 0  # flag: exact
    else:
        rng = np.random.default_rng(seed)
        perms = np.argsort(rng.random((n_perm, n)), axis=1)
    ryp = ry[perms]
    rxc = rx - rx.mean()
    rypc = ryp - ryp.mean(axis=1, keepdims=True)
    rp = (rypc @ rxc) / (np.sqrt((rypc ** 2).sum(1)) * np.sqrt((rxc ** 2).sum()))
    if n_perm == 0:
        p_perm = float(np.mean(np.abs(rp) >= abs(rho) - 1e-12))
        kind = f"exact ({len(perms)} permutations)"
    else:
        p_perm = (1 + np.sum(np.abs(rp) >= abs(rho) - 1e-12)) / (n_perm + 1)
        kind = f"Monte Carlo ({n_perm} permutations)"
    return {"rho": float(r.statistic), "p": float(r.pvalue), "p_perm": float(p_perm), "n": int(n),
            "perm_kind": kind}


def fast_spearman(x: np.ndarray, y: np.ndarray) -> float:
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    return float(np.corrcoef(_rank(x), _rank(y))[0, 1])


def lineage_cluster_bootstrap(x: Sequence[float], y: Sequence[float], lineage: Sequence[str],
                              B: int = 5000, seed: int = SEED, min_unique: int = 4,
                              stat=None) -> dict:
    """Resample lineages with replacement; recompute Spearman; discard degenerate draws."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    lin = np.asarray(lineage)
    m = np.isfinite(x) & np.isfinite(y)
    x, y, lin = x[m], y[m], lin[m]
    stat = stat or fast_spearman
    groups = sorted(set(lin.tolist()))
    idx_by = {g: np.where(lin == g)[0] for g in groups}
    rng = np.random.default_rng(seed)
    vals, disc = [], 0
    for _ in range(B):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([idx_by[groups[i]] for i in pick])
        if len(np.unique(idx)) < min_unique:
            disc += 1
            continue
        v = stat(x[idx], y[idx])
        if not np.isfinite(v):
            disc += 1
            continue
        vals.append(v)
    if len(vals) < 50:
        return {"ci": [float("nan"), float("nan")], "n_valid": len(vals), "n_discarded": disc,
                "B": B, "n_lineages": len(groups)}
    return {"ci": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))],
            "n_valid": len(vals), "n_discarded": disc, "B": B, "n_lineages": len(groups)}


def clean(o: Any) -> Any:
    """Recursively make JSON-safe (NaN/inf -> None, numpy -> python)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


def dump(obj: Any, path: Path | str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(clean(obj), indent=2, allow_nan=False))

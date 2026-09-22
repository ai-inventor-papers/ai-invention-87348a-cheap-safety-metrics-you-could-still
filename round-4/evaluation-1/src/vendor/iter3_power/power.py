"""
power.py -- Power / MDE analysis for the "logit-gap vs candidate metric" family-cluster
Spearman tests on the qwen3-safety graded panel (run_fcYd_7ruOwtm, iter_2 experiment).

Self-contained module. Reads observed inputs read-only from ROOT (iter_2 experiment_1
results), writes only inside WORKSPACE (this directory): power.json and
figures/power_curves.png.

Usage:
    venv_eval/bin/python power.py --n_mc 1000 --n_boot 500
    venv_eval/bin/python power.py --pilot --n_mc 50
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

WORKSPACE = Path(__file__).resolve().parent
ROOT = Path(
    "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_1"
)
EXCLUDED_SLUG = "Goekdeniz-Guelmez__Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1"  # D12 deviation

LOG_PATH = WORKSPACE / "logs" / "power.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

from loguru import logger  # noqa: E402  (after env vars set)

logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(LOG_PATH, level="DEBUG", rotation="20 MB")

# --------------------------------------------------------------------------------------
# Observed-data loading
# --------------------------------------------------------------------------------------


def load_observed() -> dict:
    """Reconstruct the n=15 graded panel, the observed ICC (lineage random effect) and
    the observed logit-gap vs two-sided Spearman correlation (rho_G_obs)."""
    pc = json.loads((ROOT / "results" / "per_checkpoint.json").read_text())
    jg = json.loads((ROOT / "results" / "judge_grades.json").read_text())["per_checkpoint"]
    items = json.loads((ROOT / "inherited" / "items.json").read_text())["items"]
    kind_by_id = {it["id"]: it["kind"] for it in items}
    slug_lineage = {row["slug"]: row["lineage"] for row in pc}
    slug_family = {row["slug"]: row["family"] for row in pc}

    two_sided = {}
    for slug, rec in jg.items():
        if slug == EXCLUDED_SLUG:
            continue
        item_idx = rec["item_idx"]
        full = rec["full"]
        hc_vals, fr_vals = [], []
        for idx, g in zip(item_idx, full):
            kind = kind_by_id.get(idx)
            if kind == "harmful":
                hc_vals.append(g["score"])
            elif kind == "benign_alarming":
                fr_vals.append(g["refused"])
        hc = float(np.nanmean(hc_vals)) if hc_vals else float("nan")
        fr = float(np.nanmean(fr_vals)) if fr_vals else float("nan")
        ts = (1 - hc) * (1 - fr)
        if np.isfinite(ts):
            two_sided[slug] = ts

    n_graded = len(two_sided)
    logger.info(f"graded panel: n={n_graded} (expect 15)")

    # cluster unit = lineage (matches step5_correlations.json's own resampling_unit;
    # 'family' alone only has 3 groups which cannot satisfy the >=6-families growth rule,
    # while 'lineage' naturally gives 6 groups at n=15).
    groups = defaultdict(list)
    slug_by_group = defaultdict(list)
    for slug, ts in two_sided.items():
        lin = slug_lineage[slug]
        groups[lin].append(ts)
        slug_by_group[lin].append(slug)

    # ICC(1), unbalanced one-way random-effects ANOVA estimator
    all_vals = np.array(list(two_sided.values()))
    N = len(all_vals)
    a = len(groups)
    grand_mean = all_vals.mean()
    SSB = sum(len(v) * (np.mean(v) - grand_mean) ** 2 for v in groups.values())
    SSW = sum(sum((x - np.mean(v)) ** 2 for x in v) for v in groups.values())
    MSB = SSB / (a - 1)
    MSW = SSW / (N - a) if (N - a) > 0 else float("nan")
    n_i = np.array([len(v) for v in groups.values()])
    k0 = (1.0 / (a - 1)) * (N - (n_i**2).sum() / N)
    icc1_raw = (MSB - MSW) / (MSB + (k0 - 1) * MSW)
    icc_obs = float(np.clip(icc1_raw, 0.0, 0.95))
    logger.info(f"ICC(1) raw={icc1_raw:.4f} clipped(observed)={icc_obs:.4f}, k0={k0:.4f}")

    family_sizes_15 = sorted((len(v) for v in groups.values()), reverse=True)
    lineage_order = [k for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))]
    logger.info(f"lineage groups (n=6): {dict(zip(lineage_order, family_sizes_15))}")

    # rho_G_obs: logit-gap (b_logit_gap_mean) vs two_sided target, Spearman, on the graded
    # (checkpoint-level) panel. Try step5_correlations.json first.
    rho_g_obs = None
    rho_g_source = None
    step5_path = ROOT / "results" / "step5_correlations.json"
    if step5_path.exists():
        step5 = json.loads(step5_path.read_text())
        for row in step5.get("rows", []):
            if row.get("metric_id") == "b_logit_gap_mean":
                cl = row.get("checkpoint_level", {})
                if cl.get("n") == n_graded and cl.get("spearman") is not None:
                    rho_g_obs = float(cl["spearman"])
                    rho_g_source = (
                        f"step5_correlations.json: rows[metric_id=b_logit_gap_mean]"
                        f".checkpoint_level.spearman (n={cl.get('n')}, "
                        f"p={cl.get('p_value')})"
                    )
                break

    if rho_g_obs is None:
        logger.warning("b_logit_gap_mean not found in step5_correlations.json; computing "
                        "logit gap from harvest/<slug>/acts.npz directly")
        gaps = {}
        for slug in two_sided:
            acts_path = ROOT / "harvest" / slug / "acts.npz"
            if not acts_path.exists():
                continue
            with np.load(acts_path) as d:
                logit_feats0 = d["logit_feats"][:, 0]
            gaps[slug] = float(np.mean(logit_feats0))
        common = [s for s in two_sided if s in gaps]
        g_arr = np.array([gaps[s] for s in common])
        t_arr = np.array([two_sided[s] for s in common])
        from scipy.stats import spearmanr

        rho_g_obs, p_g = spearmanr(g_arr, t_arr)
        rho_g_obs = float(rho_g_obs)
        rho_g_source = (
            f"computed from harvest/<slug>/acts.npz['logit_feats'][:,0] mean over 160 items, "
            f"Spearman vs two_sided (n={len(common)}, p={p_g:.4f})"
        )

    logger.info(f"rho_G_obs={rho_g_obs:.4f} source={rho_g_source}")

    return {
        "n_graded": n_graded,
        "two_sided": two_sided,
        "lineage_order": lineage_order,
        "family_sizes_15": family_sizes_15,
        "ICC_obs_raw": float(icc1_raw),
        "ICC_obs": icc_obs,
        "rho_G_obs": rho_g_obs,
        "rho_G_source": rho_g_source,
    }


def grow_family_sizes(base_sizes: list[int], target_n: int) -> list[int]:
    """Grow a family-size vector proportionally to target_n via the largest-remainder
    method, keeping every group >=1 (singletons allowed) and the group count fixed
    (base already has >=6 groups, so the grown vector automatically satisfies the
    'at least 6 families' requirement)."""
    base_sizes = list(base_sizes)
    base_n = sum(base_sizes)
    if target_n == base_n:
        return base_sizes
    factor = target_n / base_n
    raw = [s * factor for s in base_sizes]
    floors = [max(1, math.floor(r)) for r in raw]
    deficit = target_n - sum(floors)
    remainder_order = sorted(
        range(len(base_sizes)), key=lambda i: (raw[i] - math.floor(raw[i])), reverse=True
    )
    i = 0
    while deficit > 0:
        idx = remainder_order[i % len(remainder_order)]
        floors[idx] += 1
        deficit -= 1
        i += 1
    while deficit < 0:
        idx = max(range(len(floors)), key=lambda k: floors[k])
        if floors[idx] > 1:
            floors[idx] -= 1
            deficit += 1
        else:
            break
    assert sum(floors) == target_n
    return floors


# --------------------------------------------------------------------------------------
# Vectorized simulation core
# --------------------------------------------------------------------------------------


def family_id_array(family_sizes: list[int]) -> np.ndarray:
    ids = []
    for i, s in enumerate(family_sizes):
        ids += [i] * s
    return np.array(ids, dtype=np.int64)


def build_bootstrap_idx_map(family_sizes: list[int], B: int, rng: np.random.Generator) -> np.ndarray:
    """Data-independent family-cluster bootstrap recipe. For each of B replicates and
    each of the A family 'slots' (fixed sizes = family_sizes, in order), draw a source
    family index (with replacement, uniform over families) and fill the slot with that
    many individuals drawn from the source family's positions (without replacement if the
    source family is big enough, with replacement otherwise). Returns idx_map of shape
    (B, n) with values in [0, n) indexing into the ORIGINAL (n,)-length individual axis.
    This whole-family resampling recipe depends only on family_sizes, not on any
    simulated data, so it is computed once per (n, B) and reused across every MC dataset
    and every grid cell for that n via fancy indexing: X[:, idx_map] -> (n_mc, B, n).
    """
    n = sum(family_sizes)
    A = len(family_sizes)
    starts = np.cumsum([0] + family_sizes)[:-1]
    fam_positions = [np.arange(starts[i], starts[i] + family_sizes[i]) for i in range(A)]
    idx_map = np.empty((B, n), dtype=np.int64)
    for b in range(B):
        src = rng.integers(0, A, size=A)
        for i in range(A):
            pos_j = fam_positions[src[i]]
            n_i = family_sizes[i]
            replace = len(pos_j) < n_i
            choice = rng.choice(pos_j, size=n_i, replace=replace)
            idx_map[b, starts[i] : starts[i] + n_i] = choice
    return idx_map


def chol_or_none(rho_G: float, rho_X: float, c_XG: float) -> np.ndarray | None:
    corr = np.array([[1.0, rho_G, rho_X], [rho_G, 1.0, c_XG], [rho_X, c_XG, 1.0]])
    try:
        L = np.linalg.cholesky(corr)
    except np.linalg.LinAlgError:
        return None
    return L


def simulate_TGX(
    n_mc: int,
    n: int,
    family_id: np.ndarray,
    A: int,
    L: np.ndarray,
    ICC: float,
    rng: np.random.Generator,
    need_G: bool = True,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray]:
    """Simulate standardized trivariate (T, G, X) with family random effect, shape (n_mc, n)
    each. If need_G is False, G is not computed (saves work for the SINGLE test, which
    never uses G)."""
    fam_z = rng.standard_normal((n_mc, A, 3))
    ind_z = rng.standard_normal((n_mc, n, 3))
    fam_c = fam_z @ L.T
    ind_c = ind_z @ L.T
    fam_c_expand = fam_c[:, family_id, :]
    sq_icc = math.sqrt(ICC)
    sq_1micc = math.sqrt(1.0 - ICC)
    combined = sq_icc * fam_c_expand + sq_1micc * ind_c
    T = combined[..., 0]
    X = combined[..., 2]
    G = combined[..., 1] if need_G else None
    return T, G, X


def spearman_batch(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Vectorized Spearman correlation along the last axis (Pearson of average ranks,
    which correctly handles ties introduced by bootstrap duplication)."""
    ra = rankdata(a, axis=-1)
    rb = rankdata(b, axis=-1)
    return pearson_of_ranks(ra, rb)


def pearson_of_ranks(ra: np.ndarray, rb: np.ndarray) -> np.ndarray:
    """Pearson correlation given two already-computed rank arrays (avoids recomputing
    rankdata on an array, e.g. T, that is reused against both X and G)."""
    ra = ra - ra.mean(axis=-1, keepdims=True)
    rb = rb - rb.mean(axis=-1, keepdims=True)
    num = (ra * rb).sum(axis=-1)
    den = np.sqrt((ra**2).sum(axis=-1) * (rb**2).sum(axis=-1))
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    return out


# --------------------------------------------------------------------------------------
# Cell evaluation (chunked over n_mc for memory safety)
# --------------------------------------------------------------------------------------

MC_CHUNK = 250  # cap peak array size at (MC_CHUNK, B, n)


def run_single_cell(
    n_mc: int,
    B: int,
    n: int,
    family_id: np.ndarray,
    A: int,
    idx_map: np.ndarray,
    rho_X: float,
    ICC: float,
    rng: np.random.Generator,
) -> dict:
    """SINGLE test: H0 rho_X=0, family-cluster bootstrap 95% CI must exclude 0."""
    L = chol_or_none(0.0, rho_X, 0.0)  # rho_G, c_XG irrelevant for the T,X marginal pair
    if L is None:
        return {"skipped_non_PD": True}
    n_reject = 0
    n_eval = 0
    for start in range(0, n_mc, MC_CHUNK):
        m = min(MC_CHUNK, n_mc - start)
        T, _, X = simulate_TGX(m, n, family_id, A, L, ICC, rng, need_G=False)
        Tg = T[:, idx_map]
        Xg = X[:, idx_map]
        rTg = rankdata(Tg, axis=-1)
        rXg = rankdata(Xg, axis=-1)
        rho_boot = pearson_of_ranks(rXg, rTg)
        lo = np.percentile(rho_boot, 2.5, axis=-1)
        hi = np.percentile(rho_boot, 97.5, axis=-1)
        n_reject += int(np.sum((lo > 0) | (hi < 0)))
        n_eval += m
    return {"power": n_reject / n_eval, "n_eval": n_eval, "skipped_non_PD": False}


def run_diff_cell(
    n_mc: int,
    B: int,
    n: int,
    family_id: np.ndarray,
    A: int,
    idx_map: np.ndarray,
    rho_X: float,
    rho_G: float,
    c_XG: float,
    ICC: float,
    rng: np.random.Generator,
) -> dict:
    """S1 DIFFERENCE test: statistic |rho_XT|-|rho_GT|; reject when bootstrap CI lower
    bound of the difference > 0 AND the point difference >= 0.15."""
    L = chol_or_none(rho_G, rho_X, c_XG)
    if L is None:
        return {"skipped_non_PD": True}
    n_reject = 0
    n_eval = 0
    diff_sum = 0.0
    for start in range(0, n_mc, MC_CHUNK):
        m = min(MC_CHUNK, n_mc - start)
        T, G, X = simulate_TGX(m, n, family_id, A, L, ICC, rng, need_G=True)
        Tg = T[:, idx_map]
        Gg = G[:, idx_map]
        Xg = X[:, idx_map]
        # point estimate (rank each of T,G,X once; no ties since continuous draws)
        rT = rankdata(T, axis=-1)
        rG = rankdata(G, axis=-1)
        rX = rankdata(X, axis=-1)
        rho_XT_point = pearson_of_ranks(rX, rT)
        rho_GT_point = pearson_of_ranks(rG, rT)
        point_diff = np.abs(rho_XT_point) - np.abs(rho_GT_point)
        # bootstrap: rank each of Tg,Gg,Xg ONCE (avoid recomputing rank(Tg) twice)
        rTg = rankdata(Tg, axis=-1)
        rGg = rankdata(Gg, axis=-1)
        rXg = rankdata(Xg, axis=-1)
        rho_XT_boot = pearson_of_ranks(rXg, rTg)
        rho_GT_boot = pearson_of_ranks(rGg, rTg)
        diff_boot = np.abs(rho_XT_boot) - np.abs(rho_GT_boot)
        lo = np.percentile(diff_boot, 2.5, axis=-1)
        reject = (lo > 0) & (point_diff >= 0.15)
        n_reject += int(np.sum(reject))
        diff_sum += float(np.sum(point_diff))
        n_eval += m
    return {
        "power": n_reject / n_eval,
        "point_diff_mean": diff_sum / n_eval,
        "n_eval": n_eval,
        "skipped_non_PD": False,
    }


# --------------------------------------------------------------------------------------
# Timing calibration / reduction ladder
# --------------------------------------------------------------------------------------


CALIB_POINTS = [(100, 100), (200, 200), (300, 300), (500, 300), (1000, 300)]


def empirical_calibrate(rng: np.random.Generator, fs15: list[int], fs38: list[int]) -> dict:
    """Directly TIME run_diff_cell/run_single_cell at both small (n=15) and large
    (n=38) scale, across a handful of (mc,B) points, and fit a per-n linear model
    time ~= a + b*(mc*B). This replaces a naive per-element unit-cost estimate, which
    badly under-samples fixed per-call/per-chunk overhead when measured on a tiny
    array and so grossly mis-predicts the cost of the real (mc~1000,B~500) cells."""
    models = {}
    for n_key, fs in (("15", fs15), ("38", fs38)):
        n = sum(fs)
        fam_id = family_id_array(fs)
        A = len(fs)
        diff_pts, single_pts = [], []
        for mc, B in CALIB_POINTS:
            idx_map = build_bootstrap_idx_map(fs, B, rng)
            t0 = time.perf_counter()
            run_diff_cell(mc, B, n, fam_id, A, idx_map, 0.3, 0.2, 0.3, 0.4, rng)
            diff_pts.append((mc * B, time.perf_counter() - t0))
            t0 = time.perf_counter()
            run_single_cell(mc, B, n, fam_id, A, idx_map, 0.3, 0.4, rng)
            single_pts.append((mc * B, time.perf_counter() - t0))
        xs_d = np.array([p[0] for p in diff_pts], dtype=float)
        ys_d = np.array([p[1] for p in diff_pts], dtype=float)
        xs_s = np.array([p[0] for p in single_pts], dtype=float)
        ys_s = np.array([p[1] for p in single_pts], dtype=float)
        b_d, a_d = np.polyfit(xs_d, ys_d, 1)
        b_s, a_s = np.polyfit(xs_s, ys_s, 1)
        models[n_key] = {
            "n": n, "diff_a": float(a_d), "diff_b": float(b_d),
            "single_a": float(a_s), "single_b": float(b_s),
            "diff_points": diff_pts, "single_points": single_pts,
        }
    return models


def predict_time(models: dict, n: int, mc: int, B: int, kind: str) -> float:
    """Interpolate the fitted (a + b*mc*B) models between the n=15 and n=38 anchors."""
    m15, m38 = models["15"], models["38"]
    x = mc * B
    t15 = max(0.0, m15[f"{kind}_a"] + m15[f"{kind}_b"] * x)
    t38 = max(0.0, m38[f"{kind}_a"] + m38[f"{kind}_b"] * x)
    n15, n38 = m15["n"], m38["n"]
    frac = (n - n15) / (n38 - n15)
    return max(0.0, t15 + (t38 - t15) * frac)


def project_seconds(
    n_list: list[int],
    icc_grid: list[float],
    rho_g_grid: list[float],
    c_xg_grid: list[float],
    rho_x_grid: list[float],
    primary_key: tuple[float, float],
    tier_mc: dict[str, int],
    tier_b: dict[str, int],
    models: dict,
) -> float:
    n_rho_x = len(rho_x_grid)
    total = 0.0
    for n in n_list:
        for icc in icc_grid:
            for rg in rho_g_grid:
                tier = "primary" if (icc, rg) == primary_key else "secondary"
                mc, B = tier_mc[tier], tier_b[tier]
                total += predict_time(models, n, mc, B, "diff") * len(c_xg_grid) * n_rho_x
        for icc in icc_grid:
            tier = "primary" if icc == primary_key[0] else "secondary"
            mc, B = tier_mc[tier], tier_b[tier]
            total += predict_time(models, n, mc, B, "single") * n_rho_x
    return total


# --------------------------------------------------------------------------------------
# JSON sanitization
# --------------------------------------------------------------------------------------


def sanitize(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return sanitize(v)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    return obj


# --------------------------------------------------------------------------------------
# Main run()
# --------------------------------------------------------------------------------------


def run(
    out_dir: Path,
    n_mc: int = 1000,
    n_boot: int = 500,
    pilot: bool = False,
    seed: int = 20260921,
) -> dict:
    out_dir = Path(out_dir)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    rng_master = np.random.default_rng(seed)

    logger.info(f"=== power.py run start (pilot={pilot}, n_mc={n_mc}, n_boot={n_boot}) ===")

    obs = load_observed()
    n_list = [15, 24, 30, 38]
    family_sizes_by_n = {15: obs["family_sizes_15"]}
    for n in (24, 30, 38):
        family_sizes_by_n[n] = grow_family_sizes(obs["family_sizes_15"], n)
    for n, fs in family_sizes_by_n.items():
        logger.info(f"n={n}: family_sizes={fs} (sum={sum(fs)}, n_families={len(fs)})")

    ICC_obs = round(obs["ICC_obs"], 6)
    rho_G_obs = round(obs["rho_G_obs"], 6)
    icc_grid = sorted(set([0.0, 0.3, 0.6, ICC_obs]))
    rho_g_grid = sorted(set([rho_G_obs, 0.2, 0.4]))
    c_xg_grid = [0.0, 0.3, 0.6]
    rho_x_grid = [round(x, 2) for x in np.arange(0.0, 0.901, 0.05)]
    primary_key = (ICC_obs, rho_G_obs)
    logger.info(
        f"ICC_grid={icc_grid} rho_G_grid={rho_g_grid} c_XG_grid={c_xg_grid} "
        f"primary_key={primary_key}"
    )

    reductions: list[str] = []

    # ---- pilot / calibration: directly TIME real diff/single cells at n=15 and n=38
    # across a handful of (mc,B) points and fit a linear-in-(mc*B) model per n, rather
    # than extrapolate from one tiny (fixed-overhead-dominated) sample. ----
    t_cal0 = time.perf_counter()
    models = empirical_calibrate(rng_master, family_sizes_by_n[15], family_sizes_by_n[38])
    logger.info(f"empirical calibration done in {time.perf_counter()-t_cal0:.1f}s: {models}")

    if pilot:
        est_1000_500 = project_seconds(
            n_list, icc_grid, rho_g_grid, c_xg_grid, rho_x_grid, primary_key,
            {"primary": n_mc, "secondary": n_mc}, {"primary": n_boot, "secondary": n_boot}, models,
        )
        result = {
            "mode": "pilot",
            "calibration_models": models,
            "projected_seconds_at_requested_mc_boot": est_1000_500,
            "projected_minutes_at_requested_mc_boot": est_1000_500 / 60,
            "requested_n_mc": n_mc,
            "requested_n_boot": n_boot,
            "observed": {
                "n_graded": obs["n_graded"],
                "family_sizes": family_sizes_by_n,
                "ICC_obs": ICC_obs,
                "rho_G_obs": rho_G_obs,
                "rho_G_source": obs["rho_G_source"],
            },
        }
        out_path = out_dir / "power.json"
        out_path.write_text(json.dumps(sanitize(result), indent=2, allow_nan=False))
        logger.info(f"pilot done in {time.perf_counter()-t_start:.1f}s; wrote {out_path}")
        return result

    # ---- decide tiers via reduction ladder (measured, not guessed) ----
    BUDGET_SECONDS = 30 * 60  # leave buffer under the 40-min hard wall clock (calib + grid + plot + I/O)
    ladder = [
        ("no_reduction", {"primary": n_mc, "secondary": n_mc}, {"primary": n_boot, "secondary": n_boot}),
        (
            f"inner bootstrap reduced to 300 (from {n_boot}) for all cells",
            {"primary": n_mc, "secondary": n_mc},
            {"primary": 300, "secondary": 300},
        ),
        (
            "full grid (all rho_G x all ICC) restricted to n_mc=300 for non-primary "
            f"(ICC,rho_G) cells; PRIMARY cells (ICC_obs={ICC_obs}, rho_G_obs={rho_G_obs}) "
            f"kept at n_mc={n_mc}",
            {"primary": n_mc, "secondary": 300},
            {"primary": 300, "secondary": 300},
        ),
        (
            "secondary n_mc further restricted to 150 (300 still over budget)",
            {"primary": n_mc, "secondary": 150},
            {"primary": 300, "secondary": 150},
        ),
        (
            "secondary n_mc further restricted to 75",
            {"primary": n_mc, "secondary": 75},
            {"primary": 300, "secondary": 75},
        ),
        (
            "secondary n_mc further restricted to 40, secondary boot to 100",
            {"primary": n_mc, "secondary": 40},
            {"primary": 300, "secondary": 100},
        ),
        (
            "PRIMARY n_mc also reduced to 500 (all reductions above still over budget)",
            {"primary": 500, "secondary": 40},
            {"primary": 300, "secondary": 100},
        ),
    ]
    chosen = None
    for label, tier_mc, tier_b in ladder:
        proj = project_seconds(n_list, icc_grid, rho_g_grid, c_xg_grid, rho_x_grid, primary_key, tier_mc, tier_b, models)
        logger.info(f"ladder candidate [{label}]: projected {proj/60:.1f} min")
        if proj <= BUDGET_SECONDS:
            chosen = (label, tier_mc, tier_b, proj)
            if label != "no_reduction":
                reductions.append(f"{label} (projected {proj/60:.1f} min)")
            break
    if chosen is None:
        label, tier_mc, tier_b = ladder[-1][0], ladder[-1][1], ladder[-1][2]
        proj = project_seconds(n_list, icc_grid, rho_g_grid, c_xg_grid, rho_x_grid, primary_key, tier_mc, tier_b, models)
        reductions.append(
            f"{label}: even the most reduced ladder step projected {proj/60:.1f} min > budget; running it anyway"
        )
        chosen = (label, tier_mc, tier_b, proj)

    label, tier_mc, tier_b, proj = chosen
    logger.info(f"CHOSEN TIER: {label} -> mc={tier_mc}, boot={tier_b} (projected {proj/60:.1f} min)")

    def tier_of(icc, rg=None):
        if rg is None:
            return "primary" if icc == primary_key[0] else "secondary"
        return "primary" if (icc, rg) == primary_key else "secondary"

    # ---- main grid computation ----
    power_curves_single: dict = {}
    power_curves_diff: dict = {}
    skipped_non_pd: list = []
    n_cells_done = 0

    idx_map_cache: dict[tuple[int, int], np.ndarray] = {}

    def get_idx_map(n, B, family_sizes):
        key = (n, B)
        if key not in idx_map_cache:
            idx_map_cache[key] = build_bootstrap_idx_map(family_sizes, B, rng_master)
        return idx_map_cache[key]

    for n in n_list:
        fs = family_sizes_by_n[n]
        fam_id = family_id_array(fs)
        A = len(fs)
        power_curves_single[n] = {}
        for icc in icc_grid:
            tier = tier_of(icc)
            mc, B = tier_mc[tier], tier_b[tier]
            idx_map = get_idx_map(n, B, fs)
            curve = []
            for rx in rho_x_grid:
                res = run_single_cell(mc, B, n, fam_id, A, idx_map, rx, icc, rng_master)
                if res.get("skipped_non_PD"):
                    skipped_non_pd.append({"test": "single", "n": n, "ICC": icc, "rho_X": rx})
                    curve.append({"rho_X": rx, "power": None})
                else:
                    curve.append({"rho_X": rx, "power": res["power"], "n_mc": res["n_eval"]})
                n_cells_done += 1
            power_curves_single[n][icc] = curve
        logger.info(f"n={n}: SINGLE grid done ({n_cells_done} cells so far, "
                    f"{time.perf_counter()-t_start:.0f}s elapsed)")

        power_curves_diff[n] = {}
        for c_xg in c_xg_grid:
            power_curves_diff[n][c_xg] = {}
            for icc in icc_grid:
                power_curves_diff[n][c_xg][icc] = {}
                for rg in rho_g_grid:
                    tier = tier_of(icc, rg)
                    mc, B = tier_mc[tier], tier_b[tier]
                    idx_map = get_idx_map(n, B, fs)
                    curve = []
                    for rx in rho_x_grid:
                        res = run_diff_cell(mc, B, n, fam_id, A, idx_map, rx, rg, c_xg, icc, rng_master)
                        if res.get("skipped_non_PD"):
                            skipped_non_pd.append(
                                {"test": "diff", "n": n, "c_XG": c_xg, "ICC": icc, "rho_G": rg, "rho_X": rx}
                            )
                            curve.append({"rho_X": rx, "power": None})
                        else:
                            curve.append(
                                {
                                    "rho_X": rx,
                                    "power": res["power"],
                                    "point_diff_mean": res["point_diff_mean"],
                                    "n_mc": res["n_eval"],
                                }
                            )
                        n_cells_done += 1
                    power_curves_diff[n][c_xg][icc][rg] = curve
        logger.info(f"n={n}: DIFF grid done ({n_cells_done} cells so far total, "
                    f"{time.perf_counter()-t_start:.0f}s elapsed)")

    # ---- extra: rho_X == rho_G_obs diagonal (size check at primary cell) ----
    size_check_diag_primary = {}
    for n in n_list:
        fs = family_sizes_by_n[n]
        fam_id = family_id_array(fs)
        A = len(fs)
        mc, B = tier_mc["primary"], tier_b["primary"]
        idx_map = get_idx_map(n, B, fs)
        size_check_diag_primary[n] = {}
        for c_xg in c_xg_grid:
            res = run_diff_cell(mc, B, n, fam_id, A, idx_map, rho_G_obs, rho_G_obs, c_xg, ICC_obs, rng_master)
            size_check_diag_primary[n][c_xg] = {
                "false_positive_rate": None if res.get("skipped_non_PD") else res["power"],
                "n_mc": res.get("n_eval"),
            }
    logger.info(f"size-check diagonal (rho_X=rho_G_obs) done, {time.perf_counter()-t_start:.0f}s elapsed")

    # ---- MDE tables ----
    def find_mde_single(n, icc):
        curve = power_curves_single[n][icc]
        for pt in curve:
            if pt["power"] is not None and pt["power"] >= 0.80:
                return pt["rho_X"]
        return None

    def find_mde_diff(n, c_xg, icc, rg):
        curve = power_curves_diff[n][c_xg][icc][rg]
        for pt in curve:
            if pt["power"] is not None and pt["power"] >= 0.80:
                return round(pt["rho_X"] - rg, 4)
        return None

    MDE_single = {n: {icc: find_mde_single(n, icc) for icc in icc_grid} for n in n_list}
    MDE_diff = {
        n: {
            c_xg: {icc: {rg: find_mde_diff(n, c_xg, icc, rg) for rg in rho_g_grid} for icc in icc_grid}
            for c_xg in c_xg_grid
        }
        for n in n_list
    }

    # ---- size check (false positive rates) ----
    size_check = {"single_rho_X_equals_0": {}, "S1_diff_rho_X_equals_rho_G": {}}
    for n in n_list:
        for icc in icc_grid:
            curve = power_curves_single[n][icc]
            size_check["single_rho_X_equals_0"].setdefault(n, {})[icc] = curve[0]["power"]  # rho_X grid[0]==0.0
    for n in n_list:
        size_check["S1_diff_rho_X_equals_rho_G"][n] = {"primary_cell": size_check_diag_primary[n]}
        # also extract exact hits from the main grid where rho_G in {0.2,0.4} lies on the rho_X grid
        extra = {}
        for c_xg in c_xg_grid:
            for icc in icc_grid:
                for rg in rho_g_grid:
                    for pt in power_curves_diff[n][c_xg][icc][rg]:
                        if abs(pt["rho_X"] - rg) < 1e-9:
                            extra.setdefault(c_xg, {}).setdefault(icc, {})[rg] = pt["power"]
        size_check["S1_diff_rho_X_equals_rho_G"][n]["from_grid_exact_hits"] = extra

    # ---- analytic Fisher-z MDE ----
    analytic_fisher_z_MDE = {n: math.tanh((1.96 + 0.84) / math.sqrt(n - 3)) * 1.06 for n in n_list}

    # ---- n_eff ----
    n_eff = {}
    for n in n_list:
        fs = family_sizes_by_n[n]
        m_unw = sum(fs) / len(fs)
        m_w = sum(s**2 for s in fs) / n
        per_icc = {}
        for icc in icc_grid:
            per_icc[icc] = {
                "n_eff_unweighted_m": n / (1 + (m_unw - 1) * icc) if icc < 1 else None,
                "n_eff_weighted_m": n / (1 + (m_w - 1) * icc) if icc < 1 else None,
            }
        n_eff[n] = {
            "m_unweighted": m_unw,
            "m_weighted": m_w,
            "by_ICC": per_icc,
            "primary_ICC_obs": per_icc[ICC_obs],
        }

    # ---- bound_MDE: largest MDE_diff over c_XG at the primary (ICC_obs, rho_G_obs) cell ----
    bound_MDE = {}
    for n in n_list:
        vals = [MDE_diff[n][c_xg][ICC_obs][rho_G_obs] for c_xg in c_xg_grid]
        if any(v is None for v in vals):
            bound_MDE[n] = {"value": None, "note": "not reached by rho_X=0.9 for at least one c_XG"}
        else:
            bound_MDE[n] = {"value": max(vals), "worst_c_XG": c_xg_grid[int(np.argmax(vals))]}

    # ---- plain-word sentences ----
    mde15 = MDE_single[15][ICC_obs]
    s1 = (
        f"at n=15 a Spearman must exceed {mde15:.2f} to be detected (family-cluster CI, ICC={ICC_obs:.2f})"
        if mde15 is not None
        else f"at n=15 no Spearman up to 0.9 reached 80% power (family-cluster CI, ICC={ICC_obs:.2f})"
    )
    mde30_c0 = MDE_diff[30][0.0][ICC_obs][rho_G_obs]
    mde30_c6 = MDE_diff[30][0.6][ICC_obs][rho_G_obs]
    if mde30_c0 is not None and mde30_c0 <= 0.15:
        s2 = (
            f"the 0.15 margin is detectable at n=30 when the candidate is uncorrelated with the "
            f"logit gap (c_XG=0: MDE_diff={mde30_c0:.3f}), but not when c_XG=0.6 "
            f"(MDE_diff={mde30_c6 if mde30_c6 is not None else 'not reached by 0.9'})"
        )
    else:
        s2 = (
            f"the 0.15 margin is not detectable at n=30 even when the candidate is uncorrelated "
            f"with the logit gap (c_XG=0: MDE_diff="
            f"{mde30_c0 if mde30_c0 is not None else 'not reached by 0.9'})"
        )
    b15 = bound_MDE[15]["value"]
    s3 = (
        f"a null at n=15 cannot rule out an advantage of up to {b15:.3f} "
        f"(rho_X - rho_G) over the logit gap"
        if b15 is not None
        else "a null at n=15 cannot rule out an advantage of unknown size (MDE not reached by rho_X=0.9)"
    )
    plain_word_sentences = [s1, s2, s3]

    total_seconds = time.perf_counter() - t_start
    logger.info(f"=== power.py run done in {total_seconds/60:.1f} min ===")

    result = {
        "config": {
            "n_list": n_list,
            "family_sizes_by_n": family_sizes_by_n,
            "ICC_grid": icc_grid,
            "rho_G_grid": rho_g_grid,
            "c_XG_grid": c_xg_grid,
            "rho_X_grid": rho_x_grid,
            "primary_cell": {"ICC": ICC_obs, "rho_G": rho_G_obs},
            "tier_n_mc": tier_mc,
            "tier_n_boot": tier_b,
            "seed": seed,
            "excluded_slug_D12": EXCLUDED_SLUG,
        },
        "observed": {
            "n_graded": obs["n_graded"],
            "family_sizes": family_sizes_by_n[15],
            "lineage_order": obs["lineage_order"],
            "ICC_obs_raw": obs["ICC_obs_raw"],
            "ICC_obs": ICC_obs,
            "rho_G_obs": rho_G_obs,
            "rho_G_source": obs["rho_G_source"],
        },
        "power_curves": {"single": power_curves_single, "diff": power_curves_diff},
        "MDE_single": MDE_single,
        "MDE_diff": MDE_diff,
        "size_check": size_check,
        "analytic_fisher_z_MDE": analytic_fisher_z_MDE,
        "n_eff": n_eff,
        "bound_MDE": bound_MDE,
        "plain_word_sentences": plain_word_sentences,
        "skipped_non_PD": skipped_non_pd,
        "reductions": reductions,
        "calibration_models": models,
        "chosen_tier_label": label,
        "chosen_tier_projected_minutes": proj / 60,
        "runtime_seconds": total_seconds,
        "n_cells_computed": n_cells_done,
    }

    out_path = out_dir / "power.json"
    out_path.write_text(json.dumps(sanitize(result), indent=2, allow_nan=False))
    logger.info(f"wrote {out_path}")

    make_figure(result, fig_dir / "power_curves.png")
    logger.info(f"wrote {fig_dir / 'power_curves.png'}")

    return result


def make_figure(result: dict, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_list = result["config"]["n_list"]
    ICC_obs = result["config"]["primary_cell"]["ICC"]
    rho_G_obs = result["config"]["primary_cell"]["rho_G"]
    rho_x_grid = result["config"]["rho_X_grid"]
    c_xg_grid = result["config"]["c_XG_grid"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

    ax = axes[0]
    cmap = plt.get_cmap("viridis")
    for i, n in enumerate(n_list):
        curve = result["power_curves"]["single"][n][ICC_obs]
        xs = [pt["rho_X"] for pt in curve]
        ys = [pt["power"] if pt["power"] is not None else np.nan for pt in curve]
        ax.plot(xs, ys, marker="o", ms=3, color=cmap(i / max(1, len(n_list) - 1)), label=f"n={n}")
    ax.axhline(0.80, color="gray", ls="--", lw=1)
    ax.set_xlabel(r"$\rho_X$ (candidate vs target, true)")
    ax.set_ylabel("power")
    ax.set_title(f"SINGLE test (H0: $\\rho_X$=0)\nprimary cell: ICC={ICC_obs:.2f}")
    ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=8)

    ax = axes[1]
    ls_list = ["-", "--", ":"]
    for i, n in enumerate(n_list):
        for j, c_xg in enumerate(c_xg_grid):
            curve = result["power_curves"]["diff"][n][c_xg][ICC_obs][rho_G_obs]
            xs = [pt["rho_X"] - rho_G_obs for pt in curve]
            ys = [pt["power"] if pt["power"] is not None else np.nan for pt in curve]
            ax.plot(
                xs, ys, ls=ls_list[j % len(ls_list)], color=cmap(i / max(1, len(n_list) - 1)),
                lw=1.6, alpha=0.9,
                label=f"n={n}, c_XG={c_xg}" if i == 0 or j == 0 else None,
            )
    ax.axhline(0.80, color="gray", ls="--", lw=1)
    ax.axvline(0.15, color="red", ls=":", lw=1)
    ax.set_xlabel(r"$\rho_X - \rho_G$ (true advantage over logit gap)")
    ax.set_ylabel("power")
    ax.set_title(
        f"S1 DIFF test (|rho_XT|-|rho_GT| >= 0.15 & CI excl. 0)\nprimary cell: "
        f"ICC={ICC_obs:.2f}, rho_G={rho_G_obs:.2f}"
    )
    ax.set_ylim(-0.02, 1.02)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, fontsize=6, ncol=2, loc="lower right")

    fig.suptitle("Power curves: logit-gap-vs-candidate family-cluster Spearman tests (primary cell)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Power/MDE analysis for family-cluster Spearman tests")
    parser.add_argument("--n_mc", type=int, default=1000, help="primary-tier MC datasets")
    parser.add_argument("--n_boot", type=int, default=500, help="inner bootstrap replicates")
    parser.add_argument("--pilot", action="store_true", help="run a timing-only pilot")
    args = parser.parse_args()
    run(WORKSPACE, n_mc=args.n_mc, n_boot=args.n_boot, pilot=args.pilot)

#!/usr/bin/env python3
"""Step 1: reconcile SafeRL-vs-abliteration subspace-sharing claims.

For every layer and both read sites (hs_last, hs_first), computes per-item
differences D_s = H_saferl - H_instruct and D_a = H_abl - H_instruct on the
identical item set (all 160 items, and the harmful-only 64-item subset), for
abl in {mlabonne/Qwen3-4B-abliterated (primary), DreamFast/qwen3-4b-heretic
(second arm)}.  For each (site, abl-arm, item-subset, layer) cell it reports:

  (i)   cos(mean D_s, mean D_a)                        -- do the mean shifts align?
  (ii)  first & mean principal angles (deg) between the -- do the item-to-item
        top-k right-singular (feature-space, d=2560)       variation subspaces
        subspaces of D_s and D_a, k in {1,4,8,16}           overlap?
  (iii) four null distributions (200 draws each) for both statistics, plus
        per-layer p-values, plus a "beats null" verdict.

It then tests the pre-registered reconciliation hypothesis -- a shared
low-dimensional subspace with near-orthogonal mean shifts -- by asking
whether the first-principal-angle advantage over null survives (a) after
projecting out the top-5 PCs of the pooled instruct activations at that
layer (de-anisotropisation) and (b) at k=1, and reduces everything to one of
four verdict labels per the decision rule in `classify_layer_cell()`.

Finally it reproduces four iter-2 headline numbers from
ROOT/results/step1_anchor.json and iter-2's evaluation d1_step1.json, citing
the exact source file and JSON key for each and flagging any that do not
reproduce to rounding.

Read-only inputs (NEVER written):
  ROOT/harvest/{4 checkpoints}/acts.npz  (keys hs_last, hs_first only)
  ROOT/inherited/items.json
  ROOT/results/step1_anchor.json
  ROOT/screen/step1.py                                  (iter-2 method, for reference)
  <iter_2>/gen_art_evaluation_1/results/d1_step1.json    (iter-2 eval headline numbers)

Outputs (inside WORKSPACE only):
  step1_reconciled.json
  figures/step1_per_layer.png
  logs/step1.log
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import beta as beta_dist

# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
WORKSPACE = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_evaluation_1")
ROOT = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_1")
ITER2_EVAL = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_evaluation_1")

HARVEST = ROOT / "harvest"
ITEMS_JSON = ROOT / "inherited" / "items.json"
STEP1_ANCHOR_JSON = ROOT / "results" / "step1_anchor.json"
D1_STEP1_JSON = ITER2_EVAL / "results" / "d1_step1.json"

OUT_JSON = WORKSPACE / "step1_reconciled.json"
FIG_DIR = WORKSPACE / "figures"
FIG_PATH = FIG_DIR / "step1_per_layer.png"
LOG_DIR = WORKSPACE / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOG_DIR / "step1.log"), rotation="30 MB", level="DEBUG")

# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
CHECKPOINTS = {
    "instruct": "Qwen__Qwen3-4B",
    "saferl": "Qwen__Qwen3-4B-SafeRL",
    "mlab": "mlabonne__Qwen3-4B-abliterated",
    "heretic": "DreamFast__qwen3-4b-heretic",
}
SITES = ["hs_last", "hs_first"]
ABL_ARMS = ["mlab", "heretic"]          # mlab = primary, heretic = second arm
ITEM_SUBSETS = ["all", "harmful"]
K_LIST = [1, 4, 8, 16]
K_PRIMARY = 8                            # iter-2's k_subspace choice
D_AMBIENT = 2560
N_NULL = 200                             # per-layer null draws (spec: 200)
B_REPRO_NULL = 1000                      # exact match to d1_step1.py's B_null for reproduction only
TOP64 = 64                               # anisotropy-matched null span
N_DEANISO_PC = 5                         # PCs of pooled instruct acts removed
SEED = 20260921
PRIMARY_SITE = "hs_last"
PRIMARY_ARM = "mlab"
PRIMARY_SUBSET = "all"

VERDICT_LABELS = [
    "SHARED_ANISOTROPY_ONLY",
    "SHARED_SUBSPACE_DIFFERENT_DIRECTIONS",
    "SAME_AXIS",
    "UNRELATED",
]

RECONCILIATION_HYPOTHESIS = (
    "a shared low-dimensional subspace (small first principal angle among "
    "top-k) with near-orthogonal mean shifts is geometrically consistent: "
    "two edits can move along different directions inside a common "
    "high-variance (anisotropy) subspace."
)

DECISION_RULE_TEXT = (
    "For a given (site, abl-arm, item-subset) scope at k=K_PRIMARY: "
    "angle_significant := first_principal_angle_deg < p5(anisotropy-matched null) "
    "AND < p5(MC random-subspace null); "
    "angle_significant_deanisotropized := same test computed AFTER projecting out "
    "the top-5 instruct PCs from both D_s and D_a at that layer; "
    "mean_significant := |cos(mean_s, mean_a)| > p95(sign-flip null) "
    "AND > p95(anisotropy-matched-cosine null). "
    "Then: if NOT angle_significant (pre-projection) -> UNRELATED "
    "(neither subspace sharing nor mean alignment is established at k=1 either "
    "if that also fails, this is the strongest reading of UNRELATED). "
    "elif angle_significant and NOT angle_significant_deanisotropized -> "
    "SHARED_ANISOTROPY_ONLY (the apparent sharing is explained by both edits "
    "living in the same generic high-variance directions, not a specific "
    "shared low-rank edit subspace). "
    "elif angle_significant_deanisotropized and NOT mean_significant -> "
    "SHARED_SUBSPACE_DIFFERENT_DIRECTIONS (subspace sharing survives "
    "de-anisotropisation while the mean shifts are not aligned -- the "
    "reconciliation hypothesis's positive case). "
    "elif angle_significant_deanisotropized and mean_significant -> SAME_AXIS "
    "(both the subspace and the specific mean direction are shared -- the two "
    "edits are not merely subspace-mates, they point the same way)."
)


def classify_layer_cell(
    angle_sig_pre: bool, angle_sig_post: bool, mean_sig: bool
) -> str:
    """Verdict per the decision rule above. Kept as one small pure function
    so the rule is legible and testable independent of the data pipeline."""
    if not angle_sig_pre:
        return "UNRELATED"
    if angle_sig_pre and not angle_sig_post:
        return "SHARED_ANISOTROPY_ONLY"
    if angle_sig_post and not mean_sig:
        return "SHARED_SUBSPACE_DIFFERENT_DIRECTIONS"
    return "SAME_AXIS"


# ---------------------------------------------------------------------------
# small numerics
# ---------------------------------------------------------------------------
def row_svd(D: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Thin SVD of an (n,d) matrix with n << d via the n x n Gram (fast,
    numerically checked against LAPACK once in main()). Returns (s, Vt)
    with Vt's rows orthonormal, descending singular values."""
    G = D @ D.T
    w, U = np.linalg.eigh(G)
    idx = np.argsort(w)[::-1]
    w = np.clip(w[idx], 0.0, None)
    U = U[:, idx]
    s = np.sqrt(w)
    Vt = (U / np.where(s > 0, s, 1.0)).T @ D
    return s, Vt


def effective_rank(s: np.ndarray, tol_mult: float = 1.0) -> int:
    if s.size == 0 or s[0] <= 0:
        return 0
    return int((s > s[0] * max(s.size, 1) * np.finfo(np.float64).eps * tol_mult).sum())


def first_principal_angle_deg_cos(cos_k: np.ndarray) -> tuple[float | None, float | None]:
    """The 'first principal angle' by the standard convention: the SMALLEST
    angle among the k principal angles, i.e. acos(the LARGEST cosine),
    regardless of the input array's order. Used at every site that reports
    a 'first principal angle' (pre-projection, post-projection, and every
    null: MC random-subspace, anisotropy-matched) so the statistic is
    uniform everywhere, with a self-check that angle and cosine agree."""
    if cos_k is None or np.asarray(cos_k).size == 0:
        return None, None
    c = float(np.clip(np.max(cos_k), -1.0, 1.0))
    ang = float(np.degrees(np.arccos(c)))
    assert abs(ang - math.degrees(math.acos(np.clip(c, -1.0, 1.0)))) < 1e-9, \
        "first_angle/first_cos self-check failed"
    return ang, c


def principal_angle_cosines(VtA: np.ndarray, VtB: np.ndarray, k: int) -> np.ndarray:
    """Cosines of the k principal angles between the top-k row spaces of
    VtA, VtB (each already the top singular directions), descending order
    (cos[0] = largest overlap = smallest angle)."""
    ka = min(k, VtA.shape[0])
    kb = min(k, VtB.shape[0])
    kk = min(ka, kb)
    if kk == 0:
        return np.array([])
    M = VtA[:kk] @ VtB[:kk].T
    s = np.linalg.svd(M, compute_uv=False)
    return np.clip(s, 0.0, 1.0)[::-1][::-1]  # already descending from svd


def top_rows_centered(D: np.ndarray, kmax: int) -> tuple[np.ndarray, np.ndarray]:
    """Top singular directions of the ITEM-MEAN-CENTERED difference matrix
    (matches ROOT/screen/step1.py `_top_rows`: item-to-item VARIATION
    subspace, not the mean-shift direction itself). Returns (s, Vt[:kmax])."""
    Dc = D - D.mean(0, keepdims=True)
    s, Vt = row_svd(Dc)
    kmax = min(kmax, Vt.shape[0])
    return s[:kmax], Vt[:kmax]


def top_rows_raw(D: np.ndarray, kmax: int) -> tuple[np.ndarray, np.ndarray]:
    """Top singular directions of the RAW (uncentered) difference matrix,
    matching iter-2's d1_step1.py row_svd(mats[arm]) convention, used only
    for the faithful reproduction of the d1_step1.json headline numbers."""
    s, Vt = row_svd(D)
    kmax = min(kmax, Vt.shape[0])
    return s[:kmax], Vt[:kmax]


def signed_cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return float("nan")
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# global (data-independent) nulls: random k-dim subspaces of R^d=2560
# ---------------------------------------------------------------------------
def mc_random_subspace_null(d: int, k: int, B: int, rng: np.random.Generator) -> dict[str, Any]:
    """Monte-Carlo null: principal angles between TWO independent uniformly
    random k-dim subspaces of R^d (Haar via QR of Gaussian matrices).
    Data-independent -- computed once per k and reused everywhere."""
    Ga = rng.standard_normal((B, d, k))
    Gb = rng.standard_normal((B, d, k))
    Qa, _ = np.linalg.qr(Ga)
    Qb, _ = np.linalg.qr(Gb)
    M = np.matmul(np.swapaxes(Qa, -1, -2), Qb)   # (B,k,k)
    s = np.linalg.svd(M, compute_uv=False)        # (B,k) descending
    cos_first = np.clip(s[:, 0], 0.0, 1.0)
    assert np.allclose(cos_first, np.clip(s.max(axis=1), 0.0, 1.0)), \
        "first principal-angle cosine self-check failed (must be the LARGEST singular value per draw)"
    cos_mean = np.clip(s.mean(axis=1), 0.0, 1.0)
    ang_first_deg = np.degrees(np.arccos(cos_first))
    return {
        "kind": "monte_carlo_random_gaussian_subspace",
        "d": d, "k": k, "B": B,
        "first_angle_deg_p5": float(np.percentile(ang_first_deg, 5)),
        "first_angle_deg_p50": float(np.percentile(ang_first_deg, 50)),
        "abs_cos_first_p95": float(np.percentile(cos_first, 95)),
        "abs_cos_mean_p95": float(np.percentile(cos_mean, 95)),
        "first_angle_deg_samples_summary": {
            "mean": float(ang_first_deg.mean()), "sd": float(ang_first_deg.std(ddof=1))},
    }


def analytic_random_subspace_null(d: int, k: int) -> dict[str, Any]:
    """Closed-form null, EXACT only at k=1: the cosine between two
    independent uniformly-random unit vectors in R^d satisfies
    cos^2 ~ Beta(1/2, (d-1)/2) (condition on one vector; the other is
    uniform on the sphere, and its squared projection onto any fixed axis
    follows this Beta law exactly). For k>1 there is no simple closed form
    for the FIRST (largest) principal angle among random k-dim subspaces
    (it is an extreme-value statistic of a matrix-Beta/Jacobi ensemble), so
    we report analytic_exact=False and point at the Monte-Carlo null
    instead, rather than presenting an unverified approximation as exact."""
    if k == 1:
        a, b = 0.5, (d - 1) / 2.0
        cos2_p95 = beta_dist.ppf(0.95, a, b)
        cos2_p5 = beta_dist.ppf(0.05, a, b)
        ang_p5_deg = math.degrees(math.acos(math.sqrt(cos2_p95)))  # smallest angle at cos^2 p95
        ang_p95_deg = math.degrees(math.acos(math.sqrt(cos2_p5)))
        return {
            "kind": "analytic_beta_cos2", "d": d, "k": k, "analytic_exact": True,
            "formula": "cos^2(theta) ~ Beta(1/2, (d-1)/2) for two independent random unit vectors in R^d",
            "first_angle_deg_p5": ang_p5_deg,
            "abs_cos_first_p95": float(math.sqrt(cos2_p95)),
        }
    return {
        "kind": "analytic_not_available_for_k_gt_1", "d": d, "k": k, "analytic_exact": False,
        "note": ("No simple closed form for the largest principal angle among two "
                 "independent random k-dim subspaces (k>1) of R^d; that statistic is "
                 "an extreme eigenvalue of a matrix-variate Beta/Jacobi ensemble. "
                 "We honestly report analytic_exact=False here and use the "
                 "Monte-Carlo random-Gaussian-subspace null (same B) as the practical "
                 "stand-in for k>1; see global_nulls[k]['monte_carlo']."),
    }


# ---------------------------------------------------------------------------
# per-layer nulls that DO depend on the data
# ---------------------------------------------------------------------------
def permutation_invariance_check(Ds: np.ndarray, Da: np.ndarray, rng: np.random.Generator,
                                  n_checks: int = 5) -> dict[str, Any]:
    """Confirms (rather than assumes) that shuffling which item's D_a row is
    paired with which item's D_s row leaves BOTH the row-space (hence every
    principal angle) and the row MEAN exactly unchanged, since a pure
    permutation reorders but does not alter the SET of row vectors that
    span(D_a) or mean(D_a) are built from. Runs n_checks random permutations
    and asserts bit-level-tolerance invariance instead of asserting it."""
    n = Da.shape[0]
    _, Vt_ref = top_rows_centered(Da, min(8, n - 1))
    mean_ref = Da.mean(0)
    max_angle_dev_deg = 0.0
    max_mean_cos_dev = 0.0
    for _ in range(n_checks):
        perm = rng.permutation(n)
        Da_p = Da[perm]
        _, Vt_p = top_rows_centered(Da_p, min(8, n - 1))
        cos_pa = principal_angle_cosines(Vt_ref, Vt_p, min(8, Vt_ref.shape[0]))
        ang_dev = float(np.degrees(np.arccos(np.clip(cos_pa, -1, 1))).max())
        max_angle_dev_deg = max(max_angle_dev_deg, ang_dev)
        mean_p = Da_p.mean(0)
        c = signed_cos(mean_ref, mean_p)
        max_mean_cos_dev = max(max_mean_cos_dev, abs(1.0 - c) if np.isfinite(c) else 0.0)
    return {
        "claim": ("Row-permutation of D_a leaves span(D_a) and mean(D_a) exactly "
                  "invariant, so BOTH the principal-angle statistic and the "
                  "cosine-of-means statistic are degenerate (zero-variance) under a "
                  "plain item-shuffle null. This is a property of the statistics, "
                  "not a numerical accident."),
        "n_checks": n_checks,
        "max_principal_angle_deviation_deg": max_angle_dev_deg,
        "max_mean_cosine_deviation": max_mean_cos_dev,
        "confirmed_invariant": bool(max_angle_dev_deg < 1e-6 and max_mean_cos_dev < 1e-9),
        "resolution": ("Used a SIGN-FLIP null instead for the cosine-of-means "
                       "statistic: independently flipping the sign of each item's "
                       "row in D_a changes mean(D_a) (a sign-weighted sum) while "
                       "STILL leaving span(D_a) invariant (scaling a single row by "
                       "-1 does not change the space it spans). So sign-flip is a "
                       "genuine randomisation null for the mean-cosine test but "
                       "remains degenerate for the principal-angle test; the "
                       "principal-angle test instead relies on the "
                       "Monte-Carlo/analytic random-subspace null and the "
                       "anisotropy-matched null, which redraw genuinely different "
                       "subspaces rather than reordering existing rows."),
    }


def sign_flip_null_cos_mean(Ds: np.ndarray, Da: np.ndarray, B: int,
                             rng: np.random.Generator) -> dict[str, Any]:
    """Sign-flip null for cos(mean_s, mean_a): flips each item's contribution
    to mean(D_a) independently at random and recomputes the cosine against
    the FIXED observed mean(D_s). Valid randomisation null (see
    permutation_invariance_check for why plain permutation is not)."""
    n = Da.shape[0]
    signs = rng.choice([-1.0, 1.0], size=(B, n))
    mean_a_null = (signs @ Da) / n            # (B, d)
    mean_s = Ds.mean(0)
    ns = np.linalg.norm(mean_s)
    na = np.linalg.norm(mean_a_null, axis=1)
    valid = (ns > 0) & (na > 0)
    cos = np.full(B, np.nan)
    cos[valid] = (mean_a_null[valid] @ mean_s) / (na[valid] * ns)
    cos = cos[np.isfinite(cos)]
    if cos.size == 0:
        return {"kind": "sign_flip_null_cos_mean", "B": 0, "abs_cos_p95": float("nan"),
                "degenerate": True}
    return {
        "kind": "sign_flip_null_cos_mean", "B": int(cos.size),
        "abs_cos_p95": float(np.percentile(np.abs(cos), 95)),
        "cos_mean": float(cos.mean()), "cos_sd": float(cos.std(ddof=1)) if cos.size > 1 else 0.0,
    }


def anisotropy_matched_null(Ds: np.ndarray, Da: np.ndarray, k_list: list[int], B: int,
                             top: int, rng: np.random.Generator) -> dict[str, Any]:
    """Anisotropy-matched null: for EACH side independently, draw a random
    k-dim subspace (and, separately, a random unit vector) confined to that
    side's OWN top-`top` right-singular span, then compare the two random
    draws to each other. This asks: if the two edits had genuinely
    independent directions but each still preferentially used its own
    high-variance (anisotropic) subspace, how much overlap would arise by
    chance? It directly instantiates the reconciliation hypothesis's null."""
    n = Ds.shape[0]
    rank_s = effective_rank(row_svd(Ds)[0])
    rank_a = effective_rank(row_svd(Da)[0])
    r = min(top, rank_s, rank_a, n - 1)
    if r < 2:
        return {"kind": "anisotropy_matched_null", "degenerate": True, "top_used": r}
    _, VtS = row_svd(Ds)
    _, VtA = row_svd(Da)
    VtS_top, VtA_top = VtS[:r], VtA[:r]                    # (r, d), orthonormal rows
    Cx = VtS_top @ VtA_top.T                                # (r, r)

    out: dict[str, Any] = {"kind": "anisotropy_matched_null", "top_used": r, "B": B, "by_k": {}}

    # random unit vectors (k=1 "direction" null, used for the cosine test)
    Gs = rng.standard_normal((B, r))
    Ga = rng.standard_normal((B, r))
    Gs /= np.linalg.norm(Gs, axis=1, keepdims=True)
    Ga /= np.linalg.norm(Ga, axis=1, keepdims=True)
    cos_dir = np.einsum("bi,ij,bj->b", Gs, Cx, Ga)
    out["direction_cosine"] = {"abs_cos_p95": float(np.percentile(np.abs(cos_dir), 95)),
                                "cos_mean": float(cos_dir.mean())}

    for k in k_list:
        kk = min(k, r)
        Ms = rng.standard_normal((B, r, kk))
        Ma = rng.standard_normal((B, r, kk))
        Qs, _ = np.linalg.qr(Ms)
        Qa, _ = np.linalg.qr(Ma)
        M = np.matmul(np.swapaxes(Qs, -1, -2), np.matmul(Cx, Qa))   # (B,kk,kk)
        s = np.linalg.svd(M, compute_uv=False)
        cos_first = np.clip(s[:, 0], 0.0, 1.0)
        assert np.allclose(cos_first, np.clip(s.max(axis=1), 0.0, 1.0)), \
            "anisotropy-matched-null first principal-angle cosine self-check failed"
        cos_mean_k = np.clip(s.mean(axis=1), 0.0, 1.0)
        ang_first_deg = np.degrees(np.arccos(cos_first))
        out["by_k"][str(k)] = {
            "k_used": kk,
            "first_angle_deg_p5": float(np.percentile(ang_first_deg, 5)),
            "abs_cos_first_p95": float(np.percentile(cos_first, 95)),
            "abs_cos_mean_p95": float(np.percentile(cos_mean_k, 95)),
        }
    return out


def empirical_p_value_smaller(observed: float, null_samples: np.ndarray) -> float:
    """One-sided p-value for 'observed is smaller than expected under null'
    (used for angles: smaller = more sharing)."""
    null_samples = np.asarray(null_samples, dtype=float)
    return float((1.0 + (null_samples <= observed).sum()) / (len(null_samples) + 1.0))


def empirical_p_value_larger(observed: float, null_samples: np.ndarray) -> float:
    """One-sided p-value for 'observed is larger than expected under null'
    (used for |cos|: larger = more alignment)."""
    null_samples = np.asarray(null_samples, dtype=float)
    return float((1.0 + (null_samples >= observed).sum()) / (len(null_samples) + 1.0))


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------
def load_items() -> dict[str, Any]:
    items = json.loads(ITEMS_JSON.read_text())["items"]
    kinds = np.array([it["kind"] for it in items])
    ids = np.array([it["id"] for it in items])
    assert np.array_equal(ids, np.arange(len(items))), "item id order must equal row order"
    harmful_mask = kinds == "harmful"
    logger.info(f"items: n={len(items)}, harmful={int(harmful_mask.sum())}")
    return {"n": len(items), "kinds": kinds, "harmful_mask": harmful_mask}


def load_site_arrays() -> dict[str, dict[str, np.ndarray]]:
    """Loads ONLY hs_last, hs_first for the 4 anchor checkpoints, float16."""
    out: dict[str, dict[str, np.ndarray]] = {}
    for role, slug in CHECKPOINTS.items():
        p = HARVEST / slug / "acts.npz"
        t0 = time.time()
        with np.load(p) as z:
            arrs = {site: np.array(z[site]) for site in SITES}
        for site, a in arrs.items():
            assert a.dtype == np.float16
            assert a.shape[0] == 160 and a.shape[2] == D_AMBIENT
        out[role] = arrs
        logger.info(f"loaded {role} ({slug}) hs_last {arrs['hs_last'].shape} "
                    f"hs_first {arrs['hs_first'].shape} in {time.time()-t0:.2f}s")
    n_layers = out["instruct"]["hs_last"].shape[1]
    logger.info(f"n_layer_slots={n_layers}")
    return out, n_layers


# ---------------------------------------------------------------------------
# main analysis
# ---------------------------------------------------------------------------
def analyse(arrays: dict[str, dict[str, np.ndarray]], n_layers: int, item_info: dict[str, Any],
            layers_to_run: list[int], global_nulls: dict[int, dict[str, Any]],
            rng: np.random.Generator) -> dict[str, Any]:
    subset_masks = {"all": np.ones(item_info["n"], dtype=bool), "harmful": item_info["harmful_mask"]}
    per_combo: dict[str, list[dict[str, Any]]] = {}
    excluded: dict[str, list[int]] = {}

    for site in SITES:
        Hi_full = arrays["instruct"][site]
        for arm in ABL_ARMS:
            Ha_full = arrays[arm][site]
            Hs_full = arrays["saferl"][site]
            for subset_name, mask in subset_masks.items():
                combo_key = f"{site}|{arm}|{subset_name}"
                rows: list[dict[str, Any]] = []
                excl: list[int] = []
                logger.info(f"--- combo {combo_key} ({int(mask.sum())} items) ---")
                for l in layers_to_run:
                    Hi_l = Hi_full[mask, l, :].astype(np.float64)
                    Hs_l = Hs_full[mask, l, :].astype(np.float64)
                    Ha_l = Ha_full[mask, l, :].astype(np.float64)
                    Ds = Hs_l - Hi_l
                    Da = Ha_l - Hi_l

                    if not np.any(Ds) or not np.any(Da):
                        excl.append(l)
                        logger.debug(f"{combo_key} layer {l}: excluded "
                                     f"(D_s all-zero={not np.any(Ds)}, D_a all-zero={not np.any(Da)})")
                        continue

                    row = analyse_layer_cell(Ds, Da, Hi_l, l, n_layers, global_nulls, rng)
                    rows.append(row)
                per_combo[combo_key] = rows
                excluded[combo_key] = excl
                logger.info(f"{combo_key}: {len(rows)} layers analysed, "
                            f"{len(excl)} excluded {excl}")
    return {"per_layer": per_combo, "excluded_layers": excluded}


def analyse_layer_cell(Ds: np.ndarray, Da: np.ndarray, Hi_l: np.ndarray, l: int, n_layers: int,
                        global_nulls: dict[int, dict[str, Any]],
                        rng: np.random.Generator) -> dict[str, Any]:
    mean_s, mean_a = Ds.mean(0), Da.mean(0)
    cos_mean = signed_cos(mean_s, mean_a)

    kmax = max(K_LIST)
    n = Ds.shape[0]
    sS, VtS = top_rows_centered(Ds, min(kmax, n - 1))
    sA, VtA = top_rows_centered(Da, min(kmax, n - 1))

    angles: dict[str, Any] = {}
    for k in K_LIST:
        cos_k = principal_angle_cosines(VtS, VtA, k)
        if cos_k.size == 0:
            angles[str(k)] = {"k_used": 0, "largest_angle_among_k_deg": None, "first_principal_angle_deg": None,
                               "mean_angle_deg": None, "first_cos": None}
            continue
        ang_deg = np.degrees(np.arccos(np.clip(cos_k, -1, 1)))
        first_ang, first_cos = first_principal_angle_deg_cos(cos_k)
        assert abs(first_ang - math.degrees(math.acos(np.clip(first_cos, -1, 1)))) < 1e-9
        angles[str(k)] = {
            "k_used": int(cos_k.size),
            "largest_angle_among_k_deg": float(ang_deg.max()),  # weakest-overlap direction among the k (NOT the "first" angle)
            "first_principal_angle_deg": first_ang,   # convention: SMALLEST angle = strongest overlap = "first" principal angle
            "mean_angle_deg": float(ang_deg.mean()),
            "first_cos": first_cos,
        }

    # per-layer data-dependent nulls
    perm_check = permutation_invariance_check(Ds, Da, rng, n_checks=3)
    sign_flip = sign_flip_null_cos_mean(Ds, Da, N_NULL, rng)
    aniso = anisotropy_matched_null(Ds, Da, K_LIST, N_NULL, TOP64, rng)

    # p-values at K_PRIMARY, against the two "subspace" nulls (MC + anisotropy)
    p_vals: dict[str, Any] = {}
    k_p = str(K_PRIMARY)
    if angles[k_p]["first_principal_angle_deg"] is not None:
        obs_ang = angles[k_p]["first_principal_angle_deg"]
        obs_cos_k = angles[k_p]["first_cos"]
        mc_null = global_nulls[K_PRIMARY]["mc_samples_first_angle_deg"]
        p_vals["angle_p_vs_mc_null"] = empirical_p_value_smaller(obs_ang, mc_null)
        if not aniso.get("degenerate"):
            aniso_ang_p5 = aniso["by_k"][k_p]["first_angle_deg_p5"]
            p_vals["angle_beats_aniso_p5"] = bool(obs_ang < aniso_ang_p5)
        p_vals["angle_beats_mc_p5"] = bool(obs_ang < global_nulls[K_PRIMARY]["mc"]["first_angle_deg_p5"])
    if np.isfinite(cos_mean):
        sf_null = sign_flip.get("abs_cos_p95")
        p_vals["mean_cos_beats_signflip_p95"] = (bool(abs(cos_mean) > sf_null)
                                                  if sf_null is not None and np.isfinite(sf_null) else None)
        if not aniso.get("degenerate"):
            p_vals["mean_cos_beats_aniso_p95"] = bool(abs(cos_mean) > aniso["direction_cosine"]["abs_cos_p95"])

    # de-anisotropisation: remove top-5 PCs of pooled instruct activations
    deaniso = deanisotropize_and_retest(Ds, Da, Hi_l, n, global_nulls, rng)

    angle_sig_pre = bool(p_vals.get("angle_beats_mc_p5")) and bool(p_vals.get("angle_beats_aniso_p5", False))
    angle_sig_post = bool(deaniso.get("angle_beats_mc_p5")) and bool(deaniso.get("angle_beats_aniso_p5", False))
    mean_sig = bool(p_vals.get("mean_cos_beats_signflip_p95")) and bool(p_vals.get("mean_cos_beats_aniso_p95", False))
    verdict = classify_layer_cell(angle_sig_pre, angle_sig_post, mean_sig)

    return {
        "layer": l, "depth_frac": l / max(1, n_layers - 1),
        "cos_mean_difference": cos_mean,
        "angles_by_k": angles,
        "nulls": {
            "permutation_invariance_check": perm_check,
            "sign_flip_cos_mean": sign_flip,
            "anisotropy_matched": aniso,
        },
        "p_values_at_k8": p_vals,
        "deanisotropized_k8": deaniso,
        "significance": {"angle_sig_pre": angle_sig_pre, "angle_sig_post_deanisotropization": angle_sig_post,
                          "mean_sig": mean_sig},
        "verdict": verdict,
    }


def deanisotropize_and_retest(Ds: np.ndarray, Da: np.ndarray, Hi_l: np.ndarray, n: int,
                               global_nulls: dict[int, dict[str, Any]],
                               rng: np.random.Generator) -> dict[str, Any]:
    """Projects out the top-5 PCs of the pooled instruct activations at this
    layer from both D_s and D_a, then recomputes the k=K_PRIMARY and k=1
    first-principal-angle tests against the same MC/anisotropy nulls."""
    Hc = Hi_l - Hi_l.mean(0, keepdims=True)
    npc = min(N_DEANISO_PC, n - 1, Hc.shape[1])
    _, s_h, Vt_h = np.linalg.svd(Hc, full_matrices=False)
    P = Vt_h[:npc]                                    # (npc, d)
    Ds_p = Ds - (Ds @ P.T) @ P
    Da_p = Da - (Da @ P.T) @ P

    if not np.any(Ds_p) or not np.any(Da_p):
        return {"degenerate_after_projection": True}

    kmax = max(K_LIST)
    _, VtS_p = top_rows_centered(Ds_p, min(kmax, n - 1))
    _, VtA_p = top_rows_centered(Da_p, min(kmax, n - 1))

    out: dict[str, Any] = {"n_pcs_removed": npc, "by_k": {}}
    for k in (1, K_PRIMARY):
        cos_k = principal_angle_cosines(VtS_p, VtA_p, k)
        if cos_k.size == 0:
            out["by_k"][str(k)] = None
            continue
        ang, cos_first = first_principal_angle_deg_cos(cos_k)
        assert abs(ang - math.degrees(math.acos(np.clip(cos_first, -1, 1)))) < 1e-9, \
            "post-projection first_angle/first_cos self-check failed"
        out["by_k"][str(k)] = {"first_principal_angle_deg": ang, "first_cos": cos_first}

    aniso_p = anisotropy_matched_null(Ds_p, Da_p, [1, K_PRIMARY], N_NULL, TOP64, rng)
    out["anisotropy_matched_null_post_projection"] = {
        k: (aniso_p["by_k"].get(str(k)) if not aniso_p.get("degenerate") else None) for k in (1, K_PRIMARY)}

    k8 = out["by_k"].get(str(K_PRIMARY))
    if k8 is not None and not aniso_p.get("degenerate"):
        out["angle_beats_mc_p5"] = bool(k8["first_principal_angle_deg"] < global_nulls[K_PRIMARY]["mc"]["first_angle_deg_p5"])
        out["angle_beats_aniso_p5"] = bool(k8["first_principal_angle_deg"] < aniso_p["by_k"][str(K_PRIMARY)]["first_angle_deg_p5"])
    else:
        out["angle_beats_mc_p5"] = False
        out["angle_beats_aniso_p5"] = False
    return out


# ---------------------------------------------------------------------------
# reproduction of iter-2 headline numbers
# ---------------------------------------------------------------------------
def reproduce_headline_numbers(arrays: dict[str, dict[str, np.ndarray]], n_layers: int,
                                item_info: dict[str, Any], rng: np.random.Generator) -> dict[str, Any]:
    """Recomputes, from the SAME read-only harvest, the four iter-2 headline
    numbers named in the task brief, citing the exact source file:key each
    claim is read from. Uses iter-2's OWN method for each number (mean-
    centered SVD / k=8 / all layers / hs_last / all 160 items for #1-#2 per
    ROOT/screen/step1.py::step1_claim; RMS-normalised 4-layer band + raw
    (uncentered) SVD + within-item-span matched-anisotropy null for #3-#4
    per iter-2 eval's d1_step1.py, whose anchor for 'abliterated' in the
    headline pair is DreamFast/qwen3-4b-heretic, confirmed from
    step1_anchor.json's own anchor block)."""
    repro: dict[str, Any] = {}

    # --- claims 1 & 2: mean first angle 31.1 deg / mean cosine -0.09, hs_last, k=8, all layers, all items ---
    # Replicates ROOT/screen/step1.py VERBATIM (its own LAPACK-SVD `_top_rows` /
    # QR-based `principal_angles`, and its epsilon-guarded cosine), INCLUDING its
    # behaviour on exactly-zero difference layers (SVD of an all-zero matrix still
    # returns *some* arbitrary orthonormal completion from LAPACK, so degenerate
    # layers 0-4 for heretic still get a nonzero "angle" in the original headline;
    # this is a known quirk of the original method, not reproduced by our own
    # cleaner exclusion logic used in the main per-layer analysis below).
    def iter2_top_rows(D: np.ndarray, k: int) -> np.ndarray:
        _, _, Vt = np.linalg.svd(D - D.mean(0, keepdims=True), full_matrices=False)
        return Vt[: min(k, Vt.shape[0])]

    def iter2_principal_angles(A: np.ndarray, B: np.ndarray) -> np.ndarray:
        Qa, _ = np.linalg.qr(A.T)
        Qb, _ = np.linalg.qr(B.T)
        s = np.linalg.svd(Qa.T @ Qb, compute_uv=False)
        return np.arccos(np.clip(s, -1.0, 1.0))

    claimed_anchor = json.loads(STEP1_ANCHOR_JSON.read_text())
    assert claimed_anchor["anchor"]["abliterated"] == "DreamFast/qwen3-4b-heretic"
    claimed_headline = claimed_anchor["headline"]
    Hi = arrays["instruct"]["hs_last"].astype(np.float64)
    Hs = arrays["saferl"]["hs_last"].astype(np.float64)
    Ha = arrays["heretic"]["hs_last"].astype(np.float64)
    ang_all, cos_all = [], []
    n_degenerate_included = 0
    for l in range(n_layers):
        Ds = Hs[:, l, :] - Hi[:, l, :]
        Da = Ha[:, l, :] - Hi[:, l, :]
        ms, ma = Ds.mean(0), Da.mean(0)
        cos_all.append(float(ms @ ma / (np.linalg.norm(ms) * np.linalg.norm(ma) + 1e-12)))
        if not np.any(Ds) or not np.any(Da):
            n_degenerate_included += 1
        VtS = iter2_top_rows(Ds, K_PRIMARY)
        VtA = iter2_top_rows(Da, K_PRIMARY)
        ang = iter2_principal_angles(VtS, VtA)
        ang_all.append(float(np.degrees(ang[0])))
    recomputed_mean_angle = float(np.mean(ang_all))
    recomputed_mean_cos = float(np.mean(cos_all))
    logger.info(f"repro claims 1&2: {n_degenerate_included} exactly-zero-difference layers "
                f"still contributed a (numerically arbitrary) nonzero angle, matching the "
                f"original method's known quirk on degenerate SVD input.")

    repro["mean_first_principal_angle_deg"] = {
        "claimed": 31.1, "claimed_exact": claimed_headline["mean_first_principal_angle_deg_last_prompt_token"],
        "recomputed": recomputed_mean_angle,
        "source_file": str(STEP1_ANCHOR_JSON), "json_key": "headline.mean_first_principal_angle_deg_last_prompt_token",
        "reproduced": bool(abs(recomputed_mean_angle - 31.1) < 0.1),
        "note": ("Recomputed via ROOT/screen/step1.py's exact method: top-8 right-singular "
                 "subspaces of the MEAN-CENTERED per-item differences (Ds, Da), hs_last, all "
                 "37 layer slots (0..36) including the degenerate all-zero layers, all 160 items, "
                 "abliterated=DreamFast/qwen3-4b-heretic per step1_anchor.json's own anchor block."),
    }
    repro["mean_cosine_between_mean_difference_vectors"] = {
        "claimed": -0.09, "claimed_exact": claimed_headline["mean_cosine_between_mean_difference_vectors"],
        "recomputed": recomputed_mean_cos,
        "source_file": str(STEP1_ANCHOR_JSON), "json_key": "headline.mean_cosine_between_mean_difference_vectors",
        "reproduced": bool(abs(recomputed_mean_cos - (-0.09)) < 0.02),
        "note": "Same recomputation as above; cos_mean_difference is unsigned mean-centering-independent (raw D means).",
    }

    # --- claims 3 & 4: max|cos| 0.20 vs null p95 0.41 (safe_vs_heretic, band w4_L24-27, k=1);
    #     positive control |cos| 0.92 vs null p95 0.72 (mlab_vs_heretic positive control, its own strongest cell) ---
    d1 = json.loads(D1_STEP1_JSON.read_text())
    hn = d1["headline_numbers"]
    prov = d1["headline_numbers_provenance"]
    assert prov["verdict_cell"] == "w4_L24-27" and prov["read_position"] == "hs_last"
    layers_band = [24, 25, 26, 27]

    def band_matrix(Hchild: np.ndarray, Hinstruct: np.ndarray, layers: list[int]) -> np.ndarray:
        blocks = []
        for l in layers:
            X = Hchild[:, l, :] - Hinstruct[:, l, :]
            rms = float(np.sqrt((X ** 2).sum(1).mean()))
            blocks.append(X / rms if rms > 0 else X)
        return np.hstack(blocks)

    Hmlab = arrays["mlab"]["hs_last"].astype(np.float64)
    D_safe_band = band_matrix(Hs, Hi, layers_band)
    D_heretic_band = band_matrix(Ha, Hi, layers_band)
    D_mlab_band = band_matrix(Hmlab, Hi, layers_band)

    def within_item_span_signed_cos_and_null(DA: np.ndarray, DB: np.ndarray, B: int,
                                              rng: np.random.Generator) -> dict[str, Any]:
        mean_a, mean_b = DA.mean(0), DB.mean(0)
        raw = signed_cos(mean_a, mean_b)
        sA, VtA = row_svd(DA)
        sB, VtB = row_svd(DB)
        C = VtA @ VtB.T
        n = DA.shape[0]
        Ga = rng.standard_normal((B, n))
        Gb = rng.standard_normal((B, n))
        A = sA[None, :] * Ga
        Bm = sB[None, :] * Gb
        num = np.einsum("bi,ij,bj->b", A, C, Bm)
        den = np.linalg.norm(A, axis=1) * np.linalg.norm(Bm, axis=1)
        cos_null = np.abs(num / den)
        return {"observed_signed_cos": raw, "null_p95_abs_cos": float(np.percentile(cos_null, 95)),
                "null_B": B}

    sh = within_item_span_signed_cos_and_null(D_safe_band, D_heretic_band, B_REPRO_NULL, rng)
    pc = within_item_span_signed_cos_and_null(D_mlab_band, D_heretic_band, B_REPRO_NULL, rng)

    repro["max_abs_cos_at_verdict_band_vs_null_p95"] = {
        "claimed": "max |cos| 0.20 vs null p95 0.41",
        "claimed_exact": {"signed_cos_safe_vs_heretic": hn["signed_cos_safe_vs_heretic"],
                           "null_p95_at_verdict_band": hn["null_p95_at_verdict_band"]},
        "recomputed": {"signed_cos_safe_vs_heretic": sh["observed_signed_cos"],
                        "null_p95_abs_cos": sh["null_p95_abs_cos"]},
        "source_file": str(D1_STEP1_JSON),
        "json_key": "headline_numbers.signed_cos_safe_vs_heretic, headline_numbers.null_p95_at_verdict_band "
                    "(provenance: headline_numbers_provenance.verdict_cell = w4_L24-27, hs_last)",
        "reproduced": bool(abs(abs(sh["observed_signed_cos"]) - 0.20) < 0.02
                           and abs(sh["null_p95_abs_cos"] - 0.41) < 0.05),
        "note": ("Recomputed via iter-2 d1_step1.py's own band_matrix (RMS-normalise each of "
                 "layers 24-27 then concatenate) + within-item-span matched-anisotropy null "
                 "(k=1, B=1000 to match d1_step1.py's B_null), safe_vs_heretic pair, hs_last."),
    }
    repro["positive_control_abs_cos_vs_null_p95"] = {
        "claimed": "positive control |cos| 0.92 > null p95 0.72",
        "claimed_exact": {"positive_control_abs_cos": hn["positive_control_abs_cos"],
                           "positive_control_null_p95": hn["positive_control_null_p95"]},
        "recomputed": {"abs_cos": abs(pc["observed_signed_cos"]), "null_p95": pc["null_p95_abs_cos"]},
        "source_file": str(D1_STEP1_JSON),
        "json_key": "headline_numbers.positive_control_abs_cos, headline_numbers.positive_control_null_p95",
        # "to within rounding" = 0.01 on the 2-decimal claim; the qualitative ordering is reported apart
        "reproduced": bool(abs(abs(pc["observed_signed_cos"]) - 0.92) < 0.01
                           and abs(pc["null_p95_abs_cos"] - 0.72) < 0.01),
        "qualitative_holds_control_exceeds_null": bool(abs(pc["observed_signed_cos"]) > pc["null_p95_abs_cos"]),
        "note": ("Positive control = mlabonne vs heretic (two INDEPENDENT abliteration edits, "
                 "expected to converge on one direction). d1_step1.json records this at 'its own "
                 "strongest cell' (found by scanning bands/layers), not necessarily w4_L24-27; we "
                 "recompute at the SAME w4_L24-27 band for a controlled, cited comparison, so an "
                 "imperfect match here is expected and reported honestly rather than cell-searched "
                 "to force a match."),
    }
    return repro


# ---------------------------------------------------------------------------
# JSON-safety
# ---------------------------------------------------------------------------
def json_safe(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_safe(v) for v in o]
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return json_safe(o.tolist())
    return o


# ---------------------------------------------------------------------------
# figure
# ---------------------------------------------------------------------------
def make_figure(analysis: dict[str, Any]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    colors = {"mlab": "tab:blue", "heretic": "tab:orange"}
    for arm in ABL_ARMS:
        key = f"{PRIMARY_SITE}|{arm}|{PRIMARY_SUBSET}"
        rows = analysis["per_layer"].get(key, [])
        if not rows:
            continue
        layers = [r["layer"] for r in rows]
        ang = [r["angles_by_k"][str(K_PRIMARY)]["first_principal_angle_deg"] for r in rows]
        cos = [abs(r["cos_mean_difference"]) if r["cos_mean_difference"] is not None else np.nan for r in rows]
        aniso_p5 = [r["nulls"]["anisotropy_matched"]["by_k"].get(str(K_PRIMARY), {}).get("first_angle_deg_p5")
                    if not r["nulls"]["anisotropy_matched"].get("degenerate") else None for r in rows]
        aniso_cos_p95 = [r["nulls"]["anisotropy_matched"].get("direction_cosine", {}).get("abs_cos_p95")
                         if not r["nulls"]["anisotropy_matched"].get("degenerate") else None for r in rows]
        axes[0].plot(layers, ang, marker="o", ms=3, color=colors[arm], label=f"first angle (k={K_PRIMARY}), {arm}")
        axes[0].plot(layers, aniso_p5, ls="--", lw=1, color=colors[arm], alpha=0.5,
                     label=f"anisotropy-null p5, {arm}")
        axes[1].plot(layers, cos, marker="o", ms=3, color=colors[arm], label=f"|cos(mean_s,mean_a)|, {arm}")
        axes[1].plot(layers, aniso_cos_p95, ls="--", lw=1, color=colors[arm], alpha=0.5,
                     label=f"anisotropy-null p95, {arm}")

    axes[0].set_ylabel("first principal angle (deg), k=8")
    axes[0].set_title(f"Step1 reconciliation: {PRIMARY_SITE}, {PRIMARY_SUBSET} items, "
                       f"instruct vs SafeRL vs abliteration arms")
    axes[0].legend(fontsize=7, loc="upper right")
    axes[0].axhline(90, color="gray", lw=0.5, ls=":")
    axes[1].set_ylabel("|cos(mean D_s, mean D_a)|")
    axes[1].set_xlabel("layer slot (0=embeddings)")
    axes[1].legend(fontsize=7, loc="upper right")
    for ax in axes:
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=150)
    plt.close(fig)
    logger.info(f"figure saved: {FIG_PATH}")


# ---------------------------------------------------------------------------
# verdicts
# ---------------------------------------------------------------------------
def rollup_verdicts(analysis: dict[str, Any]) -> dict[str, Any]:
    def majority(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"verdict": "NO_DATA", "counts": {}}
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        best = max(counts, key=counts.get)
        return {"verdict": best, "counts": counts, "n_layers": len(rows)}

    out: dict[str, Any] = {"by_combo": {}}
    for key, rows in analysis["per_layer"].items():
        out["by_combo"][key] = majority(rows)

    for site in SITES:
        site_rows: list[dict[str, Any]] = []
        for arm in ABL_ARMS:
            for subset in ITEM_SUBSETS:
                site_rows.extend(analysis["per_layer"].get(f"{site}|{arm}|{subset}", []))
        out[site] = majority(site_rows)

    primary_key = f"{PRIMARY_SITE}|{PRIMARY_ARM}|{PRIMARY_SUBSET}"
    out["primary"] = {"combo": primary_key, **majority(analysis["per_layer"].get(primary_key, []))}
    out["overall"] = out["primary"]["verdict"]
    return out


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
@logger.catch(reraise=True)
def run() -> dict:
    t_start = time.time()
    rng = np.random.default_rng(SEED)

    logger.info("loading items and harvest arrays")
    item_info = load_items()
    arrays, n_layers = load_site_arrays()

    # numerics sanity check: Gram-SVD route vs LAPACK on one real block
    Hi = arrays["instruct"]["hs_last"][:, 18, :].astype(np.float64)
    Hs = arrays["saferl"]["hs_last"][:, 18, :].astype(np.float64)
    D_check = Hs - Hi
    s_g, Vt_g = row_svd(D_check)
    _, s_l, Vt_l = np.linalg.svd(D_check, full_matrices=False)
    rel_err = float(np.abs(s_g - s_l).max() / max(s_l.max(), 1e-300))
    logger.info(f"Gram-SVD vs LAPACK max relative singular-value error: {rel_err:.3e}")
    assert rel_err < 1e-8, "Gram-SVD route diverges from LAPACK -- numerics bug"

    logger.info("computing global (data-independent) random-subspace nulls per k")
    global_nulls: dict[int, dict[str, Any]] = {}
    for k in K_LIST:
        mc = mc_random_subspace_null(D_AMBIENT, k, N_NULL, rng)
        an = analytic_random_subspace_null(D_AMBIENT, k)
        Ga = rng.standard_normal((N_NULL, D_AMBIENT, k))
        Gb = rng.standard_normal((N_NULL, D_AMBIENT, k))
        Qa, _ = np.linalg.qr(Ga); Qb, _ = np.linalg.qr(Gb)
        M = np.matmul(np.swapaxes(Qa, -1, -2), Qb)
        s = np.linalg.svd(M, compute_uv=False)
        first_angle_deg_samples = np.degrees(np.arccos(np.clip(s[:, 0], 0, 1)))
        global_nulls[k] = {"mc": mc, "analytic": an, "mc_samples_first_angle_deg": first_angle_deg_samples}
        logger.info(f"k={k}: MC first-angle p5={mc['first_angle_deg_p5']:.2f} deg, "
                    f"|cos| p95={mc['abs_cos_first_p95']:.3f}; analytic_exact={an.get('analytic_exact')}")

    # ---- TEST PHASE: 2 layers first ----
    test_layers = [0, 18]
    logger.info(f"TEST PHASE on layers {test_layers}")
    t0 = time.time()
    test_analysis = analyse(arrays, n_layers, item_info, test_layers, global_nulls, rng)
    logger.info(f"test phase done in {time.time()-t0:.1f}s")
    for key, rows in test_analysis["per_layer"].items():
        for r in rows:
            assert "verdict" in r and r["verdict"] in VERDICT_LABELS
    logger.info("TEST PHASE passed sanity checks (verdict labels well-formed)")

    # ---- FULL PHASE: all layers ----
    all_layers = list(range(n_layers))
    logger.info(f"FULL PHASE on all {n_layers} layers")
    t0 = time.time()
    full_analysis = analyse(arrays, n_layers, item_info, all_layers, global_nulls, rng)
    logger.info(f"full phase done in {time.time()-t0:.1f}s")

    logger.info("reproducing iter-2 headline numbers")
    repro = reproduce_headline_numbers(arrays, n_layers, item_info, rng)
    for name, v in repro.items():
        logger.info(f"repro[{name}]: reproduced={v['reproduced']} recomputed={v.get('recomputed')}")

    logger.info("rolling up verdicts")
    verdicts = rollup_verdicts(full_analysis)
    logger.info(f"verdicts: {json.dumps({k: v for k, v in verdicts.items() if k != 'by_combo'}, default=str)}")

    logger.info("writing figure")
    make_figure(full_analysis)

    result = {
        "meta": {
            "workspace": str(WORKSPACE), "root_inputs": str(ROOT), "iter2_eval_inputs": str(ITER2_EVAL),
            "checkpoints": CHECKPOINTS, "sites": SITES, "abl_arms": ABL_ARMS, "item_subsets": ITEM_SUBSETS,
            "k_list": K_LIST, "k_primary": K_PRIMARY, "d_ambient": D_AMBIENT, "n_null_draws": N_NULL,
            "n_repro_null_draws": B_REPRO_NULL, "n_deaniso_pcs": N_DEANISO_PC, "seed": SEED,
            "n_layers": n_layers, "n_items": item_info["n"], "n_harmful_items": int(item_info["harmful_mask"].sum()),
            "primary_scope": {"site": PRIMARY_SITE, "abl_arm": PRIMARY_ARM, "item_subset": PRIMARY_SUBSET,
                               "k": K_PRIMARY},
            "gram_svd_vs_lapack_rel_error_check": rel_err,
            "runtime_minutes_so_far": (time.time() - t_start) / 60.0,
        },
        "reconciliation_hypothesis": RECONCILIATION_HYPOTHESIS,
        "decision_rule": {"labels": VERDICT_LABELS, "logic_text": DECISION_RULE_TEXT},
        "global_random_subspace_nulls": {str(k): {"mc": v["mc"], "analytic": v["analytic"]}
                                          for k, v in global_nulls.items()},
        "reproduction_of_iter2_headline_numbers": repro,
        "excluded_layers": full_analysis["excluded_layers"],
        "per_layer": full_analysis["per_layer"],
        "verdicts": verdicts,
    }
    result["meta"]["runtime_minutes_total"] = (time.time() - t_start) / 60.0

    safe = json_safe(result)
    OUT_JSON.write_text(json.dumps(safe, indent=2, allow_nan=False))
    logger.info(f"wrote {OUT_JSON} ({OUT_JSON.stat().st_size/1e6:.2f} MB)")
    logger.info(f"TOTAL runtime: {(time.time()-t_start)/60.0:.2f} min")
    return safe


if __name__ == "__main__":
    run()

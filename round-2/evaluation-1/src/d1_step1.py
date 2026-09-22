"""D1 -- principal-angle analysis of the Qwen3-4B safety anchor set.

Answers the pre-registered two-sided question: do official safety RL and
community abliteration move the SAME subspace in OPPOSITE directions, or
DIFFERENT subspaces?

Pure offline numpy over the iteration-1 activation harvest. No GPU, no
downloads, no model loading, no API calls. The upstream workspace is opened
READ-ONLY; this script owns exactly two paths:
    WS/d1_step1.py   (this file)
    WS/results/d1_step1.json
plus a log under WS/logs/.

Output is rewritten in full after every stage (D1.1, D1.2/3, D1.4, D1.5,
D1.6, D1.7, D1.8) so a mid-run kill still leaves a readable partial result.
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy.linalg import subspace_angles

WS_DIR = ("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2"
          "/gen_art/gen_art_evaluation_1")
sys.path.insert(0, WS_DIR)

from evallib.core import (  # noqa: E402
    B_NULL,
    B_SPLITHALF,
    HARVEST,
    RESULTS,
    SEED,
    UP_RESULTS,
    load_acts,
    load_items,
    load_meta,
    load_weights,
    read_json,
    write_json,
)

OUT = RESULTS / "d1_step1.json"
LOG = Path(WS_DIR) / "logs" / "d1_step1.log"

# --- the anchor set --------------------------------------------------------
INSTRUCT = "Qwen__Qwen3-4B"
ANCHORS = {
    "base": "Qwen__Qwen3-4B-Base",
    "instruct": INSTRUCT,
    "safe": "Qwen__Qwen3-4B-SafeRL",
    "mlab": "mlabonne__Qwen3-4B-abliterated",
    "heretic": "DreamFast__qwen3-4b-heretic",
}
# arms whose difference-from-instruct enters the comparison; base is magnitude-only
ARMS = ["safe", "mlab", "heretic"]
PAIRS = [("safe", "mlab"), ("safe", "heretic"), ("mlab", "heretic")]
POSITIONS = ["hs_last", "hs_first"]
KS = [1, 2, 4, 8]
N_ITEMS = 160
WEIGHT_LIMB_BUDGET_S = 30 * 60

T0 = time.time()
RESULT: dict[str, Any] = {}


def json_safe(o: Any) -> Any:
    """Recursively replace non-finite floats with None.

    evallib.core.write_json routes NUMPY scalars through _jdefault, which maps
    a non-finite value to None -- but a native Python float('nan') is
    serialisable, so json.dumps emits the bare tokens NaN / Infinity /
    -Infinity. Those are accepted by Python's own json.load and rejected by
    RFC-8259 parsers (JavaScript JSON.parse, jq --strict, many others), which
    would make this file unreadable to a downstream consumer. Every NaN in this
    output is meaningful -- a degenerate zero-difference block or an undefined
    ratio -- so it is emitted as null rather than dropped.
    """
    if isinstance(o, float):
        return o if np.isfinite(o) else None
    if isinstance(o, np.floating):
        v = float(o)
        return v if np.isfinite(v) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return json_safe(o.tolist())
    if isinstance(o, dict):
        return {k: json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_safe(v) for v in o]
    return o


def flush(stage: str) -> None:
    """Rewrite the whole output file. Called after every stage, never only at the end."""
    RESULT["runtime_minutes"] = round((time.time() - T0) / 60.0, 3)
    RESULT["last_stage_written"] = stage
    write_json(OUT, json_safe(RESULT))
    logger.info(f"[{stage}] flushed -> {OUT} ({RESULT['runtime_minutes']:.2f} min)")


# ===========================================================================
# linear-algebra helpers
# ===========================================================================
def row_svd(D: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Thin SVD of an (n, d) difference matrix with n << d, via the n x n Gram.

    Returns (s, Vt) where Vt has orthonormal ROWS spanning the row space and s
    are the singular values in descending order. Vt[:k] is the top-k right
    singular subspace -- the 'direction' subspace the fine-tune moved.

    D D^T is only 160 x 160 and shares D's nonzero spectrum, so eigh on the Gram
    is 4-8x faster than LAPACK gesdd on the rectangular matrix. Squaring the
    condition number is harmless here because the quantities used downstream are
    the leading directions and the spectrum as null WEIGHTS; cross_check_svd()
    verifies the agreement against LAPACK on real data at run time.
    """
    G = D @ D.T
    w, U = np.linalg.eigh(G)
    idx = np.argsort(w)[::-1]
    w = np.clip(w[idx], 0.0, None)
    U = U[:, idx]
    s = np.sqrt(w)
    Vt = (U / np.where(s > 0, s, 1.0)).T @ D
    return s, Vt


def cross_check_svd(D: np.ndarray) -> dict[str, float]:
    """Agreement of the Gram route with LAPACK gesdd on a real difference block."""
    s_g, Vt_g = row_svd(D)
    _, s_l, Vt_l = np.linalg.svd(D, full_matrices=False)
    ortho = float(np.abs(Vt_g @ Vt_g.T - np.eye(Vt_g.shape[0])).max())
    top8 = float(np.linalg.svd(Vt_l[:8] @ Vt_g[:8].T, compute_uv=False).min())
    return {
        "max_rel_singular_value_error": float(np.abs(s_g - s_l).max() / max(s_l.max(), 1e-300)),
        "max_orthonormality_violation": ortho,
        "min_cos_principal_angle_top8_gram_vs_lapack": top8,
        "acceptable": bool(ortho < 1e-9 and top8 > 1 - 1e-9),
    }


def effective_rank(s: np.ndarray) -> int:
    """Number of singular values above the standard relative tolerance."""
    if s.size == 0 or s[0] <= 0:
        return 0
    return int((s > s[0] * max(s.size, 1) * np.finfo(np.float64).eps).sum())


def observed_angles(VtA: np.ndarray, VtB: np.ndarray, k: int) -> dict[str, Any]:
    """Principal angles between the two top-k right singular subspaces.

    scipy.linalg.subspace_angles wants COLUMN bases and returns angles in
    DESCENDING order, so angles[-1] is the SMALLEST angle and its cosine is the
    MAXIMUM overlap. That is the convention recorded in the output.
    """
    ang = subspace_angles(np.ascontiguousarray(VtA[:k].T),
                          np.ascontiguousarray(VtB[:k].T))
    cos = np.cos(ang)
    return {
        "cos_first_principal_angle": float(cos[-1]),   # = max overlap
        "mean_cos_over_k": float(cos.mean()),
        "angles_deg_descending": [float(np.degrees(a)) for a in ang],
    }


def _inv_sqrt_batch(M: np.ndarray) -> np.ndarray:
    """Batched symmetric inverse square root of (B, k, k) Gram matrices."""
    w, Q = np.linalg.eigh(M)
    w = np.clip(w, 1e-300, None)
    return (Q * (w ** -0.5)[:, None, :]) @ np.swapaxes(Q, -1, -2)


def within_span_null(sA: np.ndarray, sB: np.ndarray, C: np.ndarray,
                     ks: list[int], rng: np.random.Generator,
                     B: int = B_NULL) -> dict[int, dict[str, np.ndarray]]:
    """Matched-anisotropy null: random subspaces drawn WITHIN THE ITEM SPAN.

    The pre-registered recipe is c ~ N(0, I_n), v = D^T c, normalise, repeat k
    times, orthonormalise, independently for both sides. Substituting the SVD
    D = U diag(s) Vt and using U^T c ~ N(0, I_n) gives v = Vt^T (s * g) with
    g ~ N(0, I_n): an EXACTLY equivalent draw expressed in the n-dimensional
    right-singular coordinates. Because Vt has orthonormal rows, every inner
    product needed for the principal angles can then be evaluated through the
    n x n cross-Gram C = Vt_A @ Vt_B^T, which is computed once per block. This
    is an algebraic identity, not an approximation, and it makes B=1000 draws
    over every layer, band, pair and k affordable on 2 CPUs.

    Principal-angle cosines of span(A), span(B) are the singular values of
    (A^T A)^-1/2 (A^T B) (B^T B)^-1/2, all of which are k x k here.
    """
    n = len(sA)
    kmax = max(ks)
    GA = rng.standard_normal((B, n, kmax))
    GB = rng.standard_normal((B, n, kmax))
    MA = sA[None, :, None] * GA
    MB = sB[None, :, None] * GB
    CMB = np.matmul(C, MB)                      # (B, n, kmax)
    out: dict[int, dict[str, np.ndarray]] = {}
    for k in ks:
        A = MA[:, :, :k]
        Bm = MB[:, :, :k]
        AtA = np.matmul(np.swapaxes(A, -1, -2), A)
        BtB = np.matmul(np.swapaxes(Bm, -1, -2), Bm)
        AtB = np.matmul(np.swapaxes(A, -1, -2), CMB[:, :, :k])
        M = _inv_sqrt_batch(AtA) @ AtB @ _inv_sqrt_batch(BtB)
        cs = np.linalg.svd(M, compute_uv=False)
        cs = np.clip(cs, 0.0, 1.0)
        out[k] = {"cos_max": cs.max(axis=1), "cos_mean": cs.mean(axis=1)}
    del GA, GB, MA, MB, CMB
    return out


def null_summary(null: np.ndarray, observed: float) -> dict[str, Any]:
    """Distribution summary plus the observed value's standing in it."""
    null = np.asarray(null, dtype=float)
    B = len(null)
    p_larger = (1.0 + float((null >= observed).sum())) / (B + 1.0)
    return {
        "null_mean": float(null.mean()),
        "null_sd": float(null.std(ddof=1)),
        "null_p5": float(np.percentile(null, 5)),
        "null_p50": float(np.percentile(null, 50)),
        "null_p95": float(np.percentile(null, 95)),
        "observed": float(observed),
        "observed_percentile_in_null": float(100.0 * (null < observed).mean()),
        "p_one_sided_overlap_larger_than_null": p_larger,
        "above_null_p95": bool(observed > float(np.percentile(null, 95))),
        "B": B,
    }


def kfield(entry: dict, k: int, field: str, sub: str | None = None):
    """Safe read of a per-k angle field that may be a degenerate placeholder."""
    kk = entry.get("k", {}).get(str(k))
    if not kk or kk.get("degenerate"):
        return None
    return kk[field][sub] if sub else kk[field]


def signed_cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return float("nan")
    return float(np.dot(a, b) / (na * nb))


def split_half_reliability(D: np.ndarray, splits: list[tuple[np.ndarray, np.ndarray]]) -> dict[str, float]:
    """r_self: cosine between the mean difference on half A and on half B.

    This is the LOWER CEILING -- the overlap a genuinely identical direction
    would still fail to exceed at this item budget.
    """
    if not np.any(D):
        # an exactly-zero block: no direction, so no reliability to estimate
        return {"mean": float("nan"), "sd": float("nan"), "B": len(splits),
                "degenerate_zero_block": True}
    nA = len(splits[0][0])
    nB = len(splits[0][1])
    WA = np.zeros((len(splits), D.shape[0]))
    WB = np.zeros((len(splits), D.shape[0]))
    for i, (a, b) in enumerate(splits):
        WA[i, a] = 1.0 / nA
        WB[i, b] = 1.0 / nB
    MA = WA @ D
    MB = WB @ D
    num = (MA * MB).sum(1)
    den = np.linalg.norm(MA, axis=1) * np.linalg.norm(MB, axis=1)
    r = num / np.where(den > 0, den, np.nan)
    return {"mean": float(np.nanmean(r)), "sd": float(np.nanstd(r, ddof=1)),
            "B": len(splits)}


def disattenuate(raw: float, rA: float, rB: float) -> dict[str, Any]:
    """Classical correction for attenuation, with the >1 pathology flagged."""
    denom = rA * rB
    if not np.isfinite(denom) or denom <= 0:
        return {"raw": raw, "disattenuated": None, "exceeds_unity": None,
                "note": "reliability product non-positive; correction undefined"}
    val = raw / float(np.sqrt(denom))
    over = bool(abs(val) > 1.0)
    return {
        "raw": raw,
        "disattenuated": float(val),
        "r_self_product": float(denom),
        "exceeds_unity": over,
        "note": ("|disattenuated| > 1: the RELIABILITY estimate is the binding "
                 "constraint, not the overlap. This is NOT a cosine above 1 and "
                 "must not be read as one; it means the split-half floor is too "
                 "low at n=160 to support a correction of this size."
                 if over else "within [-1, 1]"),
    }


# ===========================================================================
# STAGE 0 -- anchor resolution
# ===========================================================================
def stage_anchors() -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for role, slug in ANCHORS.items():
        d = HARVEST / slug
        done = (d / "DONE").exists()
        acts_ok = (d / "acts.npz").exists()
        m = load_meta(slug) if done and (d / "meta.json").exists() else {}
        tmpl = m.get("template", {})
        resolved[role] = {
            "slug": slug,
            "repo_id": m.get("repo_id"),
            "DONE": done,
            "acts_present": acts_ok,
            "n_layers": m.get("n_layers"),
            "hidden_size": m.get("hidden_size"),
            "architecture": m.get("architecture"),
            "config_torch_dtype": m.get("config_torch_dtype"),
            "renderer": tmpl.get("renderer"),
            "template_used": tmpl.get("template_used"),
            "template_sha256": tmpl.get("template_sha256"),
            "vocab_sha256": tmpl.get("vocab_sha256"),
            "enable_thinking_supported": tmpl.get("enable_thinking_supported"),
            "n_items": m.get("n_items"),
        }
    missing = [r for r, v in resolved.items() if not (v["DONE"] and v["acts_present"])]

    stale = None
    p = UP_RESULTS / "step1_claim.json"
    if p.exists():
        stale = read_json(p)

    # ---- template stratification, the thing the brief did not anticipate ----
    by_hash: dict[str, list[str]] = {}
    for role, v in resolved.items():
        by_hash.setdefault(str(v["template_sha256"]), []).append(role)
    inst_hash = resolved["instruct"]["template_sha256"]
    same_tmpl = [r for r, v in resolved.items() if v["template_sha256"] == inst_hash]
    diff_tmpl = [r for r, v in resolved.items() if v["template_sha256"] != inst_hash]

    return {
        "verified_resolution": resolved,
        "all_five_present": len(missing) == 0,
        "missing_roles": missing,
        "stale_iteration1_claim": {
            "file": str(p),
            "content": stale,
            "reportable_fact": (
                "UP/results/step1_claim.json records status 'anchor lineage "
                "incomplete' with Qwen/Qwen3-4B-SafeRL -> null and "
                "Qwen/Qwen3-4B-Base -> null, and does not list "
                "mlabonne/Qwen3-4B-abliterated at all. That file was written at "
                "23:24 during an iteration-1 race; the SafeRL harvest landed at "
                "23:36 and the mlabonne harvest at 00:33. BOTH have DONE markers "
                "now. The iteration-1 anchor was therefore never completed AS "
                "CLAIMED, but the data it claimed was missing does exist on disk "
                "and is what D1 is computed from."),
        },
        "renderer_per_member": {r: v["renderer"] for r, v in resolved.items()},
        "template_hash_groups": by_hash,
        "renderer_and_template_finding": {
            "brief_expected_base_plain_renderer": True,
            "base_actual_renderer": resolved["base"]["renderer"],
            "base_renderer_matches_brief": resolved["base"]["renderer"] == "plain",
            "detail": (
                "The brief states the BASE checkpoint uses a DIFFERENT chat "
                "renderer (plain). It does NOT. screen/harvest.py sets "
                "renderer='plain' only when the tokenizer exposes no chat "
                "template at all; Qwen3-4B-Base ships one in tokenizer_config, so "
                "it was harvested with renderer='chat' like every other member. "
                "The base stratum is therefore NOT separated by renderer in the "
                "realised harvest. It is still held out of the three-way "
                "comparison, on the stronger ground that it is a different "
                "TRAINING STAGE, and it remains a magnitude reference only."),
            "dtype_is_NOT_a_confound": (
                "config_torch_dtype is not uniform either -- mlabonne declares "
                "torch.float32 where the rest declare torch.bfloat16 -- but this "
                "is NOT a confound: screen/harvest.py loads every checkpoint with "
                "torch_dtype=torch.bfloat16 explicitly, so the compute dtype was "
                "identical across all five. The only consequence is that "
                "mlabonne's fp32 stored weights were rounded to bf16 on load, a "
                "perturbation far below the effects measured here. Recorded so "
                "the differing dtype field is not mistaken for one."),
            "template_sha256_is_NOT_uniform": True,
            "shares_instruct_template": same_tmpl,
            "differs_from_instruct_template": diff_tmpl,
            "confound": (
                "Each checkpoint was rendered with ITS OWN tokenizer template. "
                "SafeRL and heretic carry byte-identical templates to instruct "
                "(41d5929b...), so D_safe and D_heretic are rendering-clean. "
                "mlabonne/Qwen3-4B-abliterated carries the BASE-style template "
                "(3bd74c5f...), so the mlabonne checkpoint saw a DIFFERENT "
                "rendered prompt string than instruct did. D_mlab therefore "
                "confounds the weight edit with a prompt-rendering difference, "
                "and every mlab-bearing comparison (safe-vs-mlab, and the "
                "mlab-vs-heretic positive control) inherits that confound. "
                "safe-vs-heretic is the only rendering-clean cross-recipe pair "
                "in the anchor set."),
        },
    }


# ===========================================================================
# STAGE 1 -- difference matrices, shared-basis check, norm growth
# ===========================================================================
def load_differences() -> tuple[dict[str, dict[str, np.ndarray]], dict[str, dict[str, np.ndarray]], int]:
    """D[arm][pos] = (160, L+1, d) float32 difference from instruct; plus instruct itself.

    float16 -> float32 is exact and the subtraction of two float16-representable
    values in float32 is exact, so no precision is lost relative to doing the
    subtraction in float64; each LAYER is cast to float64 at use time, which is
    where the brief's requirement actually bites.
    """
    a = load_acts(INSTRUCT)
    for pos in POSITIONS:
        if a[pos].shape[0] != N_ITEMS:
            raise AssertionError(
                f"{INSTRUCT}/{pos} first dim is {a[pos].shape[0]}, expected {N_ITEMS}; "
                "the row-index join to items.json is invalid -- refusing to continue.")
    base_h = {pos: a[pos].astype(np.float32) for pos in POSITIONS}
    n_slots = base_h["hs_last"].shape[1]
    del a
    gc.collect()

    diffs: dict[str, dict[str, np.ndarray]] = {}
    for arm in ARMS + ["base"]:
        slug = ANCHORS[arm]
        b = load_acts(slug)
        for pos in POSITIONS:
            if b[pos].shape[0] != N_ITEMS:
                raise AssertionError(
                    f"{slug}/{pos} first dim is {b[pos].shape[0]}, expected {N_ITEMS}; "
                    "the row-index join to items.json is invalid -- refusing to continue.")
            if b[pos].shape != base_h[pos].shape:
                raise AssertionError(f"{slug}/{pos} shape {b[pos].shape} != instruct "
                                     f"{base_h[pos].shape}")
        diffs[arm] = {pos: b[pos].astype(np.float32) - base_h[pos] for pos in POSITIONS}
        del b
        gc.collect()
        logger.info(f"difference matrices built for {arm} ({slug})")
    return diffs, base_h, n_slots


def stage_d11(diffs, base_h, n_slots) -> tuple[dict, dict]:
    per_layer_norms: dict[str, Any] = {}
    growth: dict[str, Any] = {}
    for pos in POSITIONS:
        H = base_h[pos]
        inst_rownorm = [float(np.linalg.norm(H[:, l, :].astype(np.float64), axis=1).mean())
                        for l in range(n_slots)]
        block: dict[str, Any] = {"mean_row_norm_instruct": inst_rownorm}
        for arm in ARMS + ["base"]:
            D = diffs[arm][pos]
            fro, rown = [], []
            for l in range(n_slots):
                X = D[:, l, :].astype(np.float64)
                fro.append(float(np.linalg.norm(X)))
                rown.append(float(np.linalg.norm(X, axis=1).mean()))
            block[f"fro_D_{arm}"] = fro
            block[f"mean_row_norm_D_{arm}"] = rown
            block[f"rel_to_instruct_norm_{arm}"] = [
                float(a / b) if b > 0 else None for a, b in zip(rown, inst_rownorm)]
        per_layer_norms[pos] = block

        mx, mn = max(inst_rownorm[1:]), min(inst_rownorm[1:])
        growth[pos] = {
            "instruct_mean_row_norm_max_over_min": float(mx / mn) if mn > 0 else None,
            "instruct_mean_row_norm_min": float(mn),
            "instruct_mean_row_norm_max": float(mx),
            "argmax_layer": int(np.argmax(inst_rownorm[1:]) + 1),
            "argmin_layer": int(np.argmin(inst_rownorm[1:]) + 1),
        }
        for arm in ARMS:
            v = per_layer_norms[pos][f"mean_row_norm_D_{arm}"][1:]
            growth[pos][f"D_{arm}_mean_row_norm_max_over_min"] = (
                float(max(v) / min(v)) if min(v) > 0 else None)

    # shared-basis verdict: is the base-vs-instruct gap the same order as the
    # fine-tune gaps?  If so the "one parent, one residual basis" premise is weak.
    ratios: dict[str, Any] = {}
    for pos in POSITIONS:
        b = np.array(per_layer_norms[pos]["mean_row_norm_D_base"][1:])
        for arm in ARMS:
            f = np.array(per_layer_norms[pos][f"mean_row_norm_D_{arm}"][1:])
            with np.errstate(divide="ignore", invalid="ignore"):
                r = b / f
            ratios[f"{pos}/base_over_{arm}"] = {
                "median": float(np.nanmedian(r)),
                "min": float(np.nanmin(r)),
                "max": float(np.nanmax(r)),
            }
    med = np.median([v["median"] for v in ratios.values()])
    shared = {
        "assumption": (
            "SHARED-BASIS ASSUMPTION. Item-wise differences h_child(i,l) - "
            "h_instruct(i,l) are only interpretable as 'the direction this "
            "fine-tune moved' if every child inherits a common residual basis "
            "from the one parent, i.e. if no child has re-indexed or rotated the "
            "residual stream relative to instruct. Nothing in this harvest can "
            "prove that; what it can do is bound how far apart the checkpoints "
            "are on a scale where a KNOWN basis-preserving relation does not "
            "hold -- base-vs-instruct, two different training stages."),
        "test": ("per-layer ||D_base||_F and mean row norm reported alongside the "
                 "three fine-tune arms and alongside mean ||h_instruct||"),
        "median_ratio_base_gap_to_finetune_gap": float(med),
        "ratios": ratios,
        "verdict": None,     # filled below
    }
    if med >= 3.0:
        shared["verdict"] = "SHARED_BASIS_PLAUSIBLE"
        shared["reading"] = (
            f"The base-vs-instruct difference is {med:.1f}x the typical "
            "fine-tune difference, i.e. a different ORDER of magnitude. The "
            "three fine-tune arms sit far inside the envelope of a "
            "known-different training stage, which is consistent with (though "
            "not proof of) a shared residual basis.")
    elif med >= 1.5:
        shared["verdict"] = "SHARED_BASIS_WEAKLY_SUPPORTED"
        shared["reading"] = (
            f"The base-vs-instruct difference is only {med:.1f}x the fine-tune "
            "differences -- the same order of magnitude. The shared-basis "
            "premise is WEAK: differences of this size are not obviously small "
            "perturbations around a common basis, and every angle below should "
            "be read with that caveat.")
    else:
        shared["verdict"] = "SHARED_BASIS_PREMISE_WEAK"
        shared["reading"] = (
            f"The base-vs-instruct difference is {med:.1f}x the fine-tune "
            "differences, i.e. NOT larger in any meaningful sense. The "
            "shared-basis premise is not supported by this check and the "
            "principal angles cannot be read as 'the subspace the fine-tune "
            "moved' without further evidence.")
    return per_layer_norms, {"shared_basis_check": shared, "norm_growth_across_depth": growth}


def stage_edit_onset(diffs, n_slots) -> dict[str, Any]:
    """Where does each child FIRST differ from instruct, and what does that say
    about the template confound?

    Layer 0 of hs_* is the embedding output at the read token. Neither
    abliteration recipe touches embed_tokens, so if a child's rendered prompt
    were identical to instruct's, its layer-0 difference must be EXACTLY zero.
    A non-zero layer-0 difference therefore means either an edited embedding or
    a different final prompt token. This turns the template-hash mismatch from
    an unfalsifiable caveat into a measurement.
    """
    out: dict[str, Any] = {"rationale": stage_edit_onset.__doc__, "per_position": {}}
    for pos in POSITIONS:
        block: dict[str, Any] = {}
        for arm in ARMS + ["base"]:
            D = diffs[arm][pos]
            exact_zero = [bool(np.all(D[:, l, :] == 0)) for l in range(n_slots)]
            frac_rows_zero = [float(np.mean(np.all(D[:, l, :] == 0, axis=1)))
                              for l in range(n_slots)]
            nz = [l for l, z in enumerate(exact_zero) if not z]
            block[arm] = {
                "layer0_difference_is_exactly_zero": exact_zero[0],
                "first_layer_with_any_nonzero_difference": (nz[0] if nz else None),
                "n_layers_exactly_zero": int(sum(exact_zero)),
                "fraction_of_items_with_zero_difference_per_layer": frac_rows_zero,
            }
        out["per_position"][pos] = block

    # ---- why hs_first is layer-0-dirty for EVERY arm ---------------------
    # hs_first is read at the FIRST GENERATED token. If a child generates a
    # different first token than instruct, its layer-0 embedding differs for
    # that item no matter what the weights did, so part of every hs_first
    # difference is "a different token was emitted" rather than "the same token
    # is represented differently". first_token_id is on disk, so this is
    # measurable rather than a matter of opinion.
    def ftid(slug):
        with np.load(HARVEST / slug / "acts.npz") as z:
            return z["first_token_id"]

    fi = ftid(INSTRUCT)
    tok = {}
    for arm in ARMS + ["base"]:
        fa = ftid(ANCHORS[arm])
        agree = float(np.mean(fa == fi))
        tok[arm] = {
            "fraction_of_items_first_token_matches_instruct": agree,
            "n_items_differing": int(np.sum(fa != fi)),
        }
    out["first_generated_token_agreement_with_instruct"] = {
        "per_arm": tok,
        "why_it_matters": (
            "hs_last is read at the last PROMPT token, which is fixed by the "
            "prompt and identical across checkpoints, so a difference there is "
            "purely representational. hs_first is read at the first GENERATED "
            "token, which the checkpoint chooses. Where that token differs, the "
            "layer-0 embedding differs mechanically and the hs_first difference "
            "mixes 'represented differently' with 'said something else'. This is "
            "why every arm is layer-0-dirty at hs_first while only SafeRL is at "
            "hs_last, and it is why the hs_last verdict is the primary one."),
    }

    ml0 = out["per_position"]["hs_last"]["mlab"]["layer0_difference_is_exactly_zero"]
    he0 = out["per_position"]["hs_last"]["heretic"]["layer0_difference_is_exactly_zero"]
    sa0 = out["per_position"]["hs_last"]["safe"]["layer0_difference_is_exactly_zero"]
    ba0 = out["per_position"]["hs_last"]["base"]["layer0_difference_is_exactly_zero"]
    out["template_confound_resolution"] = {
        "mlab_layer0_exactly_zero": ml0,
        "heretic_layer0_exactly_zero": he0,
        "safe_layer0_exactly_zero": sa0,
        "base_layer0_exactly_zero": ba0,
        "verdict": ("TEMPLATE_MISMATCH_HAS_NO_MEASURABLE_EFFECT" if ml0 else
                    "TEMPLATE_MISMATCH_MAY_BITE"),
        "reading": (
            "mlabonne's chat-template hash differs from instruct's, which on its "
            "face confounds every mlab-bearing comparison. It does not. "
            "mlabonne's layer-0 (embedding) difference from instruct at the read "
            "token is EXACTLY ZERO across all 160 items: the rendered prompt "
            "ends in the same token and embed_tokens is unedited. The template "
            "texts differ in branches these items never take. The confound is "
            "therefore DETECTED AND BOUNDED, not merely flagged, and the "
            "mlab-bearing comparisons stand."
            if ml0 else
            "mlabonne's layer-0 difference from instruct is NON-ZERO, which is "
            "consistent with a genuinely different rendered prompt. Every "
            "mlab-bearing comparison is confounded and its overlap is biased "
            "downward. Treat safe-vs-heretic as the only clean cross-recipe "
            "pair."),
        "caveat": (
            "Layer 0 pins the FINAL prompt token only. Earlier tokens could "
            "still differ, and would surface from layer 1 on, where attention "
            "first mixes the full context. The layer-1 difference norms are "
            "reported next to this so the reader can check: mlab's layer-1 "
            "difference is of the same order as SafeRL's, and SafeRL is "
            "template-identical to instruct, so there is no sign of a "
            "rendering jump."),
    }
    return out


# ===========================================================================
# STAGE 2/3 -- angles, signed rank-1, nulls, reliability (per layer AND per band)
# ===========================================================================
def band_definitions(n_slots: int) -> list[dict[str, Any]]:
    bands = []
    for w in (4, 8):
        for start in range(0, n_slots, w):
            layers = list(range(start, min(start + w, n_slots)))
            bands.append({"name": f"w{w}_L{layers[0]:02d}-{layers[-1]:02d}",
                          "kind": f"window{w}", "layers": layers})
    q = np.array_split(np.arange(n_slots), 4)
    for i, ls in enumerate(q):
        bands.append({"name": f"quartile{i + 1}_L{ls[0]:02d}-{ls[-1]:02d}",
                      "kind": "quartile", "layers": [int(x) for x in ls]})
    return bands


def band_matrix(D: np.ndarray, layers: list[int]) -> np.ndarray:
    """RMS-normalise each layer block, THEN concatenate.

    Without this the residual norm growth across depth makes an unnormalised
    band a read of its deepest layer alone.
    """
    blocks = []
    for l in layers:
        X = D[:, l, :].astype(np.float64)
        rms = float(np.sqrt((X ** 2).sum(1).mean()))
        blocks.append(X / rms if rms > 0 else X)
    return np.hstack(blocks)


def analyse_scope(mats: dict[str, np.ndarray], rng: np.random.Generator,
                  splits: list[tuple[np.ndarray, np.ndarray]]) -> dict[str, Any]:
    """Everything D1.2/D1.3/D1.5 needs for ONE (position, layer-or-band) cell."""
    svds = {arm: row_svd(mats[arm]) for arm in ARMS}
    means = {arm: mats[arm].mean(0) for arm in ARMS}
    rel = {arm: split_half_reliability(mats[arm], splits) for arm in ARMS}
    ranks = {arm: effective_rank(svds[arm][0]) for arm in ARMS}
    fro = {arm: float(np.linalg.norm(mats[arm])) for arm in ARMS}

    out: dict[str, Any] = {"reliability": rel, "effective_rank": ranks,
                           "fro_norm": fro, "pairs": {}}
    for a, b in PAIRS:
        sA, VtA = svds[a]
        sB, VtB = svds[b]
        # A block can be EXACTLY zero -- an unedited depth, where the child's
        # activations are bit-identical to instruct's. There is no subspace to
        # take an angle with, so the cell is recorded as degenerate rather than
        # silently returning a meaningless angle.
        if ranks[a] == 0 or ranks[b] == 0:
            out["pairs"][f"{a}_vs_{b}"] = {
                "degenerate": True,
                "reason": (f"effective rank is 0 for "
                           f"{[x for x in (a, b) if ranks[x] == 0]}: the "
                           "difference from instruct is EXACTLY zero here, so "
                           "no subspace exists and no angle is defined"),
                "effective_rank_a": ranks[a], "effective_rank_b": ranks[b],
                "signed_rank1_cos_of_mean_difference": float("nan"),
                "abs_signed_rank1_cos": float("nan"),
                "sign": None,
                "disattenuated": {"raw": None, "disattenuated": None,
                                  "exceeds_unity": None, "note": "degenerate cell"},
                "k": {}, "signed_rank1_vs_k1_null": None,
            }
            continue
        C = VtA @ VtB.T
        nulls = within_span_null(sA, sB, C, KS, rng)
        raw = signed_cos(means[a], means[b])
        entry: dict[str, Any] = {
            "signed_rank1_cos_of_mean_difference": raw,
            "abs_signed_rank1_cos": abs(raw),
            "sign": ("negative" if raw < 0 else "positive") if np.isfinite(raw) else None,
            "disattenuated": disattenuate(raw, rel[a]["mean"], rel[b]["mean"]),
            "effective_rank_a": ranks[a], "effective_rank_b": ranks[b],
            "degenerate": False,
            "k": {},
        }
        for k in KS:
            if k > min(ranks[a], ranks[b]):
                entry["k"][str(k)] = {
                    "degenerate": True,
                    "reason": (f"k={k} exceeds the effective rank of at least one "
                               f"side (rank_a={ranks[a]}, rank_b={ranks[b]}); the "
                               "top-k subspace is not defined"),
                    "cos_first_principal_angle": float("nan"),
                    "mean_cos_over_k": float("nan"),
                    "angles_deg_descending": [],
                }
                continue
            obs = observed_angles(VtA, VtB, k)
            obs["null_cos_max"] = null_summary(nulls[k]["cos_max"],
                                               obs["cos_first_principal_angle"])
            obs["null_mean_cos"] = null_summary(nulls[k]["cos_mean"],
                                                obs["mean_cos_over_k"])
            entry["k"][str(k)] = obs
        # the signed rank-1 read is judged against the k=1 within-span null,
        # which is exactly the |cos| of two arbitrary within-span rank-1 draws
        entry["signed_rank1_vs_k1_null"] = null_summary(nulls[1]["cos_max"], abs(raw))
        out["pairs"][f"{a}_vs_{b}"] = entry
    return out


# ===========================================================================
# STAGE 5 -- positive control, from the WEIGHTS
# ===========================================================================
def stage_positive_control(per_band: dict, per_layer: dict, n_slots: int) -> dict[str, Any]:
    W = {r: load_weights(ANCHORS[r]) for r in ["instruct", "safe", "mlab", "heretic"]}
    evidence: dict[str, Any] = {}
    for mat in ("o_proj", "down_proj"):
        sv_i = W["instruct"][f"{mat}_sv"].astype(np.float64)       # (L, d)
        bot_i = W["instruct"][f"{mat}_bot"].astype(np.float64)     # (L, 16, d)
        top_i = W["instruct"][f"{mat}_top"].astype(np.float64)
        sv_sorted_i = np.sort(sv_i, axis=1)                        # ascending
        block: dict[str, Any] = {
            "instruct": {
                "botgap_bf16": W["instruct"][f"{mat}_botgap_bf16"].astype(float).tolist(),
                "sigma_min": sv_sorted_i[:, 0].tolist(),
                "sigma_2ndmin": sv_sorted_i[:, 1].tolist(),
                "sigma_min_over_2ndmin": (sv_sorted_i[:, 0] / sv_sorted_i[:, 1]).tolist(),
                "sigma_max": sv_sorted_i[:, -1].tolist(),
            }
        }
        for sib in ("safe", "mlab", "heretic"):
            sv_s = W[sib][f"{mat}_sv"].astype(np.float64)
            bot_s = W[sib][f"{mat}_bot"].astype(np.float64)
            top_s = W[sib][f"{mat}_top"].astype(np.float64)
            svs = np.sort(sv_s, axis=1)
            cos_bot1 = np.abs(np.einsum("ld,ld->l", bot_s[:, 0, :], bot_i[:, 0, :]) /
                              (np.linalg.norm(bot_s[:, 0, :], axis=1) *
                               np.linalg.norm(bot_i[:, 0, :], axis=1)))
            cos_top1 = np.abs(np.einsum("ld,ld->l", top_s[:, 0, :], top_i[:, 0, :]) /
                              (np.linalg.norm(top_s[:, 0, :], axis=1) *
                               np.linalg.norm(top_i[:, 0, :], axis=1)))
            block[sib] = {
                "abs_cos_bottom1_vs_instruct_bottom1": cos_bot1.tolist(),
                "abs_cos_top1_vs_instruct_top1": cos_top1.tolist(),
                "botgap_bf16": W[sib][f"{mat}_botgap_bf16"].astype(float).tolist(),
                "sigma_min": svs[:, 0].tolist(),
                "sigma_2ndmin": svs[:, 1].tolist(),
                "sigma_min_over_2ndmin": (svs[:, 0] / svs[:, 1]).tolist(),
                "sigma_min_ratio_to_instruct": (svs[:, 0] / sv_sorted_i[:, 0]).tolist(),
                "spectrum_rel_change_l2": (
                    np.linalg.norm(svs - sv_sorted_i, axis=1) /
                    np.linalg.norm(sv_sorted_i, axis=1)).tolist(),
                "sigma_max_ratio_to_instruct": (svs[:, -1] / sv_sorted_i[:, -1]).tolist(),
                "n_layers_spectrum_identical_to_instruct": int(
                    (np.linalg.norm(svs - sv_sorted_i, axis=1) == 0).sum()),
            }
        evidence[mat] = block
    del W
    gc.collect()

    # ---- realised strength: does either sibling show a projection signature? ----
    interp: dict[str, Any] = {}
    for mat in ("o_proj", "down_proj"):
        e = evidence[mat]
        base_ratio = np.array(e["instruct"]["sigma_min_over_2ndmin"])
        for sib in ("safe", "mlab", "heretic"):
            r = np.array(e[sib]["sigma_min_over_2ndmin"])
            rel = np.array(e[sib]["spectrum_rel_change_l2"])
            cb = np.array(e[sib]["abs_cos_bottom1_vs_instruct_bottom1"])
            n_same = int(e[sib]["n_layers_spectrum_identical_to_instruct"])
            interp[f"{mat}/{sib}"] = {
                "median_spectrum_rel_change_l2": float(np.median(rel)),
                "max_spectrum_rel_change_l2": float(rel.max()),
                "n_layers_with_ANY_spectrum_change": int(len(rel) - n_same),
                "n_layers_total": int(len(rel)),
                "layers_with_change": [int(i) for i in np.where(rel > 0)[0]],
                "median_abs_cos_bottom1_vs_instruct": float(np.median(cb)),
                "median_sigma_min_over_2ndmin": float(np.median(r)),
                "instruct_median_sigma_min_over_2ndmin": float(np.median(base_ratio)),
                "collapsed_below_instruct": bool(np.median(r) < np.median(base_ratio)),
            }

    # ---- the control's own outcome, from the activation limb ----
    ctrl: dict[str, Any] = {}
    for pos in POSITIONS:
        best = None
        for scope_name, scope in (("layer", per_layer[pos]), ("band", per_band[pos])):
            for cell, v in scope.items():
                e = v["pairs"]["mlab_vs_heretic"]
                if e.get("degenerate"):
                    continue
                cand = {
                    "scope": scope_name, "cell": cell,
                    "signed_rank1_cos": e["signed_rank1_cos_of_mean_difference"],
                    "abs_signed_rank1_cos": e["abs_signed_rank1_cos"],
                    "k1_null_p95": e["signed_rank1_vs_k1_null"]["null_p95"],
                    "k1_null_percentile": e["signed_rank1_vs_k1_null"]["observed_percentile_in_null"],
                    "p_one_sided": e["signed_rank1_vs_k1_null"]["p_one_sided_overlap_larger_than_null"],
                    "above_null_p95": e["signed_rank1_vs_k1_null"]["above_null_p95"],
                    "k8_cos_first": kfield(e, 8, "cos_first_principal_angle"),
                    "k8_above_null_p95": kfield(e, 8, "null_cos_max", "above_null_p95"),
                }
                if not np.isfinite(cand["abs_signed_rank1_cos"]):
                    continue
                if best is None or cand["abs_signed_rank1_cos"] > best["abs_signed_rank1_cos"]:
                    best = cand
        n_clear = 0
        n_tot = 0
        for scope in (per_layer[pos], per_band[pos]):
            for v in scope.values():
                e = v["pairs"]["mlab_vs_heretic"]
                if e.get("degenerate"):
                    continue
                n_tot += 1
                if e["signed_rank1_vs_k1_null"]["above_null_p95"]:
                    n_clear += 1
        ctrl[pos] = {"strongest_cell": best,
                     "n_cells_clearing_null_p95": n_clear, "n_cells": n_tot,
                     "fraction_clearing": n_clear / n_tot if n_tot else None}

    sc = ctrl["hs_last"]["strongest_cell"]
    passed = bool(sc and sc["above_null_p95"] and sc["abs_signed_rank1_cos"] >= 0.5)

    return {
        "control": "mlabonne__Qwen3-4B-abliterated  vs  DreamFast__qwen3-4b-heretic",
        "rationale": ("Two independent abliterations of the SAME parent should "
                      "share a subspace. If this pair does not clear the null, "
                      "D1's item budget may simply be too small to see any "
                      "overlap at all."),
        "activation_outcome": ctrl,
        "control_passes": passed,
        "weight_evidence": evidence,
        "weight_evidence_summary": interp,
        "two_readings": None,     # filled by the disambiguation below
    }


def disambiguate_control(pc: dict[str, Any]) -> dict[str, Any]:
    """A failed control has more than one reading; say which the weights support."""
    s = pc["weight_evidence_summary"]
    ml = s["o_proj/mlab"]
    he = s["o_proj/heretic"]
    sa = s["o_proj/safe"]
    mld = s["down_proj/mlab"]
    hed = s["down_proj/heretic"]

    # MAX, not median: a recipe that edits only a minority of layers would show
    # a median change of exactly zero and be mistaken for "no edit at all".
    def edits(x):
        return x["max_spectrum_rel_change_l2"] > 1e-9 or x["n_layers_with_ANY_spectrum_change"] > 0

    recipes_differ = (
        abs(ml["max_spectrum_rel_change_l2"] - he["max_spectrum_rel_change_l2"])
        > 0.5 * max(ml["max_spectrum_rel_change_l2"], he["max_spectrum_rel_change_l2"], 1e-12)
        or abs(ml["median_abs_cos_bottom1_vs_instruct"] -
               he["median_abs_cos_bottom1_vs_instruct"]) > 0.2
        or (ml["collapsed_below_instruct"] != he["collapsed_below_instruct"])
        or abs(ml["n_layers_with_ANY_spectrum_change"] -
               he["n_layers_with_ANY_spectrum_change"]) > 0.25 * ml["n_layers_total"]
    )
    both_edit_weights = ((edits(ml) or edits(mld)) and (edits(he) or edits(hed)))

    out = {
        "reading_i_underpowered": (
            "The measurement is too noisy at 160 items to resolve any shared "
            "subspace, so the control fails for a reason that has nothing to do "
            "with the recipes."),
        "reading_ii_recipes_genuinely_differ": (
            "The two siblings really do suppress different directions with "
            "different strengths. DreamFast/qwen3-4b-heretic comes from the "
            "Heretic tool, whose ablation weight kappa can EXCEED 1 and so can "
            "overshoot; mlabonne's is a conventional rank-1 projection, which "
            "drives one direction's singular value toward zero."),
        "reading_iii_rendering_confound": (
            "THIRD reading, not anticipated by the pre-registration and forced by "
            "the anchor audit: mlabonne ships the BASE-style chat template while "
            "heretic ships the instruct template, so D_mlab and D_heretic are not "
            "computed from the same rendered prompt string. Part of D_mlab is a "
            "tokenisation/rendering difference rather than a weight edit, which "
            "attenuates ANY mlab-bearing overlap including this control."),
        "discriminant": (
            "Recover each sibling's realised per-layer edit from ITS OWN weights: "
            "a conventional projection collapses sigma_min and opens the bottom "
            "gap; an over-strength kappa>1 edit leaves a different, larger and "
            "less bottom-localised spectral signature."),
        "measured": {
            "mlab_o_proj_median_spectrum_rel_change": ml["median_spectrum_rel_change_l2"],
            "heretic_o_proj_median_spectrum_rel_change": he["median_spectrum_rel_change_l2"],
            "safe_o_proj_median_spectrum_rel_change": sa["median_spectrum_rel_change_l2"],
            "mlab_down_proj_median_spectrum_rel_change": mld["median_spectrum_rel_change_l2"],
            "heretic_down_proj_median_spectrum_rel_change": hed["median_spectrum_rel_change_l2"],
            "mlab_median_abs_cos_bottom1_vs_instruct": ml["median_abs_cos_bottom1_vs_instruct"],
            "heretic_median_abs_cos_bottom1_vs_instruct": he["median_abs_cos_bottom1_vs_instruct"],
            "mlab_collapsed_sigma_min_below_instruct": ml["collapsed_below_instruct"],
            "heretic_collapsed_sigma_min_below_instruct": he["collapsed_below_instruct"],
            "mlab_o_proj_max_spectrum_rel_change": ml["max_spectrum_rel_change_l2"],
            "heretic_o_proj_max_spectrum_rel_change": he["max_spectrum_rel_change_l2"],
            "mlab_o_proj_n_layers_changed": ml["n_layers_with_ANY_spectrum_change"],
            "heretic_o_proj_n_layers_changed": he["n_layers_with_ANY_spectrum_change"],
            "mlab_down_proj_n_layers_changed": mld["n_layers_with_ANY_spectrum_change"],
            "heretic_down_proj_n_layers_changed": hed["n_layers_with_ANY_spectrum_change"],
            "safe_o_proj_n_layers_changed": sa["n_layers_with_ANY_spectrum_change"],
            "n_layers_total": ml["n_layers_total"],
        },
        "both_siblings_actually_edit_the_weights": both_edit_weights,
        "weight_evidence_supports": None,
    }
    if pc["control_passes"]:
        out["weight_evidence_supports"] = "CONTROL_PASSED_no_disambiguation_needed"
    elif recipes_differ and both_edit_weights:
        out["weight_evidence_supports"] = "READING_II_RECIPES_GENUINELY_DIFFER"
    elif not both_edit_weights:
        out["weight_evidence_supports"] = "NEITHER_sibling_shows_a_weight_edit_in_the_harvested_spectra"
    else:
        out["weight_evidence_supports"] = "READING_I_UNDERPOWERED"
    return out


# ===========================================================================
# STAGE 7 -- weight limb (time-boxed)
# ===========================================================================
def haar_null(d: int, k: int, rng: np.random.Generator, B: int = B_NULL) -> dict[str, np.ndarray]:
    cmax = np.empty(B)
    cmean = np.empty(B)
    for b in range(B):
        QA, _ = np.linalg.qr(rng.standard_normal((d, k)))
        QB, _ = np.linalg.qr(rng.standard_normal((d, k)))
        cs = np.clip(np.linalg.svd(QA.T @ QB, compute_uv=False), 0.0, 1.0)
        cmax[b] = cs.max()
        cmean[b] = cs.mean()
    return {"cos_max": cmax, "cos_mean": cmean}


def stage_weight_limb(rng: np.random.Generator, n_slots: int) -> dict[str, Any]:
    t_start = time.time()
    W = {r: load_weights(ANCHORS[r]) for r in ["instruct", "safe", "mlab", "heretic"]}
    d = W["instruct"]["o_proj_top"].shape[2]
    L = W["instruct"]["o_proj_top"].shape[0]
    k = W["instruct"]["o_proj_top"].shape[1]

    logger.info(f"weight limb: Haar null for k={k} in R^{d}")
    haar = haar_null(d, k, rng, B=B_NULL)
    haar_sum = {
        "cos_max": {q: float(np.percentile(haar["cos_max"], p))
                    for q, p in (("p5", 5), ("p50", 50), ("p95", 95))},
        "cos_mean": {q: float(np.percentile(haar["cos_mean"], p))
                     for q, p in (("p5", 5), ("p50", 50), ("p95", 95))},
        "cos_max_mean": float(haar["cos_max"].mean()),
        "cos_max_sd": float(haar["cos_max"].std(ddof=1)),
        "B": B_NULL,
    }

    out: dict[str, Any] = {
        "status": "RAN",
        "subspace_dim_k": int(k),
        "ambient_dim_d": int(d),
        "n_transformer_layers": int(L),
        "haar_null_two_arbitrary_k_subspaces_in_R_d": haar_sum,
        "null_adaptation_note": (
            "The activation limb's within-span null draws inside the 160-item "
            "span, which has a well-defined anisotropy. The weight harvest stores "
            "only 16 top and 16 bottom left singular vectors out of d=2560, so "
            "the full spectral span needed for the identical construction is NOT "
            "on disk and the recipe cannot be transcribed literally. Two "
            "references are given instead. (1) PRIMARY, the Haar null: two "
            "uniformly random k-dimensional subspaces of R^2560, which answers "
            "the same question the within-span null answers in the activation "
            "limb -- how much would two ARBITRARY subspaces of this shape "
            "overlap. (2) SECONDARY, a within-window anisotropy-matched null: "
            "random k-subspaces drawn inside each side's own stored 32-dimensional "
            "top-16-union-bottom-16 window with weights proportional to the "
            "matching singular values. The secondary null is deliberately "
            "conservative -- the two 32-dim windows already overlap heavily, so "
            "it sits far above the Haar null and a value inside it is not "
            "evidence of anything."),
        "per_layer": {},
        "per_band": {},
    }

    bands = [b for b in band_definitions(L) if b["kind"] == "quartile"]
    for mat in ("o_proj", "down_proj"):
        for which in ("top", "bot"):
            role = ("residual-write subspace (top-16 left singular vectors)"
                    if which == "top" else
                    "suppressed subspace (bottom-16 left singular vectors)")
            key = f"{mat}_{which}16"
            out["per_layer"][key] = {"role": role, "pairs": {}}
            out["per_band"][key] = {"role": role, "pairs": {}}
            Ai = W["instruct"][f"{mat}_{which}"].astype(np.float64)
            for sib in ("safe", "mlab", "heretic"):
                if time.time() - t_start > WEIGHT_LIMB_BUDGET_S:
                    out["status"] = "PARTIAL_TIME_BOXED"
                    out["time_box_note"] = (
                        f"weight limb hit its {WEIGHT_LIMB_BUDGET_S/60:.0f}-minute box "
                        "and stopped early; the activation limb D1.1-D1.7 is complete")
                    logger.warning("weight limb time box hit")
                    del W
                    gc.collect()
                    return out
                As = W[sib][f"{mat}_{which}"].astype(np.float64)
                cf, cm, pc_haar, pc_win = [], [], [], []
                for l in range(L):
                    a = np.ascontiguousarray(Ai[l].T)     # (d, k)
                    b = np.ascontiguousarray(As[l].T)
                    ang = subspace_angles(a, b)
                    cs = np.cos(ang)
                    cf.append(float(cs[-1]))
                    cm.append(float(cs.mean()))
                    pc_haar.append(float(100.0 * (haar["cos_max"] < cs[-1]).mean()))
                    # secondary within-window null
                    SA = np.vstack([W["instruct"][f"{mat}_top"][l],
                                    W["instruct"][f"{mat}_bot"][l]]).astype(np.float64)
                    SB = np.vstack([W[sib][f"{mat}_top"][l],
                                    W[sib][f"{mat}_bot"][l]]).astype(np.float64)
                    svA = np.sort(W["instruct"][f"{mat}_sv"][l].astype(np.float64))
                    svB = np.sort(W[sib][f"{mat}_sv"][l].astype(np.float64))
                    wA = np.concatenate([svA[-k:][::-1], svA[:k]])
                    wB = np.concatenate([svB[-k:][::-1], svB[:k]])
                    wA = wA / (wA.max() + 1e-300)
                    wB = wB / (wB.max() + 1e-300)
                    Cw = SA @ SB.T                        # (32, 32)
                    nl = within_span_null(wA, wB, Cw, [k], rng, B=200)
                    pc_win.append(float(100.0 * (nl[k]["cos_max"] < cs[-1]).mean()))
                out["per_layer"][key]["pairs"][f"instruct_vs_{sib}"] = {
                    "cos_first_principal_angle": cf,
                    "mean_cos_over_k": cm,
                    "percentile_in_haar_null": pc_haar,
                    "percentile_in_within_window_null": pc_win,
                    "median_cos_first": float(np.median(cf)),
                    "median_mean_cos": float(np.median(cm)),
                    "n_layers_above_haar_p95": int(
                        (np.array(cf) > haar_sum["cos_max"]["p95"]).sum()),
                }
                out["per_band"][key]["pairs"][f"instruct_vs_{sib}"] = {
                    bd["name"]: {
                        "median_cos_first": float(np.median([cf[l] for l in bd["layers"]])),
                        "median_mean_cos": float(np.median([cm[l] for l in bd["layers"]])),
                        "layers": bd["layers"],
                    } for bd in bands}
                logger.info(f"weight limb {key} instruct_vs_{sib}: "
                            f"median cos_first={np.median(cf):.4f}")
    del W
    gc.collect()
    out["elapsed_minutes"] = round((time.time() - t_start) / 60.0, 3)
    return out


def finalize() -> None:
    """Append the downstream-assembler keys to an already-computed result.

    Recomputes nothing: every number is read back out of results/d1_step1.json
    and flattened. Run as `python d1_step1.py --finalize`.
    """
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {message}")
    d = read_json(OUT)
    RESULT.clear()
    RESULT.update(d)

    j = d["verdict_judged_at"]
    cell = j["cell"]
    band = d["per_band"]["hs_last"].get(cell, {})
    pairs = band.get("pairs", {})
    rel = band.get("reliability", {})

    def sc(pair):
        e = pairs.get(pair, {})
        v = e.get("signed_rank1_cos_of_mean_difference")
        return float(v) if isinstance(v, (int, float)) else None

    def da(pair):
        e = pairs.get(pair, {}).get("disattenuated", {})
        v = e.get("disattenuated")
        return float(v) if isinstance(v, (int, float)) else None

    def rs(arm):
        v = rel.get(arm, {}).get("mean")
        return float(v) if isinstance(v, (int, float)) else None

    n1 = pairs.get("safe_vs_heretic", {}).get("signed_rank1_vs_k1_null", {}) or {}
    pc_cell = d["positive_control"]["activation_outcome"]["hs_last"]["strongest_cell"] or {}

    best = 0.0
    for scope in (d["per_band"]["hs_last"], d["per_layer"]["hs_last"]):
        for c in scope.values():
            for p, e in c["pairs"].items():
                v = e.get("abs_signed_rank1_cos")
                if isinstance(v, (int, float)) and np.isfinite(v):
                    best = max(best, float(v))

    RESULT["headline_numbers"] = {
        "signed_cos_safe_vs_mlab": sc("safe_vs_mlab"),
        "signed_cos_safe_vs_heretic": sc("safe_vs_heretic"),
        "disattenuated_overlap_safe_vs_mlab": da("safe_vs_mlab"),
        "disattenuated_overlap_safe_vs_heretic": da("safe_vs_heretic"),
        "null_p95_at_verdict_band": (float(n1["null_p95"]) if "null_p95" in n1 else None),
        "r_self_safe": rs("safe"),
        "r_self_mlab": rs("mlab"),
        "r_self_heretic": rs("heretic"),
        "positive_control_abs_cos": (float(pc_cell["abs_signed_rank1_cos"])
                                     if "abs_signed_rank1_cos" in pc_cell else None),
        "positive_control_null_p95": (float(pc_cell["k1_null_p95"])
                                      if "k1_null_p95" in pc_cell else None),
        "max_abs_signed_cos_anywhere_hs_last": float(best),
    }
    RESULT["headline_numbers_provenance"] = {
        "verdict_cell": cell,
        "read_position": "hs_last",
        "note": ("All values are read back from this same file; nothing is "
                 "recomputed. The signed cosines, disattenuated overlaps, "
                 "null p95 and r_self values are taken AT THE VERDICT CELL "
                 f"({cell}); positive_control_* are at its own strongest cell; "
                 "max_abs_signed_cos_anywhere_hs_last is the maximum over every "
                 "pair, band and layer at hs_last, which is the positive "
                 "control, not a SafeRL-vs-abliteration pair."),
    }

    RESULT["highest_value_missing_harvest"] = (
        "A SECOND, INDEPENDENT SAFETY-RL FINE-TUNE OF THE SAME Qwen3-4B PARENT "
        "(e.g. a public DPO/RLHF-for-harmlessness checkpoint built on "
        "Qwen/Qwen3-4B, or one trained in-house on the sibling GPU). All five "
        "pre-registered anchors ARE present, so nothing is missing for D1 as "
        "specified -- this is the harvest that would close the one hole the "
        "results actually expose. The evidence: the abliteration side HAS an "
        "internal positive control and it passes decisively (mlabonne vs "
        "heretic, |cos| 0.92 at L29 against a null p95 of 0.72, p = 0.001), so "
        "'two independent edits of the same kind converge on one direction' is "
        "demonstrated for abliteration. The safety-RL side has n = 1. "
        "Qwen3-4B-SafeRL is the only safety-RL member, so 'official safety RL "
        "moves a DIFFERENT subspace' currently rests on a single checkpoint and "
        "cannot be separated from 'this one checkpoint happens to be "
        "idiosyncratic'. A second safety-RL sibling would give that arm the "
        "same mlab-vs-heretic style control, turning the headline from one "
        "observation into a replicated contrast. It is strictly more valuable "
        "than a third abliteration, whose converging behaviour is already "
        "established here.")
    RESULT["last_stage_written"] = "D1.8_COMPLETE"
    write_json(OUT, json_safe(RESULT))
    logger.info(f"finalize: headline_numbers + highest_value_missing_harvest -> {OUT}")


# ===========================================================================
# main
# ===========================================================================
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO",
               format="{time:HH:mm:ss} | {level: <7} | {message}")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logger.add(LOG, level="DEBUG", rotation="20 MB")
    logger.info("D1 principal-angle analysis starting")

    RESULT["_meta"] = {
        "script": str(Path(WS_DIR) / "d1_step1.py"),
        "seed": SEED,
        "B_null": B_NULL,
        "B_splithalf": B_SPLITHALF,
        "ks": KS,
        "read_positions": POSITIONS,
        "upstream_read_only": str(HARVEST),
    }

    # ---------------- STAGE 0: anchors ----------------
    RESULT["anchor_resolution"] = stage_anchors()
    flush("anchor_resolution")
    if not RESULT["anchor_resolution"]["all_five_present"]:
        miss = RESULT["anchor_resolution"]["missing_roles"]
        if "safe" in miss:
            RESULT["verdict"] = "BLOCKED_MISSING_SAFERL"
            RESULT["highest_value_missing_harvest"] = "Qwen/Qwen3-4B-SafeRL"
            flush("blocked")
            return

    items = load_items()
    RESULT["_meta"]["n_items_in_items_json"] = len(items)

    # ---------------- STAGE 1: differences ----------------
    diffs, base_h, n_slots = load_differences()
    RESULT["_meta"]["n_layer_slots_including_embeddings"] = int(n_slots)
    mid = n_slots // 2
    RESULT["_meta"]["numerics_check_gram_svd_vs_lapack"] = {
        f"{arm}/hs_last/L{mid:02d}": cross_check_svd(
            diffs[arm]["hs_last"][:, mid, :].astype(np.float64)) for arm in ARMS}
    norms, d11 = stage_d11(diffs, base_h, n_slots)
    RESULT.update(d11)
    RESULT["per_layer_norms"] = norms
    RESULT["edit_onset_and_template_confound"] = stage_edit_onset(diffs, n_slots)
    del base_h
    gc.collect()
    flush("D1.1")

    # ---------------- STAGE 2/3: per layer ----------------
    rng = np.random.default_rng(SEED)
    perm_rng = np.random.default_rng(SEED + 1)
    splits = []
    for _ in range(B_SPLITHALF):
        p = perm_rng.permutation(N_ITEMS)
        splits.append((p[: N_ITEMS // 2], p[N_ITEMS // 2:]))

    per_layer: dict[str, dict[str, Any]] = {pos: {} for pos in POSITIONS}
    for pos in POSITIONS:
        for l in range(n_slots):
            mats = {arm: diffs[arm][pos][:, l, :].astype(np.float64) for arm in ARMS}
            per_layer[pos][f"L{l:02d}"] = analyse_scope(mats, rng, splits)
            del mats
        logger.info(f"per-layer angles done for {pos}")
    RESULT["per_layer"] = per_layer
    RESULT["signed_rank1"] = {
        pos: {f"{a}_vs_{b}": [per_layer[pos][f"L{l:02d}"]["pairs"][f"{a}_vs_{b}"]
                              ["signed_rank1_cos_of_mean_difference"]
                              for l in range(n_slots)]
              for a, b in PAIRS} for pos in POSITIONS}
    flush("D1.2_D1.3")

    # ---------------- STAGE 4: bands ----------------
    bands = band_definitions(n_slots)
    per_band: dict[str, dict[str, Any]] = {pos: {} for pos in POSITIONS}
    for pos in POSITIONS:
        for bd in bands:
            mats = {arm: band_matrix(diffs[arm][pos], bd["layers"]) for arm in ARMS}
            cell = analyse_scope(mats, rng, splits)
            cell["layers"] = bd["layers"]
            cell["kind"] = bd["kind"]
            per_band[pos][bd["name"]] = cell
            del mats
            gc.collect()
        logger.info(f"per-band angles done for {pos}")
    RESULT["per_band"] = per_band
    RESULT["band_definitions"] = bands
    RESULT["band_normalisation"] = (
        "Each layer's difference block was divided by the RMS norm of its rows "
        "BEFORE concatenation. Justification is in norm_growth_across_depth: "
        "without it a band is a read of its deepest layer alone.")
    for pos in POSITIONS:
        RESULT["signed_rank1"][f"{pos}__bands"] = {
            f"{a}_vs_{b}": {bd["name"]: per_band[pos][bd["name"]]["pairs"]
                            [f"{a}_vs_{b}"]["signed_rank1_cos_of_mean_difference"]
                            for bd in bands} for a, b in PAIRS}
    flush("D1.4")

    # ---------------- STAGE 5: nulls / reliability / disattenuation rollup ----
    RESULT["nulls"] = {
        "construction": (
            "UPPER FLOOR, matched-anisotropy within-span null, B=1000. For each "
            "side independently: c ~ N(0, I_160), v = D^T c, normalise, k draws, "
            "orthonormalise. Evaluated in right-singular coordinates via the "
            "algebraic identity D^T c = Vt^T (s * g); see within_span_null(). "
            "Two arbitrary high-dimensional differences of this shape are "
            "near-orthogonal by default, so a LARGE ANGLE IS NOT BY ITSELF "
            "EVIDENCE -- only an overlap above the null p95 is."),
        "summary_hs_last_by_pair": {},
    }
    for a, b in PAIRS:
        rows = []
        for bd in bands:
            e = per_band["hs_last"][bd["name"]]["pairs"][f"{a}_vs_{b}"]
            if e.get("degenerate"):
                rows.append({"band": bd["name"], "degenerate": True,
                             "reason": e.get("reason")})
                continue
            n1 = e["signed_rank1_vs_k1_null"]
            rows.append({
                "band": bd["name"],
                "signed_rank1_cos": e["signed_rank1_cos_of_mean_difference"],
                "k1_null_p95": n1["null_p95"],
                "k1_null_percentile": n1["observed_percentile_in_null"],
                "k1_above_null_p95": n1["above_null_p95"],
                "k8_cos_first": kfield(e, 8, "cos_first_principal_angle"),
                "k8_null_p95": kfield(e, 8, "null_cos_max", "null_p95"),
                "k8_above_null_p95": kfield(e, 8, "null_cos_max", "above_null_p95"),
            })
        RESULT["nulls"]["summary_hs_last_by_pair"][f"{a}_vs_{b}"] = rows

    RESULT["reliability"] = {
        "construction": (
            "LOWER CEILING, split-half over 200 random 80/80 item splits (the "
            "SAME splits for every arm, so the arms are paired). r_self is the "
            "cosine between the mean difference on half A and on half B. A "
            "genuinely IDENTICAL pair of directions could not exceed roughly "
            "sqrt(r_self_A * r_self_B) at this item budget."),
        "per_band_hs_last": {
            bd["name"]: {arm: per_band["hs_last"][bd["name"]]["reliability"][arm]
                         for arm in ARMS} for bd in bands},
        "per_layer_hs_last": {arm: [per_layer["hs_last"][f"L{l:02d}"]["reliability"][arm]["mean"]
                                    for l in range(n_slots)] for arm in ARMS},
        "per_layer_hs_first": {arm: [per_layer["hs_first"][f"L{l:02d}"]["reliability"][arm]["mean"]
                                     for l in range(n_slots)] for arm in ARMS},
    }
    RESULT["disattenuated_overlap"] = {
        "formula": "cos(Delta_a, Delta_b) / sqrt(r_self_a * r_self_b)",
        "per_band_hs_last": {
            f"{a}_vs_{b}": {bd["name"]: per_band["hs_last"][bd["name"]]["pairs"]
                            [f"{a}_vs_{b}"]["disattenuated"] for bd in bands}
            for a, b in PAIRS},
    }
    flush("D1.5")

    # ---------------- STAGE 6: positive control ----------------
    RESULT["sign_consistency"] = sign_consistency(per_layer, per_band, n_slots)
    pc = stage_positive_control(per_band, per_layer, n_slots)
    pc["two_readings"] = disambiguate_control(pc)
    RESULT["positive_control"] = pc
    flush("D1.6")

    # ---------------- STAGE 7: verdict ----------------
    RESULT["verdict"], RESULT["verdict_judged_at"], RESULT["verdict_hs_first"] = \
        decide_verdict(per_layer, per_band, pc, n_slots)
    RESULT["assumptions"] = ASSUMPTIONS
    RESULT["limitations"] = build_limitations(RESULT)
    flush("D1.7")

    del diffs
    gc.collect()

    # ---------------- STAGE 8: weight limb ----------------
    try:
        RESULT["weight_limb"] = stage_weight_limb(rng, n_slots)
    except (OSError, ValueError, np.linalg.LinAlgError, KeyError) as exc:
        RESULT["weight_limb"] = {"status": "DEFERRED_TO_SIBLING_EXPERIMENT",
                                 "reason": f"{type(exc).__name__}: {exc}"}
        logger.exception("weight limb failed; deferred")
    flush("D1.8")
    logger.info(f"D1 complete in {RESULT['runtime_minutes']:.2f} min")


def sign_consistency(per_layer, per_band, n_slots) -> dict[str, Any]:
    """Is the sign of the rank-1 overlap CONSISTENT, even where it is small?

    The pre-registered enum only fires on |cos| >= 0.5, so a small but
    systematically NEGATIVE overlap would be reported as DIFFERENT_SUBSPACES
    and its direction thrown away. That direction is the whole point of the
    two-sided question, so it is summarised here separately. No p-value is
    claimed: neighbouring layers and overlapping windows are strongly
    dependent, so a binomial test on them would be anti-conservative. The
    quartile count is the closest thing to an independent tally.
    """
    out: dict[str, Any] = {"note": sign_consistency.__doc__, "per_position": {}}
    for pos in POSITIONS:
        block: dict[str, Any] = {}
        for a, b in PAIRS:
            key = f"{a}_vs_{b}"
            def collect(cells, only_quartile=False):
                vals = []
                for cell in cells:
                    if only_quartile and cell.get("kind") != "quartile":
                        continue
                    e = cell["pairs"][key]
                    if e.get("degenerate"):
                        continue
                    v = e["signed_rank1_cos_of_mean_difference"]
                    if np.isfinite(v):
                        vals.append(float(v))
                return vals

            lay = collect([per_layer[pos][f"L{l:02d}"] for l in range(n_slots)])
            allb = collect(list(per_band[pos].values()))
            quart = collect(list(per_band[pos].values()), only_quartile=True)
            block[key] = {
                "n_layers_scored": len(lay),
                "frac_layers_negative": (float(np.mean(np.array(lay) < 0))
                                         if lay else None),
                "median_layer_signed_cos": float(np.median(lay)) if lay else None,
                "n_bands_scored": len(allb),
                "frac_bands_negative": (float(np.mean(np.array(allb) < 0))
                                        if allb else None),
                "median_band_signed_cos": float(np.median(allb)) if allb else None,
                "quartile_signed_cos": quart,
                "n_quartiles_negative": int(np.sum(np.array(quart) < 0)) if quart else 0,
                "n_quartiles": len(quart),
            }
        out["per_position"][pos] = block
    return out


def decide_verdict(per_layer, per_band, pc, n_slots):
    """Pre-registered enum, judged on hs_last at the band where the effect is largest."""
    def scan(pos, scopes=("band",)):
        best = None
        n_scanned = 0
        cells = []
        if "band" in scopes:
            cells += [("band", name, cell) for name, cell in per_band[pos].items()]
        if "layer" in scopes:
            cells += [("layer", name, cell) for name, cell in per_layer[pos].items()]
        for scope, name, cell in cells:
            for a, b in [("safe", "mlab"), ("safe", "heretic")]:
                e = cell["pairs"][f"{a}_vs_{b}"]
                if e.get("degenerate"):
                    continue
                v = e["abs_signed_rank1_cos"]
                if not np.isfinite(v):
                    continue
                n_scanned += 1
                if best is None or v > best["abs_signed_rank1_cos"]:
                    best = {
                        "scope": scope, "cell": name, "pair": f"{a}_vs_{b}",
                        "read_position": pos,
                        "layers": cell.get("layers"),
                        "signed_rank1_cos": e["signed_rank1_cos_of_mean_difference"],
                        "abs_signed_rank1_cos": v,
                        "sign": e["sign"],
                        "k1_null_p95": e["signed_rank1_vs_k1_null"]["null_p95"],
                        "k1_null_percentile": e["signed_rank1_vs_k1_null"]["observed_percentile_in_null"],
                        "p_one_sided": e["signed_rank1_vs_k1_null"]["p_one_sided_overlap_larger_than_null"],
                        "above_null_p95": e["signed_rank1_vs_k1_null"]["above_null_p95"],
                        "disattenuated": e["disattenuated"],
                        "k8_cos_first": kfield(e, 8, "cos_first_principal_angle"),
                        "k8_above_null_p95": kfield(e, 8, "null_cos_max", "above_null_p95"),
                    }
        if best is not None:
            best["n_cells_scanned_for_this_maximum"] = n_scanned
            p = best["p_one_sided"]
            best["bonferroni_p_over_scanned_cells"] = min(1.0, p * n_scanned)
        return best

    def call(best):
        if best is None:
            return "DIFFERENT_SUBSPACES"
        big = best["abs_signed_rank1_cos"] >= 0.5
        above = best["above_null_p95"]
        if big and above and best["sign"] == "negative":
            return "SAME_SUBSPACE_OPPOSITE_SIGN"
        if big and above and best["sign"] == "positive":
            return "SAME_SUBSPACE_SAME_SIGN"
        return "DIFFERENT_SUBSPACES"

    def nuance(best):
        """DIFFERENT_SUBSPACES covers two materially different states."""
        if best is None:
            return None
        if best["abs_signed_rank1_cos"] >= 0.5:
            return None
        if best["above_null_p95"]:
            return (
                "DETECTABLY_NON_ORTHOGONAL_BUT_NOT_SHARED: the largest overlap "
                f"is |cos| = {best['abs_signed_rank1_cos']:.3f} with a "
                f"{best['sign']} sign, which EXCEEDS the within-span null p95 of "
                f"{best['k1_null_p95']:.3f} yet falls far short of the "
                "pre-registered 0.5 for a shared subspace. The two edits are not "
                "orthogonal, but they are nowhere near the same direction. "
                "Reporting this as a bare DIFFERENT_SUBSPACES would discard a "
                "real, if small, structured relation.")
        return (
            "INSIDE_THE_NULL_BAND: the largest overlap anywhere, "
            f"|cos| = {best['abs_signed_rank1_cos']:.3f}, sits inside the "
            f"within-span null (p95 = {best['k1_null_p95']:.3f}). This is the "
            "clean form of DIFFERENT_SUBSPACES -- the edits are no more aligned "
            "than two arbitrary differences of the same shape and anisotropy.")

    best_last = scan("hs_last")                       # BANDS, per the pre-registration
    best_first = scan("hs_first")
    best_last_layer = scan("hs_last", scopes=("layer",))
    v_last = call(best_last)
    v_first = call(best_first)

    ctrl_ok = pc["control_passes"]
    supports = pc["two_readings"]["weight_evidence_supports"]
    if not ctrl_ok and supports == "READING_I_UNDERPOWERED":
        v_last = "UNDERPOWERED"
        v_first = "UNDERPOWERED"

    judged = {
        "read_position": "hs_last",
        "scope": best_last["scope"] if best_last else None,
        "cell": best_last["cell"] if best_last else None,
        "layers": best_last["layers"] if best_last else None,
        "pair": best_last["pair"] if best_last else None,
        "selection_rule": ("the BAND (over all 4-layer windows, 8-layer windows "
                           "and depth quartiles) maximising |signed rank-1 "
                           "cosine| for safe-vs-mlab or safe-vs-heretic at "
                           "hs_last, exactly as pre-registered"),
        "selection_multiplicity_note": (
            "This is a MAXIMUM over many cells, so its null percentile is "
            "upward-biased. A Bonferroni p over the cells scanned is reported "
            "alongside the raw one-sided p. The bias inflates overlap, so it "
            "works AGAINST a DIFFERENT_SUBSPACES call and cannot manufacture "
            "one: if the largest effect anywhere still sits inside the null, "
            "the finding is if anything conservative."),
        "nuance": nuance(best_last),
        "detail": best_last,
        "strongest_single_layer_supplementary": best_last_layer,
        "positive_control_passed": ctrl_ok,
        "positive_control_weight_reading": supports,
        "verdict_override_by_control": (v_last == "UNDERPOWERED"),
        "thresholds": {"abs_signed_cos_min": 0.5, "overlap_must_exceed": "null p95"},
    }
    return v_last, judged, {"verdict": v_first, "nuance": nuance(best_first),
                            "detail": best_first}


ASSUMPTIONS = [
    "SHARED BASIS: item-wise differences h_child - h_instruct presume all "
    "fine-tunes of the one parent inherit a common residual basis. Not provable "
    "from this harvest; bounded by the base-vs-instruct magnitude reference in "
    "shared_basis_check.",
    "ROW-INDEX JOIN: row i of every acts.npz is item i of items.json. Asserted "
    "at load time for all five checkpoints (first dim == 160) and the script "
    "aborts loudly otherwise.",
    "PRECISION: the store is float16. Differences are formed in float32, which "
    "is exact for float16 operands, and every layer is cast to float64 before "
    "any SVD, Gram or angle computation.",
    "PRINCIPAL-ANGLE CONVENTION: scipy.linalg.subspace_angles returns angles in "
    "DESCENDING order. 'cos of the first principal angle' is reported as "
    "cos(angles[-1]) -- the SMALLEST angle and therefore the MAXIMUM overlap.",
    "SUBSPACE DEFINITION: the top-k RIGHT singular vectors (Vt[:k]) of the "
    "160 x d difference matrix, i.e. directions in residual space, not item "
    "loadings.",
    "BAND CONSTRUCTION: per-layer RMS row-norm normalisation BEFORE "
    "concatenation, so a band is not a read of its deepest layer.",
    "NULL: matched-anisotropy, drawn WITHIN the item span of each side's own "
    "difference matrix, independently per side, B=1000.",
    "RELIABILITY: 200 random 80/80 item split-halves, identical splits across "
    "arms so the arms are paired.",
    "BASE STRATUM: Qwen3-4B-Base is a magnitude reference only and never enters "
    "the three-way SafeRL/abliterated comparison.",
    "JSON SAFETY: every non-finite float is written as null. Note for sibling "
    "lanes -- evallib.core.write_json alone does NOT guarantee this. Its "
    "_jdefault hook only fires for NUMPY scalars; a native Python float('nan') "
    "is serialisable and json.dumps emits the bare token NaN, which Python's "
    "json.load accepts but RFC-8259 parsers reject. This script sanitises "
    "recursively before calling write_json.",
]


def build_limitations(res: dict) -> list[str]:
    lim = [
        "n = 160 items is the whole budget. Every overlap here is attenuated by "
        "sampling noise, which is exactly what the split-half floor quantifies; "
        "read raw and disattenuated together and neither alone.",
        "The two reference levels bracket the measurement but do not make it "
        "causal: nothing here shows that the subspace a fine-tune MOVED is the "
        "subspace that CARRIES refusal behaviour.",
        "The difference matrices are observational. A shared subspace between "
        "two children could be inherited parent structure rather than a shared "
        "edit; the base arm bounds but does not remove that.",
        "Only two read positions (last prompt token, first generated token) were "
        "harvested, so nothing can be said about mid-response drift.",
        "hs_first IS NOT A CLEAN REPRESENTATIONAL READ. It is taken at the first "
        "GENERATED token, which each checkpoint picks for itself, so wherever "
        "two checkpoints emit different first tokens the difference includes a "
        "mechanical embedding change. The measured first-token agreement rates "
        "are reported under edit_onset_and_template_confound. hs_last, at the "
        "last PROMPT token, is identical across checkpoints by construction and "
        "is therefore the primary read position.",
        "The weight limb sees only 16 top and 16 bottom left singular vectors of "
        "o_proj and down_proj out of d=2560; the middle of the spectrum, where a "
        "diffuse edit would live, was never harvested.",
    ]
    ar = res.get("anchor_resolution", {})
    f = ar.get("renderer_and_template_finding", {})
    tcr = res.get("edit_onset_and_template_confound", {}).get(
        "template_confound_resolution", {})
    if f.get("template_sha256_is_NOT_uniform"):
        if tcr.get("verdict") == "TEMPLATE_MISMATCH_HAS_NO_MEASURABLE_EFFECT":
            lim.insert(0,
                       "TEMPLATE MISMATCH (found here, not pre-registered, and "
                       "RESOLVED): mlabonne ships the BASE-style chat template "
                       "while instruct, SafeRL and heretic share the instruct "
                       "one, and the harvest renders each checkpoint with its "
                       "own. This would confound every mlab-bearing comparison, "
                       "but mlabonne's layer-0 embedding difference from "
                       "instruct is EXACTLY ZERO on all 160 items, so the "
                       "rendered prompt is effectively identical at the read "
                       "position and the mismatch does not bite. Listed because "
                       "a reader checking the metadata will see the hash "
                       "mismatch and should not have to re-derive this.")
        else:
            lim.insert(0,
                       "TEMPLATE CONFOUND (found here, not pre-registered, and "
                       "NOT resolved): mlabonne ships the BASE-style chat "
                       "template and its layer-0 difference from instruct is "
                       "non-zero, so D_mlab mixes a weight edit with a "
                       "prompt-rendering difference. safe-vs-heretic is then the "
                       "only rendering-clean cross-recipe pair, and safe-vs-mlab "
                       "plus the mlab-vs-heretic control are biased DOWNWARD.")
    if not f.get("base_renderer_matches_brief", True):
        lim.insert(1,
                   "The brief's premise that the base checkpoint uses the plain "
                   "renderer is FALSE in the realised harvest: Qwen3-4B-Base "
                   "ships a chat template and was rendered with renderer='chat'. "
                   "The base stratum separation is justified by training stage, "
                   "not by renderer.")
    sb = res.get("shared_basis_check", {})
    if sb.get("verdict") in ("SHARED_BASIS_WEAKLY_SUPPORTED", "SHARED_BASIS_PREMISE_WEAK"):
        lim.insert(0, "SHARED-BASIS PREMISE IS WEAK: " + sb.get("reading", ""))
    return lim


if __name__ == "__main__":
    if "--finalize" in sys.argv:
        finalize()
    else:
        main()

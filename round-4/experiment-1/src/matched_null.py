#!/usr/bin/env python3
"""matched_null.py -- EXPLORATORY, POST HOC robustness check of the direction null behind rule S2(b)
for candidates C1 and C2, reusing method.py's own measurement code path exactly (same base pass, same
cross-fitted direction fitting, same c1_block / c2_block). NOT pre-registered. It never enters PREREG's
S1-S6 selection rule; the only pre-registered C1/C2 null_p95 values are the ones written by method.py to
rows/<slug>.json. See matched_null.md.

BACKGROUND. In method.measure(), the direction null for C1 and C2 at B_mid (the production band, L_h +-1
at 50% depth) draws N_RAND=20 random directions per B_mid layer via M.aniso_random_dirs(A, h_l, N_RAND,
rng_c): A = the centred token-level residual matrix at that layer (massive-activation positions excluded),
v = A^T g accepted when var(A v) is within +/-25% of var(A h_l); otherwise the 'closest' fallback is used.
Per rows/*.json random_dirs, the picked directions' variance ratio var(Av)/var(Ah) has median ~2.89 (the
null typically carries ~3x the harm direction's own variance). This script asks how much of S2(b)'s failure
(C1 11/23, C2 7/23 exceeding p95) comes from that variance mismatch, by rebuilding a VARIANCE-MATCHED null
(var(A w) == var(A h_l) exactly, within 1e-3) and recomputing null_p95 with the identical c1_block/c2_block
code path -- changing only the directions fed in.

For each of the 23 graded repos (WS/labels_map.json 'rows' with non-null BALANCED), it:
  - loads the model exactly as measure() does (M.ModelRun(repo); .load());
  - builds the plain batch exactly as measure() does (M.NP=16 pairs, 32 items);
  - runs ONE base pass capturing R (all-layer last-token residuals) and the full-sequence hidden states
    at the 3 B_mid layers (for A) and at B_mid[0]-1 (the skip_call input layer j-1); KEEPS the KV cache
    (base["cache"]), because C1's c1_block.run() reuses it via ModelRun.last_call for every eps/null draw;
  - fits the cross-fitted harm directions once with method.cf_harm_dirs (same folds), D;
  - REPRODUCES the production null: same M.aniso_random_dirs, same rng_c seeded SEED+1 (C1) / SEED+2 (C2),
    same N_RAND=20 on cuda, then runs the SAME c1_block / c2_block that method.py's run_condition() calls
    for the production band, and checks the resulting null_p95 against rows/<slug>.json
    candidates.{C1,C2}.null_p95 (acceptance check, tol 1e-3);
  - draws a VARIANCE-MATCHED null per B_mid layer: v = A^T g / ||.|| (the production family) and an
    isotropic unit Gaussian u, orthogonalised to v (u' = u - (u.v)v, normalised); w(t) = cos(t) v + sin(t) u'
    has var(A w(t)) a quadratic form in (cos t, sin t) that is bisected over t in [0, pi/2] to hit
    var(A h_l) exactly (redrawing the (v, u) pair when no root exists in that range); seed
    20260921 + 100 + candidate-offset (C1: +1, C2: +2, matching measure()'s own offsets);
  - computes the matched-null null_p95 for C1 and C2 with the identical c1_block/c2_block code, only the
    null_dirs argument replaced;
  - unloads the model before the next one.

Usage:
    venv_gpu/bin/python matched_null.py [--repos a,b,...] [--force] [--limit N]

Run with env TORCH_DISABLE_NATIVE_JIT=1 (torch 2.14's native Triton DSL ops need a C toolchain this pod
lacks -- see method.py's own note).
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import os

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

import method as M  # noqa: E402 -- PREREG gate, prompts, FOLDS, ModelRun, cf_harm_dirs, aniso_random_dirs, ...
from live_lib import DEVICE, unit  # noqa: E402

WS = M.WS
LOGS = WS / "logs"
LOGS.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(LOGS / "matched_null.log", rotation="30 MB", level="DEBUG")

OUT_JSON = WS / "matched_null.json"
OUT_MD = WS / "matched_null.md"

ACCEPTANCE_TOL = 1e-3
RATIO_TOL = 1e-3
MATCH_SEED_BASE = 20260921 + 100  # task spec: 20260921 + 100 + candidate offset
CAND_OFFSET = {"C1": 1, "C2": 2}  # same offsets measure() uses for SEED + off
MAX_REDRAWS = 500
# BALANCED median over the 23 graded repos, computed from labels_map.json itself (task states ~0.608).
BALANCED_MEDIAN = float(np.median([v["BALANCED"] for v in M.LABELS.values() if v.get("BALANCED") is not None]))


# ----------------------------------------------------------------------------- repo list / ordering
def graded_repos() -> list[str]:
    return [r for r, v in M.LABELS.items() if v.get("BALANCED") is not None]


def default_repo_order() -> list[str]:
    repos = graded_repos()
    return sorted(repos, key=lambda r: (M.PANEL.get(r, {}).get("n_params") or 9e9))


# ----------------------------------------------------------------------------- variance-matched direction
def var_Av(A: np.ndarray, v: np.ndarray) -> float:
    """mean((A v)^2): A is already mean-centred (as aniso_random_dirs centres it), so this equals var(Av)."""
    return float(np.mean((A @ v) ** 2))


def matched_direction(A: np.ndarray, h: np.ndarray, tgt: float, rng: np.random.Generator,
                      max_redraws: int = MAX_REDRAWS) -> tuple[np.ndarray, dict]:
    """One variance-matched unit direction w with var(A w) == tgt (== var(A h)) within RATIO_TOL.

    v = A^T g / ||.|| (the production aniso_random_dirs family -- usually ABOVE target variance);
    u = isotropic unit Gaussian, u' = (u - (u.v) v) normalised (usually BELOW target variance, orthogonal
    to v). w(t) = cos(t) v + sin(t) u' is unit-norm for every t since {v, u'} is orthonormal, and
    var(A w(t)) = cos^2(t) var(Av) + sin^2(t) var(Au') + 2 sin(t) cos(t) mean(Av . Au') is continuous in t,
    so if var(Av) and var(Au') straddle tgt a root exists in [0, pi/2] and is found by bisection. If they
    do not straddle tgt (both directions land on the same side, which the task flags as possible), the
    (v, u) pair is redrawn."""
    d = A.shape[1]
    for attempt in range(max_redraws):
        g = rng.standard_normal(A.shape[0]).astype(np.float32)
        v = A.T @ g
        nv = np.linalg.norm(v)
        if nv < 1e-12:
            continue
        v = v / nv
        u = rng.standard_normal(d).astype(np.float32)
        u = u / max(np.linalg.norm(u), 1e-12)
        u_perp = u - float(u @ v) * v
        nu = np.linalg.norm(u_perp)
        if nu < 1e-8:
            continue  # u ~ parallel to v: redraw
        u_perp = u_perp / nu

        Av = A @ v
        Au = A @ u_perp
        a_c = float(np.mean(Av ** 2))
        a_s = float(np.mean(Au ** 2))
        a_cs = float(np.mean(Av * Au))

        def f(t: float) -> float:
            c, s = np.cos(t), np.sin(t)
            return a_c * c * c + a_s * s * s + 2 * a_cs * c * s - tgt

        f0, f1 = f(0.0), f(np.pi / 2)
        if f0 == 0.0:
            t_star = 0.0
        elif f1 == 0.0:
            t_star = np.pi / 2
        elif f0 * f1 > 0:
            continue  # no root in [0, pi/2] for this (v, u) pair: redraw
        else:
            lo, hi, flo = 0.0, np.pi / 2, f0
            for _ in range(100):
                mid = (lo + hi) / 2
                fm = f(mid)
                if flo * fm <= 0:
                    hi = mid
                else:
                    lo, flo = mid, fm
            t_star = (lo + hi) / 2

        w = np.cos(t_star) * v + np.sin(t_star) * u_perp
        w = w / max(np.linalg.norm(w), 1e-12)
        achieved = var_Av(A, w) / max(tgt, 1e-12)
        return w.astype(np.float32), {"attempts": attempt + 1, "t_star": float(t_star),
                                      "ratio_v": a_c / max(tgt, 1e-12), "ratio_u_perp": a_s / max(tgt, 1e-12),
                                      "achieved_ratio": float(achieved)}
    raise RuntimeError(f"matched_direction: no straddling (v,u) pair found in {max_redraws} redraws")


def build_A(base_full_l: torch.Tensor, mask: torch.Tensor, n_items: int) -> np.ndarray:
    """Exactly measure()'s A construction at one B_mid layer l (before aniso_random_dirs's own centring)."""
    Hf = base_full_l.float().detach().cpu().numpy()
    mnp = mask.detach().cpu().numpy().astype(bool)
    return M.massive_filter(np.concatenate([Hf[i, mnp[i]] for i in range(n_items)], 0))


# ----------------------------------------------------------------------------- one model
def run_one_repo(repo: str) -> dict:
    t0 = time.time()
    mr = M.ModelRun(repo)
    out: dict[str, Any] = {"repo": repo}
    try:
        mr.load()
        B_mid = list(mr.B_mid)
        j = B_mid[0]
        out["n_layers"] = mr.L
        out["L_h"] = mr.L_h
        out["B_mid"] = B_mid

        b = mr.batch("plain")
        b.item_idx = list(range(2 * M.NP))  # exactly what measure() does for B["plain"] before use

        full_layers = sorted(set(B_mid) | {j - 1})
        base = mr.base_pass(b, full_layers, want_attn=False)  # KEEP base["cache"]: C1's last_call needs it
        # base_pass's 2nd forward call (o2, over the last prompt token) mutates the KV cache in place from
        # length T-1 (after o1) to length T. In measure(), mr.generate() runs several more steps on this
        # same cache object and crops it back to T-1 at the end, which is the state ModelRun.last_call
        # (used by c1_block for every eps/null draw) asserts on. This script never calls generate() (no
        # C11 / 64-token generation needed here), so it performs the equivalent crop directly: this only
        # trims the cache's already-computed KV entries back to the T-1 they held right after o1, an
        # in-place slice with no randomness, identical to what generate()'s own final crop leaves behind.
        base["cache"].crop(b.T - 1)
        Rp = base["R"]
        h_in = base["full"][j - 1]

        allp = list(range(M.NP))
        D = M.cf_harm_dirs(Rp, allp, M.FOLDS)

        # ---- per-layer A (raw, exactly as measure() builds it -- aniso_random_dirs centres it itself) and
        # a separately-centred copy for the target-variance / matched-direction math below, which needs an
        # already-centred A (mirroring aniso_random_dirs's own `A = A - A.mean(0)` with the identical formula
        # so the two centrings are bit-identical). h_l = the all-item harm dir measure() passes as `h`.
        A_raw_by_l: dict[int, np.ndarray] = {}
        A_c_by_l: dict[int, np.ndarray] = {}
        h_by_l: dict[int, np.ndarray] = {}
        tgt_by_l: dict[int, float] = {}
        for l in B_mid:
            A_raw = build_A(base["full"][l], b.mask, 2 * M.NP).astype(np.float32)
            A_c = A_raw - A_raw.mean(0, keepdims=True)
            h_l = unit(Rp[M.HARM_IDX, l].mean(0) - Rp[M.TWIN_IDX, l].mean(0)).astype(np.float32)
            A_raw_by_l[l] = A_raw
            A_c_by_l[l] = A_c
            h_by_l[l] = h_l
            tgt_by_l[l] = var_Av(A_c, h_l)

        # ---- reproduce the production null (same function, same seed, same draw order, same RAW A as
        # measure() itself passes -- aniso_random_dirs does its own centring, so passing the pre-centred
        # copy here would double-centre and drift from production by float rounding)
        null_dirs_prod: dict[str, np.ndarray] = {}
        info_prod: dict[str, list[dict]] = {}
        for cname, off in CAND_OFFSET.items():
            rng_c = np.random.default_rng(M.SEED + off)
            V = np.zeros((len(B_mid), M.N_RAND, mr.d), np.float32)
            infos = []
            for li, l in enumerate(B_mid):
                V[li], inf_ = M.aniso_random_dirs(A_raw_by_l[l], h_by_l[l], M.N_RAND, rng_c)
                inf_["n_rows"] = int(A_raw_by_l[l].shape[0])
                infos.append(inf_)
            null_dirs_prod[cname] = V
            info_prod[cname] = infos

        # ---- variance-matched null (independent seed 20260921+100+offset)
        null_dirs_match: dict[str, np.ndarray] = {}
        info_match: dict[str, list[dict]] = {}
        for cname, off in CAND_OFFSET.items():
            rng_m = np.random.default_rng(MATCH_SEED_BASE + off)
            V = np.zeros((len(B_mid), M.N_RAND, mr.d), np.float32)
            infos = []
            for li, l in enumerate(B_mid):
                per_draw = []
                for k in range(M.N_RAND):
                    w, dinfo = matched_direction(A_c_by_l[l], h_by_l[l], tgt_by_l[l], rng_m)
                    V[li, k] = w
                    per_draw.append(dinfo)
                infos.append({"n_rows": int(A_c_by_l[l].shape[0]), "var_h": tgt_by_l[l], "draws": per_draw,
                             "achieved_ratio_mean": float(np.mean([d["achieved_ratio"] for d in per_draw])),
                             "achieved_ratio_max_abs_dev_from_1": float(
                                 max(abs(d["achieved_ratio"] - 1.0) for d in per_draw))})
            null_dirs_match[cname] = V
            info_match[cname] = infos

        # ---- run the SAME c1_block / c2_block code path, only null_dirs swapped
        rows_eval = list(range(2 * M.NP))
        c1_prod = mr.c1_block(b, base, D, rows_eval, [M.EPS0], None, null_dirs_prod["C1"])
        c1_match = mr.c1_block(b, base, D, rows_eval, [M.EPS0], None, null_dirs_match["C1"])

        b_full = b.with_items(rows_eval)
        m_ref, _ = mr.skip_call(b_full, j, h_in, [])
        c2_prod = mr.c2_block(b_full, j, h_in, D, m_ref, null_dirs_prod["C2"])
        c2_match = mr.c2_block(b_full, j, h_in, D, m_ref, null_dirs_match["C2"])

        # ---- acceptance check against the production row
        row_path = M.ROWS / f"{M.slug(repo)}.json"
        acc: dict[str, Any] = {}
        row = json.loads(row_path.read_text()) if row_path.exists() else None
        for cname, my_block in (("C1", c1_prod), ("C2", c2_prod)):
            row_v = row["candidates"][cname]["null_p95"] if row else None
            my_v = my_block["null_p95"]
            diff = abs(float(row_v) - float(my_v)) if (row_v is not None and my_v is not None) else None
            acc[cname] = {"row_null_p95": row_v, "reproduced_null_p95": my_v, "abs_diff": diff}

        out["candidates"] = {
            "C1": {
                "value": c1_prod["value"],
                "null_p95_production": c1_prod["null_p95"], "null_p95_matched": c1_match["null_p95"],
                "exceed_production": (c1_prod["value"] is not None and c1_prod["null_p95"] is not None
                                      and c1_prod["value"] > c1_prod["null_p95"]),
                "exceed_matched": (c1_match["value"] is not None and c1_match["null_p95"] is not None
                                   and c1_match["value"] > c1_match["null_p95"]),
                "achieved_ratio_mean_production": float(np.mean([r for infos in info_prod["C1"]
                                                                  for r in infos["ratio_picked"]])),
                "achieved_ratio_mean_matched": float(np.mean([infos["achieved_ratio_mean"]
                                                              for infos in info_match["C1"]])),
            },
            "C2": {
                "value": c2_prod["value"],
                "null_p95_production": c2_prod["null_p95"], "null_p95_matched": c2_match["null_p95"],
                "exceed_production": (c2_prod["value"] is not None and c2_prod["null_p95"] is not None
                                      and c2_prod["value"] > c2_prod["null_p95"]),
                "exceed_matched": (c2_match["value"] is not None and c2_match["null_p95"] is not None
                                   and c2_match["value"] > c2_match["null_p95"]),
                "achieved_ratio_mean_production": float(np.mean([r for infos in info_prod["C2"]
                                                                  for r in infos["ratio_picked"]])),
                "achieved_ratio_mean_matched": float(np.mean([infos["achieved_ratio_mean"]
                                                              for infos in info_match["C2"]])),
            },
        }
        out["acceptance"] = acc
        out["random_dirs_info_production"] = info_prod
        out["random_dirs_info_matched"] = info_match
        out["BALANCED"] = M.LABELS[repo]["BALANCED"]
        out["status"] = "ok"
        del base, D, b, b_full
    except Exception as e:  # noqa: BLE001 -- never drop a repo silently; record and move on
        logger.exception(f"{repo}: matched_null failed")
        out["status"] = "error"
        out["error"] = f"{type(e).__name__}: {e}"
        out["traceback"] = traceback.format_exc()[-4000:]
    finally:
        try:
            mr.unload()
        except Exception:  # noqa: BLE001
            pass
        del mr
        gc.collect()
        if DEVICE.type == "cuda":
            torch.cuda.empty_cache()
    out["wall_s"] = round(time.time() - t0, 1)
    return out


# ----------------------------------------------------------------------------- analysis
def analyze(results: dict[str, dict]) -> dict:
    graded = [r for r in graded_repos() if results.get(r, {}).get("status") == "ok"]
    bal = {r: float(M.LABELS[r]["BALANCED"]) for r in graded}
    upper = [r for r in graded if bal[r] > BALANCED_MEDIAN]
    lower = [r for r in graded if bal[r] <= BALANCED_MEDIAN]

    totals: dict[str, Any] = {}
    for cname in ("C1", "C2"):
        def count(group: list[str], key: str) -> int:
            return sum(1 for r in group if results[r]["candidates"][cname][key])

        totals[cname] = {
            "n": len(graded),
            "exceed_production_overall": count(graded, "exceed_production"),
            "exceed_matched_overall": count(graded, "exceed_matched"),
            "n_upper": len(upper), "n_lower": len(lower),
            "exceed_production_upper": count(upper, "exceed_production"),
            "exceed_production_lower": count(lower, "exceed_production"),
            "exceed_matched_upper": count(upper, "exceed_matched"),
            "exceed_matched_lower": count(lower, "exceed_matched"),
            "s2b_fraction_production": count(graded, "exceed_production") / len(graded) if graded else None,
            "s2b_fraction_matched": count(graded, "exceed_matched") / len(graded) if graded else None,
            "s2b_pass_production": (count(graded, "exceed_production") / len(graded) >= 0.60) if graded else None,
            "s2b_pass_matched": (count(graded, "exceed_matched") / len(graded) >= 0.60) if graded else None,
        }
    return {"n_graded_models_used": len(graded), "balanced_median_used": BALANCED_MEDIAN,
           "upper_repos": upper, "lower_repos": lower, "totals": totals}


# ----------------------------------------------------------------------------- md report
def write_md(payload: dict) -> None:
    a = payload.get("analysis", {})
    acc = payload["meta"]["acceptance_check"]
    lines = []
    lines.append("# Matched-null robustness check for S2(b) -- C1 / C2 (EXPLORATORY, post hoc)\n")
    lines.append("**This check is exploratory and post hoc. It was never pre-registered, it is not part of "
                 "S1-S6, and it never changes any pre-registered verdict. The only pre-registered C1/C2 "
                 "null_p95 values -- the ones used anywhere in S1-S6's rule S2(b) -- are method.py's "
                 "production values at B_mid = [L_h-1, L_h, L_h+1] (the band at 50% depth), written to "
                 "rows/<slug>.json. Everything below exists purely to describe how much of S2(b)'s C1/C2 "
                 "failure traces to the production null directions' variance mismatch (median ratio "
                 "var(Av)/var(Ah) ~= 2.89 across rows/*.json), for interpretation only.**\n")

    lines.append("## Acceptance check\n")
    for cname in ("C1", "C2"):
        c = acc[cname]
        lines.append(f"- **{cname}**: max |reproduced null_p95 - rows/<slug>.json "
                     f"candidates.{cname}.null_p95| over {c['n_checked']} models: **{c['max_abs_diff']}** "
                     f"(tolerance {ACCEPTANCE_TOL}). "
                     + ("All checked models passed." if not c["failures"]
                        else f"FAILED on {len(c['failures'])} model(s): {c['failures']}"))
    lines.append("")

    if a:
        lines.append("\n## S2(b) exceed counts: production null vs variance-matched null\n")
        lines.append(f"Split by the BALANCED median ({a['balanced_median_used']:.4f}): upper = BALANCED > "
                     f"median, lower = BALANCED <= median.\n")
        lines.append("| candidate | null | overall | upper half | lower half | S2(b) fraction | S2(b) pass (>=60%) |")
        lines.append("|---|---|---|---|---|---|---|")
        for cname in ("C1", "C2"):
            t = a["totals"][cname]
            lines.append(f"| {cname} | production | {t['exceed_production_overall']}/{t['n']} | "
                         f"{t['exceed_production_upper']}/{t['n_upper']} | "
                         f"{t['exceed_production_lower']}/{t['n_lower']} | "
                         f"{t['s2b_fraction_production']:.3f} | {t['s2b_pass_production']} |")
            lines.append(f"| {cname} | matched | {t['exceed_matched_overall']}/{t['n']} | "
                         f"{t['exceed_matched_upper']}/{t['n_upper']} | "
                         f"{t['exceed_matched_lower']}/{t['n_lower']} | "
                         f"{t['s2b_fraction_matched']:.3f} | {t['s2b_pass_matched']} |")

        lines.append("\n## Per-model detail\n")
        lines.append("| repo | BALANCED | C1 value | C1 null_p95 (prod) | C1 null_p95 (matched) | C1 exceed "
                     "(prod/matched) | C1 mean ratio (prod/matched) | C2 value | C2 null_p95 (prod) | "
                     "C2 null_p95 (matched) | C2 exceed (prod/matched) | C2 mean ratio (prod/matched) |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in sorted(payload["repos"], key=lambda x: -M.LABELS.get(x, {}).get("BALANCED", 0)):
            v = payload["repos"][r]
            if v.get("status") != "ok":
                continue
            c1, c2 = v["candidates"]["C1"], v["candidates"]["C2"]
            fmt = lambda x: f"{x:.3f}" if isinstance(x, (int, float)) else "n/a"  # noqa: E731
            lines.append(f"| {r} | {fmt(v['BALANCED'])} | {fmt(c1['value'])} | {fmt(c1['null_p95_production'])} | "
                         f"{fmt(c1['null_p95_matched'])} | {c1['exceed_production']}/{c1['exceed_matched']} | "
                         f"{fmt(c1['achieved_ratio_mean_production'])}/{fmt(c1['achieved_ratio_mean_matched'])} | "
                         f"{fmt(c2['value'])} | {fmt(c2['null_p95_production'])} | {fmt(c2['null_p95_matched'])} | "
                         f"{c2['exceed_production']}/{c2['exceed_matched']} | "
                         f"{fmt(c2['achieved_ratio_mean_production'])}/{fmt(c2['achieved_ratio_mean_matched'])} |")

        lines.append("\n## Interpretation\n")
        for cname in ("C1", "C2"):
            t = a["totals"][cname]
            same = t["s2b_pass_production"] == t["s2b_pass_matched"]
            lines.append(f"- **{cname}**: production null exceed count {t['exceed_production_overall']}/{t['n']} "
                         f"({t['s2b_fraction_production']:.1%}) vs variance-matched null exceed count "
                         f"{t['exceed_matched_overall']}/{t['n']} ({t['s2b_fraction_matched']:.1%}). "
                         + ("The variance-matched null does NOT change the S2(b) pass/fail outcome for "
                            f"{cname} (both {'reach' if t['s2b_pass_matched'] else 'fail'} the >=60% bar)."
                            if same else
                            f"The variance-matched null FLIPS the S2(b) outcome for {cname} from "
                            f"{'pass' if t['s2b_pass_production'] else 'fail'} (production) to "
                            f"{'pass' if t['s2b_pass_matched'] else 'fail'} (matched) -- exploratory only, "
                            "the pre-registered verdict is unaffected."))
        lines.append("\nThis check is exploratory and post hoc; it never changes S1-S6, and the "
                     "pre-registered S2(b) verdict (C1 11/23, C2 7/23, both below the 60% bar) stands "
                     "regardless of what the matched null shows.\n")

    lines.append("\n## Runtime\n")
    lines.append(f"Total wall time: {payload['meta']['total_wall_s']:.0f}s over "
                f"{payload['meta']['n_repos_attempted']} repos.\n")

    failed = [r for r, v in payload["repos"].items() if v.get("status") != "ok"]
    lines.append("\n## Failures\n")
    lines.append(f"{len(failed)} repo(s) failed: {failed}\n" if failed else "None.\n")

    OUT_MD.write_text("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------- driver
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default="", help="comma-separated repo list; default = all 23 graded repos")
    ap.add_argument("--force", action="store_true", help="re-run repos that already have a status=ok entry")
    ap.add_argument("--limit", type=int, default=999, help="stop after this many NEW repos")
    a = ap.parse_args()

    if DEVICE.type == "cuda":
        total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        torch.cuda.set_per_process_memory_fraction(M.VRAM_CAP_GB / total_vram_gb)
        logger.info(f"CUDA device {torch.cuda.get_device_name(0)}: {total_vram_gb:.1f} GB total, "
                    f"capped at {M.VRAM_CAP_GB} GB ({M.VRAM_CAP_GB / total_vram_gb:.3f} fraction)")

    repos = [r for r in a.repos.split(",") if r] if a.repos else default_repo_order()
    logger.info(f"repos ({len(repos)}): {repos}")

    payload: dict[str, Any] = {"meta": {}, "repos": {}}
    if OUT_JSON.exists():
        try:
            payload = json.loads(OUT_JSON.read_text())
            payload.setdefault("repos", {})
        except (json.JSONDecodeError, OSError):
            payload = {"meta": {}, "repos": {}}

    t0 = time.time()
    done_new = 0
    for repo in repos:
        if done_new >= a.limit:
            break
        if (not a.force) and payload["repos"].get(repo, {}).get("status") == "ok":
            logger.info(f"skip (already done): {repo}")
            continue
        logger.info(f"=== {repo} ===")
        res = run_one_repo(repo)
        payload["repos"][repo] = res
        done_new += 1
        if res["status"] == "ok":
            status_msg = f"acc_C1={res['acceptance']['C1']['abs_diff']} acc_C2={res['acceptance']['C2']['abs_diff']}"
        else:
            status_msg = res.get("error")
        logger.info(f"{repo}: status={res['status']} wall_s={res['wall_s']} {status_msg}")
        M.atomic_write(OUT_JSON, {**payload, "meta": {**payload.get("meta", {}), "partial": True}})

    ok_results = {r: v for r, v in payload["repos"].items() if v.get("status") == "ok"}
    acceptance: dict[str, Any] = {}
    for cname in ("C1", "C2"):
        diffs = {r: v["acceptance"][cname]["abs_diff"] for r, v in ok_results.items()
                if v.get("acceptance", {}).get(cname, {}).get("abs_diff") is not None}
        failures = [r for r, d in diffs.items() if d > ACCEPTANCE_TOL]
        acceptance[cname] = {"n_checked": len(diffs), "max_abs_diff": (max(diffs.values()) if diffs else None),
                             "per_repo_abs_diff": diffs, "failures": failures, "tolerance": ACCEPTANCE_TOL}

    ratio_violations = []
    for r, v in ok_results.items():
        for cname in ("C1", "C2"):
            for infos in v.get("random_dirs_info_matched", {}).get(cname, []):
                if infos["achieved_ratio_max_abs_dev_from_1"] > RATIO_TOL:
                    ratio_violations.append({"repo": r, "candidate": cname,
                                            "max_abs_dev": infos["achieved_ratio_max_abs_dev_from_1"]})

    analysis = analyze(ok_results) if any(r in ok_results for r in graded_repos()) else {}

    payload["meta"] = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                       "acceptance_check": acceptance, "matched_ratio_tolerance": RATIO_TOL,
                       "matched_ratio_violations": ratio_violations,
                       "total_wall_s": time.time() - t0, "n_repos_attempted": len(repos),
                       "match_seed_base": MATCH_SEED_BASE, "cand_offset": CAND_OFFSET,
                       "note": "EXPLORATORY / post hoc. Never enters S1-S6. See matched_null.md."}
    payload["analysis"] = analysis
    M.atomic_write(OUT_JSON, payload)
    write_md(payload)
    logger.info(f"acceptance: {acceptance}")
    logger.info(f"ratio_violations: {len(ratio_violations)}")
    logger.info(f"wrote {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    main()

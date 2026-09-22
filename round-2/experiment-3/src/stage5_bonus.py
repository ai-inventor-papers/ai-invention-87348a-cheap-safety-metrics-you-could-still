#!/usr/bin/env python3
"""STAGE 5 = PART 4 - the request's first bonus: what is the readout reading, and what breaks it.

5.1 WHICH LAYERS AND COMPONENTS CARRY IT  - the endpoint recomputed per depth quintile and per
    matrix family (o_proj vs down_proj).
5.2 ANISOTROPY-MATCHED RANDOM-DIRECTION NULL - NOT an isotropic Gaussian null. A prior iteration in
    this project measured that the isotropic null is wrong and ties the fitted probe, so the null
    directions here are drawn to match the empirical covariance of the REAL recovered bottom
    directions across the HONEST panel. Both nulls are reported so the reader sees how much the
    matching mattered.
5.3 THE CHEAPEST FORGERY - add a rank-one term back into an already-abliterated checkpoint and
    sweep its size until the detector is healed. Pre-registered prediction: the DETECTOR is healed
    and the BEHAVIOUR is not, which would make the detection column cheap to fake.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec import recipe as R  # noqa: E402
from lanec import stats as S  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage5.log"), rotation="30 MB", level="DEBUG")

VEC_DIR = WS / "results" / "vecs"
CKPT_DIR = WS / "results" / "ckpt"


def load_ckpts() -> list[dict]:
    out = []
    for fp in sorted(CKPT_DIR.glob("*.json")):
        c = json.loads(fp.read_text())
        if c.get("status") == "OK":
            out.append(c)
    return out


def load_vecs(repo_id: str, comp: str = "mlp") -> dict[int, np.ndarray]:
    """Default to down_proj: it is the only residual-write site with d_in > d_out on every family
    on this panel, and therefore the only one whose bottom direction is interpretable."""
    fp = VEC_DIR / f"{repo_id.replace('/', '__')}.npz"
    if not fp.exists():
        return {}
    with np.load(fp) as z:
        return {int(k.split("_")[-1]): z[k] for k in z.files if k.startswith(f"{comp}_u_")}


# ---------------------------------------------------------------- 5.1 layer / component profile
def layer_profile(ckpts: list[dict], graded: dict[str, dict]) -> dict[str, Any]:
    """Recompute the endpoint from each depth quintile, and from each matrix family separately."""
    out: dict[str, Any] = {}
    for comp in ("attn", "mlp"):
        for q in range(5):
            xs, ys, fams = [], [], []
            for c in ckpts:
                g = graded.get(c["repo_id"])
                if not g or g.get("COMPLIANCE") is None or c.get("arm") != "edited":
                    continue
                pl = ((c.get("by_component") or {}).get(comp) or {}).get("per_layer_kappa_hat") or {}
                if not pl:
                    continue
                ls = sorted(int(k) for k in pl)
                lo, hi = int(len(ls) * q / 5), max(int(len(ls) * (q + 1) / 5), 1)
                sel = [pl[str(l)] for l in ls[lo:hi] if np.isfinite(pl[str(l)])]
                if not sel:
                    continue
                xs.append(float(np.max(sel))); ys.append(float(g["COMPLIANCE"]))
                fams.append(c.get("family_signature", "?"))
            if len(xs) >= 5 and np.ptp(xs) > 0:
                out[f"{comp}_quintile{q+1}"] = {
                    **S.cluster_bootstrap_spearman(xs, ys, fams, n_boot=2000),
                    "depth_fraction": [q / 5, (q + 1) / 5]}
        xs, ys, fams = [], [], []
        for c in ckpts:
            g = graded.get(c["repo_id"])
            h = (c.get("by_component") or {}).get(comp) or {}
            if not g or g.get("COMPLIANCE") is None or c.get("arm") != "edited":
                continue
            v = h.get("kappa_hat_max")
            if v is None or not np.isfinite(v):
                continue
            xs.append(float(v)); ys.append(float(g["COMPLIANCE"])); fams.append(c.get("family_signature", "?"))
        if len(xs) >= 5 and np.ptp(xs) > 0:
            out[f"{comp}_whole"] = S.cluster_bootstrap_spearman(xs, ys, fams, n_boot=2000)
    return out


# ---------------------------------------------------------------- 5.2 anisotropy-matched null
def anisotropy_null(ckpts: list[dict], n_draws: int = 80, seed: int = 20260920,
                    max_families: int = 4, time_budget_s: float = 900.0) -> dict[str, Any]:
    """Null distributions of BSA_w8 and XLC under directions matched to the HONEST panel's own
    anisotropy, and (for contrast) under isotropic Gaussian directions."""
    by_sig: dict[str, list[np.ndarray]] = {}
    honest_layers: dict[str, list[dict[int, np.ndarray]]] = {}
    for c in ckpts:
        if c.get("arm") != "edited":
            v = load_vecs(c["repo_id"])
            if v:
                sig = c.get("family_signature", "?")
                by_sig.setdefault(sig, []).extend(list(v.values()))
                honest_layers.setdefault(sig, []).append(v)
    min_vecs = 8
    pooled_by_dim = False
    if not any(len(v) >= min_vecs for v in by_sig.values()):
        # No single architecture family has enough honest bottom directions yet. Pool by d_model
        # instead and SAY SO: the null then describes the anisotropy of honest bottom directions at
        # that width rather than within one family, which is a weaker but still matched reference.
        pooled: dict[str, list[np.ndarray]] = {}
        pooled_layers: dict[str, list[dict[int, np.ndarray]]] = {}
        for sig, vs in by_sig.items():
            if not vs:
                continue
            key = f"d_model={vs[0].shape[-1]} (POOLED ACROSS FAMILIES)"
            pooled.setdefault(key, []).extend(vs)
            pooled_layers.setdefault(key, []).extend(honest_layers[sig])
        if any(len(v) >= min_vecs for v in pooled.values()):
            by_sig, honest_layers, pooled_by_dim = pooled, pooled_layers, True
    out: dict[str, Any] = {"per_family": {}}
    rng = np.random.default_rng(seed)
    t_start = time.time()
    # process the best-populated families first, and stop on the time budget: the null is a
    # per-family statement, so four well-populated families say more than twelve thin ones
    order = sorted(by_sig, key=lambda k: -len(by_sig[k]))[:max_families]
    for sig in order:
        vecs = by_sig[sig]
        if len(vecs) < min_vecs or time.time() - t_start > time_budget_s:
            continue
        V = np.stack([v.astype(np.float64).ravel() for v in vecs], axis=0)
        nV = np.linalg.norm(V, axis=1, keepdims=True)
        nV[nV == 0] = 1.0
        V = V / nV
        d = V.shape[1]
        n_layers = int(np.median([len(x) for x in honest_layers[sig]])) or 8

        # LOW-RANK FACTOR FORM. The anisotropy-matched null draws directions from N(0, C) with
        # C = V^T V / n, the empirical covariance of the REAL recovered bottom directions on the
        # honest panel. Sampling that as normalise(V^T g), g ~ N(0, I/n), is EXACTLY the same
        # distribution as a Cholesky draw from C but costs O(n_vectors * d) instead of O(d^2) --
        # about three orders of magnitude less here, which is what makes the null affordable at all
        # on this worker. The isotropic contrast is drawn the usual way.
        def draw(aniso: bool) -> dict[str, float]:
            dd = {}
            if aniso:
                G = rng.standard_normal((n_layers, V.shape[0])) / np.sqrt(V.shape[0])
                M = G @ V                                    # (n_layers, d)
            else:
                M = rng.standard_normal((n_layers, d))
            nm = np.linalg.norm(M, axis=1, keepdims=True)
            nm[nm == 0] = 1.0
            M = M / nm
            for l in range(n_layers):
                dd[l] = M[l]
            return {"bsa": R.bsa_window(dd, window=min(8, n_layers))["bsa_w"],
                    "xlc": R.cross_layer_cosine(dd)["xlc"]}

        an = [draw(True) for _ in range(n_draws)]
        iso = [draw(False) for _ in range(n_draws)]
        def _bsa(c):
            m = ((c.get("by_component") or {}).get("mlp") or {}).get("BSA_w8")
            return m if m is not None else float("nan")

        def _match(c):
            return pooled_by_dim or c.get("family_signature") == sig

        obs_e = [_bsa(c) for c in ckpts if _match(c) and c.get("arm") == "edited"
                 and np.isfinite(_bsa(c))]
        obs_h = [_bsa(c) for c in ckpts if _match(c) and c.get("arm") != "edited"
                 and np.isfinite(_bsa(c))]
        rec = {"n_honest_vectors": int(V.shape[0]), "d_model": int(d), "n_layers_used": n_layers,
               "anisotropic_BSA": {"mean": float(np.mean([a["bsa"] for a in an])),
                                   "q95": float(np.percentile([a["bsa"] for a in an], 95))},
               "isotropic_BSA": {"mean": float(np.mean([a["bsa"] for a in iso])),
                                 "q95": float(np.percentile([a["bsa"] for a in iso], 95))},
               "anisotropic_XLC": {"mean": float(np.mean([a["xlc"] for a in an])),
                                   "q95": float(np.percentile([a["xlc"] for a in an], 95))},
               "isotropic_XLC": {"mean": float(np.mean([a["xlc"] for a in iso])),
                                 "q95": float(np.percentile([a["xlc"] for a in iso], 95))},
               "observed_edited_BSA_mean": float(np.mean(obs_e)) if obs_e else None,
               "observed_honest_BSA_mean": float(np.mean(obs_h)) if obs_h else None}
        if obs_e:
            rec["p_edited_vs_anisotropic_null"] = float(
                np.mean([a["bsa"] >= float(np.mean(obs_e)) for a in an]))
        if obs_h:
            rec["p_honest_vs_anisotropic_null"] = float(
                np.mean([a["bsa"] >= float(np.mean(obs_h)) for a in an]))
        out["per_family"][sig] = rec
        logger.info(f"    null for {sig}: aniso BSA mean {rec['anisotropic_BSA']['mean']:.3f} "
                    f"vs iso {rec['isotropic_BSA']['mean']:.3f}; observed edited "
                    f"{rec.get('observed_edited_BSA_mean')} honest "
                    f"{rec.get('observed_honest_BSA_mean')}")
    out["n_families_processed"] = len(out["per_family"])
    out["pooled_across_families_by_d_model"] = pooled_by_dim
    out["min_honest_vectors_required"] = min_vecs
    out["component"] = "mlp (down_proj) - the only site with d_in > d_out on every family here"
    out["n_draws"] = n_draws
    out["note"] = ("The isotropic null is reported only as a contrast. A prior iteration in this "
                   "project measured that it is WRONG - it ties the fitted probe - so the "
                   "anisotropy-matched null is the one the p-values are taken from.")
    return out


# ---------------------------------------------------------------- 5.3 the cheapest forgery
def forgery_sweep(repo_id: str, token: str | None, max_layers: int = 8,
                  epss: tuple[float, ...] = (0.0, 0.05, 0.15, 0.35, 0.6, 1.0)
                  ) -> dict[str, Any]:
    """Add a rank-one term back into an abliterated checkpoint until the detector is healed."""
    sess = R._session(token)
    try:
        plan = R.plan_repo(repo_id, token=token, sess=sess)
        if plan.skip_reason:
            return {"repo_id": repo_id, "error": plan.skip_reason}
        attn = {t["layer"]: t for _, t in plan.targets.items() if t["component"] == "attn"}
        layers = sorted(attn)[:max_layers]
        t0 = time.time()
        Ws = {l: R.fetch_tensor(sess, repo_id, attn[l]).astype(np.float64) for l in layers}
        fetch_s = time.time() - t0
        rows, t1 = [], time.time()
        flops = 0
        # the UNREPAIRED spectrum of each layer is computed ONCE, not once per eps: the sweep only
        # changes the rank-one term that is added back, not the matrix it is added to
        base: dict[int, dict] = {}
        for l, W in Ws.items():
            st = R.spectrum_stats(W)
            j = min(int(st["j_star"]), st["u_bottom"].shape[1] - 1)
            base[l] = {"u": st["u_bottom"][:, j].astype(np.float64), "botgap": st["botgap"],
                       "s_rms": st["s_rms"]}
        for eps in epss:
            u_by, bots = {}, {}
            for l, W in Ws.items():
                st = base[l]
                u = st["u"]
                if eps > 0:
                    # the forgery: push the suppressed direction back up to eps * the RMS singular
                    # value, using only the checkpoint's OWN weights. Zero labels, zero prompts.
                    v = (u @ W)
                    nv = np.linalg.norm(v)
                    v = v / nv if nv > 0 else v
                    Wf = W + (eps * st["s_rms"]) * np.outer(u, v)
                    flops += 2 * W.shape[0] * W.shape[1]
                    st2 = R.spectrum_stats(Wf)
                    j2 = min(int(st2["j_star"]), st2["u_bottom"].shape[1] - 1)
                    u_by[l] = st2["u_bottom"][:, j2]
                    bots[l] = st2["botgap"]
                else:
                    u_by[l] = u
                    bots[l] = st["botgap"]
            bsa = R.bsa_window(u_by, window=min(8, len(layers)))["bsa_w"]
            bm = float(min(bots.values()))
            rows.append({"eps": eps, "BOTGAP_min": bm, "BSA_w8": bsa,
                         "detector_healed": bool(bm > 0.10 and bsa < 0.35)})
            logger.info(f"    eps={eps:<5} BOTGAP_min={bm:.4f} BSA_w8={bsa:.3f} "
                        f"healed={rows[-1]['detector_healed']}")
        healed = next((r for r in rows if r["detector_healed"]), None)
        return {"repo_id": repo_id, "n_layers": len(layers), "rows": rows,
                "fetch_seconds": round(fetch_s, 1),
                "compute_seconds": round(time.time() - t1, 1),
                "flops_for_the_edit": int(flops), "labelled_examples_needed": 0,
                "prompts_needed": 0,
                "cheapest_healing_eps": healed["eps"] if healed else None,
                "detector_is_forgeable": bool(healed is not None),
                "PREREGISTERED_PREDICTION":
                    "the detector is healed and the behaviour is NOT; if that holds, the detection "
                    "column is cheap to fake and the finding must be stated",
                "behavioural_remeasurement": "NOT RUN - no GPU on this worker (failure branch F5); "
                                             "handed to the forgery lane as a prediction"}
    finally:
        sess.close()


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--forgery-repo", default="")
    ap.add_argument("--skip-forgery", action="store_true")
    args = ap.parse_args()
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    ckpts = load_ckpts()
    graded = {}
    for fp in (WS / "results" / "graded").glob("*.json"):
        g = json.loads(fp.read_text())
        graded[g["repo_id"]] = g
    logger.info(f"STAGE 5 on {len(ckpts)} checkpoints, {len(graded)} graded")

    out: dict[str, Any] = {"n_ckpt": len(ckpts), "n_graded": len(graded)}
    out["layer_and_component_profile"] = layer_profile(ckpts, graded)
    logger.info("  5.1 layer/component profile done")
    try:
        out["anisotropy_matched_null"] = anisotropy_null(ckpts)
    except (ValueError, np.linalg.LinAlgError, MemoryError) as exc:
        logger.error(f"anisotropy null failed: {exc}")
        out["anisotropy_matched_null"] = {"error": str(exc)}
    logger.info("  5.2 anisotropy-matched null done")

    if not args.skip_forgery:
        repo = args.forgery_repo
        if not repo:
            ed = [c for c in ckpts if c.get("arm") == "edited"
                  and np.isfinite(c.get("BOTGAP_min", float("nan")))]
            ed.sort(key=lambda c: (c.get("BOTGAP_min", 1.0), c.get("n_params_est") or 1e12))
            repo = ed[0]["repo_id"] if ed else ""
        if repo:
            logger.info(f"  5.3 forgery sweep on {repo}")
            try:
                out["forgery"] = forgery_sweep(repo, token)
            except (R.RangedReadError, OSError, ValueError) as exc:
                out["forgery"] = {"error": str(exc), "repo_id": repo}
        else:
            out["forgery"] = {"error": "no edited checkpoint with a finite BOTGAP_min available"}
    (WS / "results" / "forgery_handoff.json").write_text(
        json.dumps(out.get("forgery", {}), indent=2, default=float))
    (WS / "results" / "stage5_bonus.json").write_text(json.dumps(out, indent=2, default=float))
    logger.info("STAGE 5 done")


if __name__ == "__main__":
    main()

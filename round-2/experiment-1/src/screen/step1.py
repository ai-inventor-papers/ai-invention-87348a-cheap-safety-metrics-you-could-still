"""P6. THE REQUEST'S STEP 1, AS A NAMED CLAIM.

Both objects are already in the harvest, so this is free: the principal angle
between the instruct-to-SafeRL and the instruct-to-abliterated activation
differences on the Qwen3-4B anchor.  Pre-registered TWO-SIDED: either the two
edits live in the SAME subspace and layer band, or in ORTHOGONAL ones.
Base stays in its OWN stratum with the plain renderer and is never mixed in.
"""

from __future__ import annotations

import numpy as np

from .reads import load_harvest


def principal_angles(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Principal angles (radians, ascending) between the row spaces of A and B."""
    Qa, _ = np.linalg.qr(A.T)
    Qb, _ = np.linalg.qr(B.T)
    s = np.linalg.svd(Qa.T @ Qb, compute_uv=False)
    return np.arccos(np.clip(s, -1.0, 1.0))


def _top_rows(D: np.ndarray, k: int) -> np.ndarray:
    """Top-k right singular directions of a set of per-item difference vectors."""
    _, _, Vt = np.linalg.svd(D - D.mean(0, keepdims=True), full_matrices=False)
    return Vt[: min(k, Vt.shape[0])]


def step1_claim(instruct_slug: str, saferl_slug: str, abl_slug: str,
                base_slug: str | None = None, k: int = 8) -> dict:
    hi = load_harvest(instruct_slug)
    hs = load_harvest(saferl_slug)
    ha = load_harvest(abl_slug)

    out: dict = {
        "anchor": {"instruct": hi["meta"]["repo_id"], "saferl": hs["meta"]["repo_id"],
                   "abliterated": ha["meta"]["repo_id"]},
        "k_subspace": k,
        "prediction_two_sided": "SAME subspace and layer band, or ORTHOGONAL ones",
        "positions": {},
    }

    for pos in ("hs_last", "hs_first"):
        Hi, Hs, Ha = (h["a"][pos].astype(np.float64) for h in (hi, hs, ha))
        n = min(len(Hi), len(Hs), len(Ha))
        L = min(Hi.shape[1], Hs.shape[1], Ha.shape[1])
        per_layer = []
        for l in range(L):
            Ds = Hs[:n, l, :] - Hi[:n, l, :]      # instruct -> SafeRL, per item
            Da = Ha[:n, l, :] - Hi[:n, l, :]      # instruct -> abliterated, per item
            ms, ma = Ds.mean(0), Da.mean(0)
            cos_mean = float(ms @ ma / (np.linalg.norm(ms) * np.linalg.norm(ma) + 1e-12))
            ang = principal_angles(_top_rows(Ds, k), _top_rows(Da, k))
            per_layer.append({
                "layer": l,
                "depth_frac": l / max(1, L - 1),
                "cos_mean_difference": cos_mean,
                "first_principal_angle_deg": float(np.degrees(ang[0])),
                "mean_principal_angle_deg": float(np.degrees(ang).mean()),
                "norm_delta_saferl": float(np.linalg.norm(ms)),
                "norm_delta_abliterated": float(np.linalg.norm(ma)),
                "norm_ratio_abl_over_saferl": float(
                    np.linalg.norm(ma) / (np.linalg.norm(ms) + 1e-12)),
            })
        bands = {"early": (0, L // 3), "middle": (L // 3, 2 * L // 3), "late": (2 * L // 3, L)}
        band_summary = {
            bn: {
                "mean_first_principal_angle_deg": float(np.mean(
                    [r["first_principal_angle_deg"] for r in per_layer[a:b]])),
                "mean_cos_mean_difference": float(np.mean(
                    [r["cos_mean_difference"] for r in per_layer[a:b]])),
                "mean_norm_ratio": float(np.mean([r["norm_ratio_abl_over_saferl"]
                                                  for r in per_layer[a:b]])),
            } for bn, (a, b) in bands.items() if b > a
        }
        out["positions"][pos] = {"per_layer": per_layer, "by_band": band_summary}

    # (iii) the same comparison on the WEIGHT side
    wsum = {}
    for mat in ("o_proj", "down_proj"):
        key_top = f"{mat}_top"
        if not all(key_top in h["w"] for h in (hi, hs, ha)):
            continue
        Ti, Ts, Ta = (h["w"][key_top].astype(np.float64) for h in (hi, hs, ha))
        L = min(len(Ti), len(Ts), len(Ta))
        angs_s, angs_a, angs_sa = [], [], []
        for l in range(L):
            angs_s.append(np.degrees(principal_angles(Ti[l][:k], Ts[l][:k])[0]))
            angs_a.append(np.degrees(principal_angles(Ti[l][:k], Ta[l][:k])[0]))
            angs_sa.append(np.degrees(principal_angles(Ts[l][:k], Ta[l][:k])[0]))
        wsum[mat] = {
            "mean_first_angle_instruct_to_saferl_deg": float(np.mean(angs_s)),
            "mean_first_angle_instruct_to_abliterated_deg": float(np.mean(angs_a)),
            "mean_first_angle_saferl_to_abliterated_deg": float(np.mean(angs_sa)),
            "per_layer_instruct_to_abliterated_deg": [float(v) for v in angs_a],
        }
        bi = hi["w"].get(f"{mat}_bot")
        ba = ha["w"].get(f"{mat}_bot")
        bs = hs["w"].get(f"{mat}_bot")
        if bi is not None and ba is not None and bs is not None:
            Lb = min(len(bi), len(ba), len(bs))
            wsum[mat]["mean_bottom1_abs_cos_instruct_vs_abliterated"] = float(np.mean([
                abs(float(bi[l, 0] @ ba[l, 0] /
                          (np.linalg.norm(bi[l, 0]) * np.linalg.norm(ba[l, 0]) + 1e-12)))
                for l in range(Lb)]))
            wsum[mat]["mean_bottom1_abs_cos_instruct_vs_saferl"] = float(np.mean([
                abs(float(bi[l, 0] @ bs[l, 0] /
                          (np.linalg.norm(bi[l, 0]) * np.linalg.norm(bs[l, 0]) + 1e-12)))
                for l in range(Lb)]))
    out["weight_side"] = wsum

    if base_slug:
        hb = load_harvest(base_slug)
        out["base_stratum_note"] = (
            "Base uses the PLAIN renderer and is reported in its own stratum; it is never "
            "mixed into the instruct/SafeRL/abliterated three-way comparison.")
        out["base_repo"] = hb["meta"]["repo_id"]

    # the headline, stated as a number
    hl = out["positions"]["hs_last"]["by_band"]
    ang_all = [r["first_principal_angle_deg"]
               for r in out["positions"]["hs_last"]["per_layer"]]
    cos_all = [r["cos_mean_difference"] for r in out["positions"]["hs_last"]["per_layer"]]
    out["headline"] = {
        "mean_first_principal_angle_deg_last_prompt_token": float(np.mean(ang_all)),
        "min_first_principal_angle_deg": float(np.min(ang_all)),
        "mean_cosine_between_mean_difference_vectors": float(np.mean(cos_all)),
        "band_with_smallest_angle": min(hl, key=lambda b: hl[b]["mean_first_principal_angle_deg"]),
        "by_band": hl,
        "verdict": _verdict(float(np.mean(ang_all)), float(np.mean(cos_all))),
    }
    return out


def _verdict(mean_angle_deg: float, mean_cos: float) -> str:
    if mean_angle_deg < 45.0:
        return ("SHARED_SUBSPACE: the SafeRL edit and the abliteration edit move the "
                "residual stream inside overlapping subspaces")
    if mean_angle_deg > 75.0 and abs(mean_cos) < 0.2:
        return ("ORTHOGONAL: the two edits move the residual stream in essentially "
                "unrelated subspaces")
    return ("PARTIAL_OVERLAP: neither a shared subspace nor orthogonality; the two edits "
            "share some directions and differ in others")

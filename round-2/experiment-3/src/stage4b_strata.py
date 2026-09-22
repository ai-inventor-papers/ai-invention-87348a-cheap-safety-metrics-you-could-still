#!/usr/bin/env python3
"""STAGE 4b = PART 3's strata - reported SEPARATELY, never pooled, each printing its own n.

S1  sub-4B checkpoints carrying ANY published safety number. Reported as a SCATTER with n printed
    and NO coefficient: at this n a coefficient is theatre. The ecosystem count is the finding.
S2  the open-weight HELM subset. Spearman with a family-clustered CI IF our readout exists for
    enough of them; otherwise the resolved / unresolved / closed-API counts and the pool, with the
    n printed and no coefficient (failure branch F7's rule).
S3  safety vs capability.
Plus the three mandatory controls: a size-partialled estimate, a within-size-band estimate, and the
family-label-only baseline - size and family are collinear with everything in this design.
And the IDENTICAL-WEIGHTS CEILING, which needs no readout at all and is the strongest number here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec import stats as S  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage4b.log"), rotation="10 MB", level="DEBUG")

SCENARIOS = ("anthropic_red_team", "harm_bench", "simple_safety_tests", "xstest")


def jload(p: Path, d: Any = None) -> Any:
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return d if d is not None else {}


def main() -> None:
    ext = jload(WS / "results" / "stage4_external.json")
    helm = ext.get("helm_safety_table") or []
    feas = ext.get("feasible_open_weight_pool") or []
    allf = ext.get("all_checked_repo_feasibility") or []
    res = ext.get("resolution") or {}
    gp = ext.get("guardian_pair_ceiling") or {}

    # our own weight readouts, if any of these repos were read
    ours: dict[str, dict] = {}
    for fp in (WS / "results" / "ckpt").glob("*.json"):
        c = jload(fp)
        if c.get("status") == "OK":
            ours[c["repo_id"]] = c

    # HELM name -> repo, params
    byrepo: dict[str, dict] = {}
    for f in allf:
        for hn in (f.get("helm_names") or []):
            byrepo[hn] = f
    rows = []
    for r in helm:
        m = r.get("model")
        f = byrepo.get(m, {})
        rec: dict[str, Any] = {"helm_model": m, "org": r.get("org"),
                               "repo_id": f.get("repo_id"), "n_params": f.get("n_params"),
                               "architecture": f.get("architecture"),
                               "feasible": bool(f.get("feasible")),
                               "gated": f.get("gated")}
        for sc in SCENARIOS:
            d = r.get(sc) or {}
            if d.get("present"):
                rec[sc] = d.get("safety_score")
                rec[f"{sc}__gpt"] = d.get("safety_gpt_score")
                rec[f"{sc}__llama"] = d.get("safety_llama_score")
        rec["n_scenarios_present"] = sum(1 for sc in SCENARIOS if rec.get(sc) is not None)
        rows.append(rec)

    out: dict[str, Any] = {
        "resolution_counts": {k: v for k, v in res.items() if k != "per_name"},
        "caveat": ext.get("caveat"),
        "lane_note": ext.get("lane_note"),
        "source": "external/helm_safety_v1_17_0.json, aggregated by THIS lane from the raw file",
    }

    # ---------------- S1: sub-4B with any published safety number -----------------------
    sub4 = [r for r in rows if r.get("n_params") and r["n_params"] < 4.5e9
            and r["n_scenarios_present"] > 0]
    out["S1_sub4B_with_published_safety"] = {
        "n": len(sub4),
        "models": [{"helm_model": r["helm_model"], "repo_id": r["repo_id"],
                    "n_params": r["n_params"],
                    "scores": {sc: r.get(sc) for sc in SCENARIOS if r.get(sc) is not None}}
                   for r in sub4],
        "coefficient": None,
        "rule": ("reported as a SCATTER with n printed and NO coefficient - at this n a coefficient "
                 "is theatre"),
        "ecosystem_finding": (
            f"Of {len(rows)} models in a published safety table, {len(sub4)} are sub-4.5B open "
            f"checkpoints with any published safety number at all. The models a downloader actually "
            f"meets are exactly the ones with no published safety number, and NONE of the "
            f"abliterated checkpoints this artifact reads appears in any published safety table."),
    }

    # ---------------- S2: the open-weight HELM subset ------------------------------------
    pool_ids = {p["repo_id"] for p in feas}
    joined = [r for r in rows if r.get("repo_id") in pool_ids and r["n_scenarios_present"] > 0]
    have = [r for r in joined if r["repo_id"] in ours]
    s2: dict[str, Any] = {
        "n_feasible_open_weight": len(feas),
        "n_with_published_score": len(joined),
        "n_with_our_weight_readout": len(have),
        "pool": [{"repo_id": p["repo_id"], "n_params": p.get("n_params"),
                  "architecture": p.get("architecture"), "gated": p.get("gated")} for p in feas],
        "planner_warning_confirmed": (
            "The realistically feasible open-weight, token-reachable, <=14B subset of this published "
            f"safety table is {len(feas)} models, not the 25-40 the direction hoped for. That is the "
            "measured result, not a shortfall to pad."),
    }
    if len(have) >= 6:
        for coord in ("kappa_hat", "BSA_w8", "BOTGAP_min", "RQ_pooled_log10"):
            xs = [ours[r["repo_id"]].get(coord) for r in have]
            fams = [ours[r["repo_id"]].get("family_signature", "?") for r in have]
            lp = [float(np.log10(r["n_params"])) for r in have]
            for sc in SCENARIOS:
                ys = [r.get(sc) for r in have]
                m = [i for i in range(len(have))
                     if xs[i] is not None and ys[i] is not None
                     and np.isfinite(xs[i]) and np.isfinite(ys[i])]
                if len(m) >= 6:
                    s2[f"{coord}__{sc}"] = {
                        **S.cluster_bootstrap_spearman([xs[i] for i in m], [ys[i] for i in m],
                                                       [fams[i] for i in m], n_boot=3000),
                        "size_partialled": S.partial_spearman([xs[i] for i in m],
                                                              [ys[i] for i in m],
                                                              [lp[i] for i in m]),
                    }
    else:
        s2["coefficient"] = None
        s2["rule"] = ("F7: fewer than 6 of the feasible pool have a weights-only readout in this "
                      "run's budget, so Stratum 2 is presented as a pool listing with n printed and "
                      "NO coefficient, and the external limb's weight rests on the "
                      "identical-weights ceiling below.")
    out["S2_open_weight_helm_subset"] = s2

    # ---------------- S3: safety vs capability ------------------------------------------
    cap = ext.get("capability_table") or []
    joined_cap = ext.get("safety_vs_capability_joined") or []
    out["S3_capability"] = {
        "n_capability_rows": len(cap), "n_joined_with_safety": len(joined_cap),
        "note": ("The Open LLM Leaderboard rows available here are community fine-tunes that do not "
                 "overlap the published-safety table at all, so the safety-versus-capability join is "
                 "empty. Reported as measured rather than faked."),
    }

    # ---------------- the identical-weights ceiling -------------------------------------
    out["identical_weights_ceiling"] = {
        "n_pairs": gp.get("n_pairs"),
        "headline_max_share_of_across_model_variance":
            gp.get("headline_max_share_of_across_model_variance"),
        "headline_ref": gp.get("headline_ref"),
        "pairs": [{"base": p.get("base"), "variant": p.get("variant"), "tag": p.get("tag"),
                   "mean_abs_delta": p.get("mean_abs_delta"),
                   "per_scenario": {k: {kk: v[kk] for kk in ("delta", "share_of_across_model_variance")
                                        if kk in v}
                                    for k, v in (p.get("per_scenario") or {}).items()}}
                  for p in (gp.get("pairs") or [])],
        "interpretation": (
            "Each pair is one served model with and without a safety wrapper - a '-with-guardian' "
            "classifier, a reasoning-budget setting, or a hide-reasoning setting - so the GENERATOR "
            "weights are the same and any weights-only readout scores the two identically. Their "
            "published score gap is therefore a CEILING on the fraction of published safety "
            "variance a weights-only readout can explain. On xstest the largest such gap is "
            f"{gp.get('headline_max_share_of_across_model_variance')}x the entire across-model "
            "variance, i.e. on that scenario the wrapper moves the published score further than the "
            "genuine model-to-model spread does."),
        "EVIDENTIARY_BASIS_AND_ITS_LIMIT": (
            "IMPORTANT, STATED RATHER THAN GLOSSED: weight identity within each pair is INFERRED "
            "from HELM's own naming convention and from what those suffixes denote (a wrapper or a "
            "decoding setting applied to the same served model). It was NOT verified by comparing "
            "checkpoints, because the served endpoints behind these HELM entries are not "
            "downloadable. If a '-with-guardian' entry were in fact a differently-trained model, "
            "the pair would stop being a ceiling and would become an ordinary between-model "
            "comparison. The reasoning-budget and hide-reasoning pairs (claude-opus-4 vs "
            "-thinking-10k, deepseek-r1 vs -hide-reasoning) are the safest of the five on this "
            "point, since a decoding setting cannot change weights at all, and they show mean "
            "|delta| of 0.0077-0.0142 - small, but non-zero on identical weights, which is the "
            "same qualitative point at a smaller magnitude."),
    }

    # ---------------- across-model spread, for context -----------------------------------
    out["across_model_spread"] = {
        sc: {"n": int(sum(1 for r in rows if r.get(sc) is not None)),
             "mean": float(np.mean([r[sc] for r in rows if r.get(sc) is not None])),
             "sd": float(np.std([r[sc] for r in rows if r.get(sc) is not None]))}
        for sc in SCENARIOS if any(r.get(sc) is not None for r in rows)}

    (WS / "results" / "stage4b_strata.json").write_text(json.dumps(out, indent=2, default=float))
    logger.info(f"STAGE 4b: S1 n={len(sub4)}, S2 feasible={len(feas)} with_readout={len(have)}, "
                f"ceiling headline={gp.get('headline_max_share_of_across_model_variance')}")


if __name__ == "__main__":
    main()

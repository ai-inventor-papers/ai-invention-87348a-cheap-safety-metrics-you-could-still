#!/usr/bin/env python3
"""Stage 4 — external limb. Aggregates the pre-downloaded HELM safety table, the HELM
AIR-Bench table and the Open LLM Leaderboard capability table into one joined,
name-resolved, feasibility-annotated results file.

This script does NOT compute the final safety-readout correlations (that is a different,
downstream module) and does NOT depend on any parallel dataset-building lane: every input
here is a file this lane fetched and aggregated itself, already on disk under WS/external/.

Run: WS/.venv/bin/python stage4_external.py
Writes: WS/results/stage4_external.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(WS / "logs").mkdir(parents=True, exist_ok=True)
logger.add(WS / "logs" / "stage4.log", rotation="10 MB", retention=5, level="DEBUG", enqueue=True)

from lanec import external  # noqa: E402

HELM_SAFETY_PATH = WS / "external" / "helm_safety_v1_17_0.json"
HELM_AIRBENCH_PATH = WS / "external" / "helm_airbench_v1_19_0.json"
CAPABILITY_PATH = WS / "external" / "openllm_capability.json"
OUT_PATH = WS / "results" / "stage4_external.json"

CAVEAT_TEXT = ("HELM xstest safety_score is an annotator-graded score over the XSTest set, "
               "NOT a pure over-refusal rate.")


def _resolve_all(models: list[str], hf_api: Any) -> dict[str, dict[str, Any]]:
    """Resolve every distinct HELM display name to a repo_id/status verdict."""
    verdicts: dict[str, dict[str, Any]] = {}
    for i, name in enumerate(models, 1):
        v = external.resolve_name_to_repo(name, hf_api=hf_api)
        verdicts[name] = v
        logger.info(f"[{i}/{len(models)}] resolve {name} -> "
                    f"{v['status']} ({v.get('repo_id')})")
    return verdicts


def _build_feasible_pool(verdicts: dict[str, dict[str, Any]], hf_api: Any) -> list[dict[str, Any]]:
    """Run helm_feasibility on every RESOLVED repo_id, once per distinct repo_id (several
    HELM names — e.g. a guardian-wrapper pair — can resolve to the same repo_id).
    """
    resolved = {v["repo_id"]: v for v in verdicts.values()
                if v["status"] in ("RESOLVED_HANDMAP", "RESOLVED_SEARCH") and v.get("repo_id")}
    pool: list[dict[str, Any]] = []
    for i, repo_id in enumerate(sorted(resolved), 1):
        feas = external.helm_feasibility(repo_id, hf_api)
        helm_names = sorted(n for n, v in verdicts.items() if v.get("repo_id") == repo_id)
        feas["helm_names"] = helm_names
        pool.append(feas)
        logger.info(f"[{i}/{len(resolved)}] feasibility {repo_id}: "
                    f"feasible={feas['feasible']} n_params={feas.get('n_params')} "
                    f"reasons={feas['infeasible_reasons']}")
    return pool


def _join_safety_capability(safety_table: list[dict[str, Any]],
                             verdicts: dict[str, dict[str, Any]],
                             capability_table: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join each resolved HELM model's mean xstest/harm_bench/simple_safety_tests safety_score
    onto the capability table's repo, matched case-insensitively on repo_id.
    """
    cap_by_repo_lower = {r["repo_lower"]: r for r in capability_table if r.get("repo_lower")}
    joined: list[dict[str, Any]] = []
    for row in safety_table:
        verdict = verdicts.get(row["model"], {})
        repo_id = verdict.get("repo_id")
        if not repo_id:
            continue
        cap = cap_by_repo_lower.get(repo_id.lower())
        if cap is None:
            continue
        safety_scores = [row[scen]["safety_score"] for scen in
                          ("xstest", "harm_bench", "simple_safety_tests", "anthropic_red_team")
                          if row.get(scen, {}).get("present") and row[scen].get("safety_score") is not None]
        joined.append({
            "model": row["model"], "repo_id": repo_id,
            "mean_safety_score": sum(safety_scores) / len(safety_scores) if safety_scores else None,
            "n_safety_scenarios": len(safety_scores),
            "mmlu": cap.get("mmlu"), "gsm8k": cap.get("gsm8k"), "arc": cap.get("arc"),
        })
    return joined


@logger.catch(reraise=True)
def main() -> None:
    for p in (HELM_SAFETY_PATH, HELM_AIRBENCH_PATH, CAPABILITY_PATH):
        if not p.exists():
            logger.error(f"required input missing: {p}")
            raise FileNotFoundError(str(p))

    logger.info("loading HELM safety table")
    safety_table = external.load_helm_safety(HELM_SAFETY_PATH)
    models = [r["model"] for r in safety_table]
    logger.info(f"{len(models)} distinct HELM models in the safety table")

    logger.info("loading HELM AIR-Bench table")
    airbench_table = external.load_airbench(HELM_AIRBENCH_PATH)

    logger.info("loading Open LLM Leaderboard capability table")
    capability_table = external.load_capability(CAPABILITY_PATH)

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        logger.warning("HF_TOKEN not set in environment; gated-repo feasibility checks will "
                        "under-report token_can_read")
    from huggingface_hub import HfApi

    hf_api = HfApi(token=hf_token)

    logger.info("resolving HELM names to HF repo_ids")
    verdicts = _resolve_all(models, hf_api)

    n_closed = sum(1 for v in verdicts.values() if v["status"] == "CLOSED_API_BY_CONSTRUCTION")
    n_resolved_handmap = sum(1 for v in verdicts.values() if v["status"] == "RESOLVED_HANDMAP")
    n_resolved_search = sum(1 for v in verdicts.values() if v["status"] == "RESOLVED_SEARCH")
    n_unresolved = sum(1 for v in verdicts.values() if v["status"] == "UNRESOLVED")
    n_resolved = n_resolved_handmap + n_resolved_search
    logger.info(f"resolution: resolved={n_resolved} (handmap={n_resolved_handmap} "
                f"search={n_resolved_search}) unresolved={n_unresolved} closed_api={n_closed} "
                f"(total={len(verdicts)})")

    logger.info("checking HF feasibility for every resolved repo_id")
    feasible_pool_all = _build_feasible_pool(verdicts, hf_api)
    feasible_pool = [f for f in feasible_pool_all if f["feasible"]]
    logger.info(f"feasible open-weight pool: {len(feasible_pool)} / {len(feasible_pool_all)} "
                f"resolved repos pass the feasibility gate")
    if len(feasible_pool) < 6:
        logger.warning(f"feasible pool has only {len(feasible_pool)} repos (< 6) — reporting "
                        f"this honestly, NOT padding it")

    logger.info("computing guardian-pair ceiling")
    ceiling = external.guardian_pair_ceiling(safety_table)
    logger.info(f"guardian_pair_ceiling: {ceiling['n_pairs']} pairs, "
                f"headline_max_share={ceiling['headline_max_share_of_across_model_variance']}")

    logger.info("joining safety scores onto the capability table by resolved repo_id")
    joined = _join_safety_capability(safety_table, verdicts, capability_table)
    logger.info(f"safety_vs_capability_joined: {len(joined)} rows matched by repo_id")

    output: dict[str, Any] = {
        "helm_safety_table": safety_table,
        "helm_airbench_table": airbench_table,
        "capability_table": capability_table,
        "resolution": {
            "n_models_total": len(verdicts),
            "n_resolved": n_resolved,
            "n_resolved_handmap": n_resolved_handmap,
            "n_resolved_search": n_resolved_search,
            "n_unresolved": n_unresolved,
            "n_closed_api_by_construction": n_closed,
            "per_name": verdicts,
        },
        "feasible_open_weight_pool": feasible_pool,
        "all_checked_repo_feasibility": feasible_pool_all,
        "guardian_pair_ceiling": ceiling,
        "safety_vs_capability_joined": joined,
        "lane_note": "This lane (lanec/external.py + stage4_external.py) aggregated the "
                     "helm_safety_v1_17_0.json, helm_airbench_v1_19_0.json and "
                     "openllm_capability.json tables ITSELF, reading only files already on "
                     "disk under WS/external/, and did NOT depend on any parallel dataset "
                     "lane's output for this aggregation.",
        "caveat": CAVEAT_TEXT,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(output, indent=2, default=str))
    tmp.replace(OUT_PATH)
    logger.info(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.2f} MB)")

    logger.info("=== SUMMARY ===")
    logger.info(f"HELM models: {len(models)}")
    logger.info(f"resolved={n_resolved} unresolved={n_unresolved} closed_api={n_closed}")
    logger.info(f"feasible open-weight pool size: {len(feasible_pool)}")
    for f in feasible_pool:
        logger.info(f"  {f['repo_id']}: n_params={f.get('n_params')} "
                    f"gated={f.get('gated')} names={f.get('helm_names')}")
    logger.info(f"guardian pairs: {ceiling['n_pairs']}")
    for pr in ceiling["pairs"]:
        logger.info(f"  {pr['base']} vs {pr['variant']} [{pr['tag']}]: "
                    f"mean_abs_delta={pr['mean_abs_delta']}")


if __name__ == "__main__":
    main()

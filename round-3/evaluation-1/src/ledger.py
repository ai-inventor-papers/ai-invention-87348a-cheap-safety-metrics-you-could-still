#!/usr/bin/env python3
"""Numbers ledger for the iter-3 hypothesis text: verify every iter-2 headline
number against its source JSON in iter_2/gen_art, by reading each value from
its source file at a recorded key path (never hard-coding the found value).

Only the claim text, the claimed value, and the source path+key are
hard-coded below; every `found_value` is read at run time from the JSON on
disk, so the ledger is reproducible against the iter-2 artifacts.

Writes $WORKSPACE/numbers_ledger.json via `run() -> dict`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

WORKSPACE = Path(__file__).resolve().parent
ITER2_ROOT = Path(
    "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art"
)
PIPELINE2_PY = ITER2_ROOT / "gen_art_experiment_1" / "screen" / "pipeline2.py"

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WORKSPACE / "logs" / "ledger.log", rotation="30 MB", level="DEBUG")

_JSON_CACHE: dict[str, Any] = {}


def load_json(rel_path: str) -> Any:
    """Load and cache a JSON source file, given a path relative to iter_2/gen_art."""
    if rel_path not in _JSON_CACHE:
        fp = ITER2_ROOT / rel_path
        logger.debug(f"loading {fp}")
        _JSON_CACHE[rel_path] = json.loads(fp.read_text())
    return _JSON_CACHE[rel_path]


class PathError(Exception):
    pass


def resolve(obj: Any, path: list) -> Any:
    """Walk a key path. A step is a dict key (str), a list index (int), or a
    tuple ("find", field, value) that searches a list of dicts for the first
    element whose [field] == value."""
    cur = obj
    for step in path:
        try:
            if isinstance(step, tuple) and step[0] == "find":
                _, field, value = step
                match = next((x for x in cur if x.get(field) == value), None)
                if match is None:
                    raise PathError(f"no item with {field}={value!r}")
                cur = match
            else:
                cur = cur[step]
        except (KeyError, IndexError, TypeError) as e:
            raise PathError(f"failed at step {step!r}: {e}") from e
    return cur


def path_to_str(path: list) -> str:
    parts = []
    for step in path:
        if isinstance(step, tuple) and step[0] == "find":
            parts.append(f"[find {step[1]}={step[2]}]")
        elif isinstance(step, int):
            parts[-1] = parts[-1] + f"[{step}]" if parts else f"[{step}]"
        else:
            parts.append(step)
    out = ""
    for p in parts:
        if p.startswith("["):
            out += p
        else:
            out += ("." if out else "") + p
    return out


def get(source_file: str, path: list) -> Any:
    return resolve(load_json(source_file), path)


def num_decimals(claimed: str) -> int:
    s = claimed.strip().rstrip("%")
    return len(s.split(".")[1]) if "." in s else 0


def close(found: float, claimed: str, scale: float = 1.0) -> tuple[float, bool]:
    """Round `found*scale` to the number of decimals in `claimed` and compare."""
    dec = num_decimals(claimed)
    claimed_num = float(claimed.strip().rstrip("%"))
    found_r = round(found * scale, dec)
    tol = 10 ** (-dec) / 2 + 1e-9
    return found_r, abs(found_r - claimed_num) <= tol


ROWS: list[dict] = []


def add_row(
    row_group: str,
    claim_text: str,
    claimed_value: str,
    unit: str,
    panel_tag: str,
    getter,
) -> None:
    """`getter()` must return a dict with keys found_value, ci, n, source_file,
    json_key, reproduced, status, note. It must catch its own lookup errors
    and return status='NOT_FOUND_IN_ARTIFACTS' rather than raising."""
    row = {
        "row_group": row_group,
        "claim_text": claim_text,
        "claimed_value": claimed_value,
        "unit": unit,
        "panel_tag": panel_tag,
    }
    try:
        row.update(getter())
    except Exception as e:  # noqa: BLE001 - this is a discovery ledger, not a pipeline
        logger.error(f"[{row_group}] lookup failed for {claim_text!r}: {e}")
        row.update(
            found_value=None,
            ci=None,
            n=None,
            source_file=None,
            json_key=None,
            reproduced="not_recomputable",
            status="NOT_FOUND_IN_ARTIFACTS",
            note=f"lookup error: {e}",
        )
    ROWS.append(row)
    logger.info(
        f"[{row_group}] {claim_text[:60]!r} -> found={row.get('found_value')!r} "
        f"status={row['status']} reproduced={row['reproduced']}"
    )


# ---------------------------------------------------------------------------
# RACE (P33 = 33 checkpoint / 8 family race, gen_art_experiment_1)
# ---------------------------------------------------------------------------

RACE_JSON = "gen_art_experiment_1/results/race.json"
POLES_JSON = "gen_art_experiment_1/results/poles.json"
STEP5_JSON = "gen_art_experiment_1/results/step5_correlations.json"
BAKEOFF_JSON = "gen_art_experiment_1/results/readout_bakeoff.json"


def _row_race_beat_null():
    n_beat = get(RACE_JSON, ["n_metrics_beating_null_p95"])
    n_fail = get(POLES_JSON, ["n_metrics_failing"])
    n_pass = get(POLES_JSON, ["n_metrics_passing"])
    total = n_fail + n_pass
    found_value = f"{n_beat}/{total}"
    return dict(
        found_value=found_value,
        ci=None,
        n=total,
        source_file="gen_art_experiment_1/results/race.json + results/poles.json",
        json_key="race.json:n_metrics_beating_null_p95 ; poles.json:n_metrics_failing+n_metrics_passing",
        reproduced=(found_value == "3/50"),
        status="FOUND",
        note="total metric count (50) is n_metrics_failing+n_metrics_passing from poles.json, "
        "cross-checked against analysis_out.json class_trend.common_support.support "
        "('ALL 50 metrics are defined').",
    )


add_row(
    "race",
    "3/50 metrics beat the leave-one-LINEAGE-out null p95 in the checkpoint race",
    "3/50",
    "metric",
    "P33",
    _row_race_beat_null,
)


def _row_race_metric(metric_id: str, claimed: str, extra_note: str = ""):
    def getter():
        path = [(list_key := "rows_primary"), ("find", "metric_id", metric_id)]
        row = get(RACE_JSON, [list_key, ("find", "metric_id", metric_id)])
        ba = row["primary_ba"]
        p95 = row["null_null_p95"]
        found = f"{ba:.3f} vs {p95:.3f}"
        m = re.match(r"([\d.]+) vs ([\d.]+)", claimed)
        c_ba, c_p95 = float(m.group(1)), float(m.group(2))
        reproduced = abs(ba - c_ba) < 0.0006 and abs(p95 - c_p95) < 0.0006
        return dict(
            found_value=found,
            ci=None,
            n=row.get("n_checkpoints_with_value"),
            source_file=RACE_JSON,
            json_key=f"rows_primary[find metric_id={metric_id}].primary_ba , .null_null_p95",
            reproduced=reproduced,
            status="FOUND",
            note=extra_note,
        )

    return getter


add_row(
    "race",
    "presentation invariance (x_presentation_invariance) PRIMARY BA vs its null p95",
    "1.000 vs 0.775",
    "checkpoint",
    "P33",
    _row_race_metric("x_presentation_invariance", "1.000 vs 0.775"),
)
add_row(
    "race",
    "card regex termswept (b_card_regex_termswept) PRIMARY BA vs its null p95",
    "0.917 vs 0.788",
    "checkpoint",
    "P33",
    _row_race_metric("b_card_regex_termswept", "0.917 vs 0.788"),
)
add_row(
    "race",
    "logit_gap_alarming (b_logit_gap_alarming) PRIMARY BA vs its null p95",
    "0.800 vs 0.700",
    "checkpoint",
    "P33",
    _row_race_metric("b_logit_gap_alarming", "0.800 vs 0.700"),
)


def _row_race_namefree():
    row = get(RACE_JSON, ["rows_primary", ("find", "metric_id", "b_card_regex_namefree")])
    ba = row["primary_ba"]
    found_r, ok = close(ba, "0.455")
    return dict(
        found_value=found_r,
        ci=None,
        n=row.get("n_checkpoints_with_value"),
        source_file=RACE_JSON,
        json_key="rows_primary[find metric_id=b_card_regex_namefree].primary_ba",
        reproduced=ok,
        status="FOUND",
        note="name-free variant of the card-regex metric; contrast with b_card_regex_termswept's 0.917.",
    )


add_row(
    "race",
    "name-free card regex (b_card_regex_namefree) PRIMARY BA",
    "0.455",
    "checkpoint",
    "P33",
    _row_race_namefree,
)


def _row_pole_failures():
    n = get(POLES_JSON, ["n_metrics_failing"])
    return dict(
        found_value=n,
        ci=None,
        n=None,
        source_file=POLES_JSON,
        json_key="n_metrics_failing",
        reproduced=(n == 19),
        status="FOUND",
        note="cross-checked against race.json digest line 'n_metrics_failing_pole_rule: 19'.",
    )


add_row(
    "race",
    "19 metrics fail the pole rule (blanket-refuser floor)",
    "19",
    "metric",
    "P33",
    _row_pole_failures,
)


def _row_presentation_target(level: str, claimed: str):
    def getter():
        row = get(STEP5_JSON, ["rows", ("find", "metric_id", "x_presentation_invariance")])
        block = row[f"{level}_level"]
        rho = block["spearman"]
        n = block["n"]
        found_r, ok = close(rho, claimed)
        return dict(
            found_value=found_r,
            ci=None,
            n=n,
            source_file=STEP5_JSON,
            json_key=f"rows[find metric_id=x_presentation_invariance].{level}_level.spearman (.n={n})",
            reproduced=ok,
            status="FOUND",
            note=f"Spearman(x_presentation_invariance, two-sided target), {level}-level aggregation.",
        )

    return getter


add_row(
    "race",
    "presentation invariance vs the two-sided target, checkpoint-level Spearman",
    "-0.71",
    "checkpoint",
    "P33",
    _row_presentation_target("checkpoint", "-0.71"),
)
add_row(
    "race",
    "presentation invariance vs the two-sided target, lineage-level Spearman",
    "-0.40",
    "lineage",
    "P33",
    _row_presentation_target("lineage", "-0.40"),
)

# ---------------------------------------------------------------------------
# BAKE-OFF (P15_3 = 15 judged checkpoint / 3 family bake-off, prompt budget)
# ---------------------------------------------------------------------------


def _row_bakeoff(readout: str, field: str, claimed: str, note: str):
    def getter():
        summary = get(BAKEOFF_JSON, ["summary", readout])
        val = summary[field]
        found_r, ok = close(val, claimed)
        return dict(
            found_value=found_r,
            ci=None,
            n=summary.get("n_checkpoints_scored"),
            source_file=BAKEOFF_JSON,
            json_key=f"summary.{readout}.{field}",
            reproduced=ok,
            status="FOUND",
            note=note,
        )

    return getter


add_row(
    "bakeoff",
    "probe_cf readout, minimum per-checkpoint AUROC across the bake-off panel",
    "0.544",
    "checkpoint",
    "P15_3",
    _row_bakeoff("probe_cf", "min_auroc", "0.544", ""),
)
add_row(
    "bakeoff",
    "logitgap readout, minimum per-checkpoint AUROC, with 3/15 checkpoints below chance",
    "0.437",
    "checkpoint",
    "P15_3",
    _row_bakeoff(
        "logitgap",
        "min_auroc",
        "0.437",
        "n_below_chance=3 of n_checkpoints_scored=15 (same summary.logitgap block).",
    ),
)
add_row(
    "bakeoff",
    "logitgap readout, count of checkpoints below chance",
    "3/15",
    "checkpoint",
    "P15_3",
    lambda: (
        lambda s: dict(
            found_value=f"{s['n_below_chance']}/{s['n_checkpoints_scored']}",
            ci=None,
            n=s["n_checkpoints_scored"],
            source_file=BAKEOFF_JSON,
            json_key="summary.logitgap.n_below_chance , .n_checkpoints_scored",
            reproduced=(f"{s['n_below_chance']}/{s['n_checkpoints_scored']}" == "3/15"),
            status="FOUND",
            note="",
        )
    )(get(BAKEOFF_JSON, ["summary", "logitgap"])),
)
add_row(
    "bakeoff",
    "greedy24 readout, minimum per-checkpoint AUROC",
    "0.547",
    "checkpoint",
    "P15_3",
    _row_bakeoff("greedy24", "min_auroc", "0.547", ""),
)

# ---------------------------------------------------------------------------
# DIRECTION NULLS (three counts, one row group, site + panel recorded per row)
# ---------------------------------------------------------------------------

D2_CONTROLS_JSON = "gen_art_evaluation_1/results/d2_controls.json"
DIRECTION_NULLS_JSON = "gen_art_experiment_1/results/direction_nulls.json"


def _row_d2_controls(site_key: str, claimed_frac: str):
    def getter():
        agg = get(D2_CONTROLS_JSON, ["aggregate", site_key])
        found = agg["SURV_span_of_n"]
        return dict(
            found_value=found,
            ci=agg.get("SURV_span_wilson95"),
            n=agg.get("n_checkpoints"),
            source_file=D2_CONTROLS_JSON,
            json_key=f"aggregate.{site_key}.SURV_span_of_n",
            reproduced=(found == claimed_frac),
            status="FOUND",
            note=f"site={site_key}; n_lineages={agg.get('n_lineages')}; "
            f"verdict_band={agg.get('verdict_band')}.",
        )

    return getter


add_row(
    "direction_nulls",
    "content_last (last-token) site: fraction of checkpoints SURVIVING the direction-null span test, "
    "harmful vs plain_benign",
    "16/17",
    "checkpoint",
    "P17_2",
    _row_d2_controls("content_last", "16/17"),
)
add_row(
    "direction_nulls",
    "content_first (first-token) site: fraction of checkpoints SURVIVING the direction-null span test, "
    "harmful vs plain_benign",
    "9/17",
    "checkpoint",
    "P17_2",
    _row_d2_controls("content_first", "9/17"),
)


def _row_direction_nulls_20():
    n = get(DIRECTION_NULLS_JSON, ["n_fitted_beats_within_span_p95"])
    total = get(DIRECTION_NULLS_JSON, ["n_checkpoints"])
    found = f"{n}/{total}"
    return dict(
        found_value=found,
        ci=None,
        n=total,
        source_file=DIRECTION_NULLS_JSON,
        json_key="n_fitted_beats_within_span_p95 , n_checkpoints",
        reproduced=(found == "9/20"),
        status="FOUND",
        note="site=within-span (matched-anisotropy null over the fitted direction's layer span); "
        f"win_rate={get(DIRECTION_NULLS_JSON, ['win_rate'])}; verdict={get(DIRECTION_NULLS_JSON, ['verdict'])}.",
    )


add_row(
    "direction_nulls",
    "within-span site: count of checkpoints where the FITTED direction beats its own matched null p95",
    "9/20",
    "checkpoint",
    "P20_harvest",
    _row_direction_nulls_20,
)

# ---------------------------------------------------------------------------
# PROMPT BUDGET (both scales, P15_3 panel: 15 checkpoints, 9 two-way)
# ---------------------------------------------------------------------------

PROMPT_BUDGET_JSON = "gen_art_experiment_1/results/prompt_budget.json"


def _row_budget_range(field: str, claimed_lo: float, claimed_hi: float, label: str):
    def getter():
        curves = get(PROMPT_BUDGET_JSON, ["curves"])
        vals = [(c["k"], c[field]["mean"]) for c in curves if c[field]["mean"] is not None]
        lo_k, lo_v = min(vals, key=lambda t: t[1])
        hi_k, hi_v = max(vals, key=lambda t: t[1])
        found = f"{lo_v:.3f}-{hi_v:.3f}"
        reproduced = abs(lo_v - claimed_lo) < 0.0015 and abs(hi_v - claimed_hi) < 0.0015
        return dict(
            found_value=found,
            ci=None,
            n=get(PROMPT_BUDGET_JSON, ["n_checkpoints"]),
            source_file=PROMPT_BUDGET_JSON,
            json_key=f"curves[*].{field}.mean (min at k={lo_k}, max at k={hi_k})",
            reproduced=reproduced,
            status="FOUND",
            note=f"{label}; range taken over k in {{1,8,16,32,64}} (k=0 excluded, black-box undefined there).",
        )

    return getter


add_row(
    "prompt_budget",
    "black-box |Spearman rho| vs the two-sided target, range over the prompt-budget grid k=1..64",
    "0.282-0.337",
    "checkpoint",
    "P15_3",
    _row_budget_range("blackbox_abs_spearman", 0.282, 0.337, "black-box = mean first-token logit-gap margin"),
)
add_row(
    "prompt_budget",
    "internal |Spearman rho| vs the two-sided target, range over the prompt-budget grid k=1..64",
    "0.021-0.210",
    "checkpoint",
    "P15_3",
    _row_budget_range(
        "internal_abs_spearman", 0.021, 0.210, "internal = LOO cross-fitted harm-vs-benign separation at 60% depth"
    ),
)


def _row_budget_lolo(k: int, claimed_bb: float, claimed_int: float):
    def getter():
        curves = get(PROMPT_BUDGET_JSON, ["curves"])
        c = next(c for c in curves if c["k"] == k)
        bb = c["blackbox_lolo_ba_2way"]["mean"]
        it = c["internal_lolo_ba_2way"]["mean"]
        reproduced = abs(bb - claimed_bb) < 0.0015 and abs(it - claimed_int) < 0.0015
        idx = curves.index(c)
        return dict(
            found_value=f"{bb:.3f} vs {it:.3f}",
            ci=None,
            n=get(PROMPT_BUDGET_JSON, ["n_checkpoints_two_way"]),
            source_file=PROMPT_BUDGET_JSON,
            json_key=f"curves[{idx}].blackbox_lolo_ba_2way.mean , .internal_lolo_ba_2way.mean (k={k})",
            reproduced=reproduced,
            status="FOUND",
            note="leave-one-LINEAGE-out balanced accuracy, two-way.",
        )

    return getter


add_row(
    "prompt_budget",
    "LOLO balanced accuracy at k=1, black-box vs internal",
    "0.724 vs 0.445",
    "checkpoint",
    "P15_3",
    _row_budget_lolo(1, 0.724, 0.445),
)
add_row(
    "prompt_budget",
    "LOLO balanced accuracy at k=64, black-box vs internal",
    "0.571 vs 0.592",
    "checkpoint",
    "P15_3",
    _row_budget_lolo(64, 0.571, 0.592),
)

# ---------------------------------------------------------------------------
# WEIGHTS (P14_edited = weight EDIT_NOT_RISK panel, gen_art_experiment_3)
# ---------------------------------------------------------------------------

STAGE3_V2_JSON = "gen_art_experiment_3/results/stage3_v2.json"


def _row_edit_not_risk_auroc(section_path: list, claimed: str, note: str):
    def getter():
        auroc = get(STAGE3_V2_JSON, section_path + ["mlp_kappa_hat_band", "auroc_pooled"])
        n = get(STAGE3_V2_JSON, section_path + ["mlp_kappa_hat_band", "n"])
        found_r, ok = close(auroc, claimed)
        return dict(
            found_value=found_r,
            ci=None,
            n=n,
            source_file=STAGE3_V2_JSON,
            json_key=".".join(section_path) + ".mlp_kappa_hat_band.auroc_pooled",
            reproduced=ok,
            status="FOUND",
            note=note,
        )

    return getter


add_row(
    "weights",
    "EDIT_NOT_RISK detection AUROC, all edited vs honest checkpoints (down_proj kappa_hat)",
    "0.84",
    "checkpoint",
    "P14_edited",
    _row_edit_not_risk_auroc(
        ["part1_detection", "statistics"], "0.84", "pooled AUROC, n=71 (36 edited / 35 honest)"
    ),
)
add_row(
    "weights",
    "EDIT_NOT_RISK detection AUROC, abliteration-TOOL outputs only vs honest",
    "0.95",
    "checkpoint",
    "P14_edited",
    _row_edit_not_risk_auroc(
        ["part1_detection", "statistics_abliteration_tool_only"],
        "0.95",
        "pooled AUROC, n=60 (25 edited-by-tool / 35 honest); fine-tune 'uncensored' models excluded.",
    ),
)


def _row_spearman_ci_n(source_file: str, path: list, claimed_rho: str, claimed_ci: tuple, claimed_n: int, note: str):
    def getter():
        node = get(source_file, path)
        rho = node["spearman"]["rho"]
        ci = node["spearman_ci95_family_cluster_boot"]
        n = node["spearman"]["n"]
        rho_r, rho_ok = close(rho, claimed_rho)
        ci_ok = abs(ci[0] - claimed_ci[0]) < 0.006 and abs(ci[1] - claimed_ci[1]) < 0.006
        return dict(
            found_value=rho_r,
            ci=[round(ci[0], 2), round(ci[1], 2)],
            n=n,
            source_file=source_file,
            json_key=path_to_str(path) + ".spearman.rho , .spearman_ci95_family_cluster_boot",
            reproduced=(rho_ok and ci_ok and n == claimed_n),
            status="FOUND",
            note=note,
        )

    return getter


add_row(
    "weights",
    "PRIMARY within-edited Spearman(kappa_hat, COMPLIANCE), real edited checkpoints",
    "0.26",
    "checkpoint",
    "P14_edited",
    _row_spearman_ci_n(
        STAGE3_V2_JSON,
        ["primary_endpoint", "per_checkpoint"],
        "0.26",
        (-0.65, 0.86),
        14,
        "n_families=5, resampling unit=FAMILY. achieved_mde_abs_rho listed separately below.",
    ),
)


def _row_mde():
    v = get(STAGE3_V2_JSON, ["primary_endpoint", "achieved_mde_abs_rho"])
    found_r, ok = close(v, "0.56")
    return dict(
        found_value=found_r,
        ci=None,
        n=14,
        source_file=STAGE3_V2_JSON,
        json_key="primary_endpoint.achieved_mde_abs_rho",
        reproduced=ok,
        status="FOUND",
        note="minimum detectable |rho| for the primary within-edited test, family-cluster bootstrap.",
    )


add_row(
    "weights",
    "achieved MDE |rho| for the primary within-edited test",
    "0.56",
    "family",
    "P14_edited",
    _row_mde,
)


def _row_true_parent():
    rho = get(
        STAGE3_V2_JSON,
        [
            "true_kappa_ground_truth",
            "true_strength_vs_risk_blocks",
            "signed_kappa_true",
            "per_checkpoint",
            "spearman",
            "rho",
        ],
    )
    n = get(
        STAGE3_V2_JSON,
        [
            "true_kappa_ground_truth",
            "true_strength_vs_risk_blocks",
            "signed_kappa_true",
            "per_checkpoint",
            "spearman",
            "n",
        ],
    )
    found_r, ok = close(rho, "0.03")
    return dict(
        found_value=found_r,
        ci=None,
        n=n,
        source_file=STAGE3_V2_JSON,
        json_key="true_kappa_ground_truth.true_strength_vs_risk_blocks.signed_kappa_true.per_checkpoint.spearman.rho",
        reproduced=(ok and n == 12),
        status="FOUND",
        note="PARENT-BASED true realised strength (ground truth, calibration only) vs COMPLIANCE, "
        "projection edits only.",
    )


add_row(
    "weights",
    "true-parent (ground-truth) signed strength vs COMPLIANCE, projection edits only",
    "0.03",
    "checkpoint",
    "P14_edited",
    _row_true_parent,
)


def _row_replication(section: str, claimed_rho: str, claimed_ci: tuple, claimed_n: int, note: str):
    def getter():
        node = get(STAGE3_V2_JSON, ["replication_other_runs", section])
        rho = node["rho"]
        ci = node["ci95"]
        n = node["n_total"]
        rho_r, rho_ok = close(rho, claimed_rho)
        ci_ok = abs(ci[0] - claimed_ci[0]) < 0.006 and abs(ci[1] - claimed_ci[1]) < 0.006
        return dict(
            found_value=rho_r,
            ci=[round(ci[0], 2), round(ci[1], 2)],
            n=n,
            source_file=STAGE3_V2_JSON,
            json_key=f"replication_other_runs.{section}.rho , .ci95 , .n_total",
            reproduced=(rho_ok and ci_ok and n == claimed_n),
            status="FOUND",
            note=note,
        )

    return getter


add_row(
    "weights",
    "n=20 replication over other harvest runs (extD/extE/extF), mixed edit types, within-edited kappa vs COMPLIANCE",
    "0.849",
    "checkpoint",
    "P14_edited",
    _row_replication(
        "combined_kappa_within_edited",
        "0.849",
        (0.56, 0.95),
        20,
        "n-weighted mean Fisher-z of within-source Spearman, 3 sources; placed BESIDE the n=14 primary null.",
    ),
)
add_row(
    "weights",
    "projection-only replication, detected projection edits only",
    "0.65",
    "checkpoint",
    "P14_edited",
    _row_replication(
        "combined_detected_projection_edits_only",
        "0.65",
        (-0.26, 0.95),
        10,
        "restricted to edits the kappa_hat>honest-p95 detector actually flags as projection edits.",
    ),
)


def _row_in_arm_logit_gap():
    node = get(STAGE3_V2_JSON, ["exploratory_within_edited", "L1_logit_gap_H", "per_checkpoint", "spearman"])
    rho, p, n = node["rho"], node["p"], node["n"]
    rho_r, rho_ok = close(rho, "-0.62")
    p_r, p_ok = close(p, "0.02")
    return dict(
        found_value=f"{rho_r} (p={p_r})",
        ci=None,
        n=n,
        source_file=STAGE3_V2_JSON,
        json_key="exploratory_within_edited.L1_logit_gap_H.per_checkpoint.spearman.rho , .p",
        reproduced=(rho_ok and p_ok),
        status="FOUND",
        note="EXPLORATORY (not pre-registered) within-edited readout; 18 such readouts were screened, "
        "so a nominal p<0.05 among them is expected by chance (see exploratory_note in the same file).",
    )


add_row(
    "weights",
    "in-arm logit gap (L1_logit_gap_H) Spearman vs COMPLIANCE, within edited arm",
    "-0.62",
    "checkpoint",
    "P14_edited",
    _row_in_arm_logit_gap,
)

# ---------------------------------------------------------------------------
# DETECTION WITHDRAWN
# ---------------------------------------------------------------------------

EXP2_ANALYSIS_JSON = "gen_art_experiment_2/out/analysis_out.json"


def _row_detection_withdrawn():
    auroc = get(EXP2_ANALYSIS_JSON, ["withdrawal", "best_single_weight_auroc"])
    found_r, ok = close(auroc, "0.738")
    rule = get(EXP2_ANALYSIS_JSON, ["withdrawal", "rule"])
    bar_ok = "0.80" in rule
    return dict(
        found_value=found_r,
        ci=None,
        n=get(EXP2_ANALYSIS_JSON, ["withdrawal"]).get("n_honest_panel"),
        source_file=EXP2_ANALYSIS_JSON,
        json_key="withdrawal.best_single_weight_auroc (bar=0.80 is embedded in withdrawal.rule text)",
        reproduced=(ok and bar_ok),
        status="FOUND",
        note="best single weight metric = w_down_botgap_min; DETECTION_AXIS_WITHDRAWN=True since it does not "
        "clear the pre-registered 0.80 bar at n_honest=39 (12 families). This is the (P6_hosts-scale) grader/"
        "weight-screen panel in gen_art_experiment_2, distinct from gen_art_experiment_3's own held-out-family "
        "BOTGAP_min pooled AUROC (0.737, n=71) reported under the weights rows above.",
    )


add_row(
    "detection_withdrawn",
    "weight screen best single metric (w_down_botgap_min) AUROC vs the pre-registered 0.80 bar -> WITHDRAWN",
    "0.738 vs 0.80",
    "checkpoint",
    "P6_hosts",
    _row_detection_withdrawn,
)


def _row_threshold_97pct():
    fpr = get(STAGE3_V2_JSON, ["part1_detection", "prereg_threshold_operating_points", "mlp_BSA_w8", "fpr_on_honest"])
    found_r, ok = close(fpr, "97%", scale=100.0)
    return dict(
        found_value=f"{found_r}%",
        ci=None,
        n=get(STAGE3_V2_JSON, ["part1_detection", "prereg_threshold_operating_points", "mlp_BSA_w8", "n_honest"]),
        source_file=STAGE3_V2_JSON,
        json_key="part1_detection.prereg_threshold_operating_points.mlp_BSA_w8.fpr_on_honest",
        reproduced=ok,
        status="FOUND",
        note="the PREREG BSA_w8 > 0.35 flag rule, measured on real honest weights (simulated honest was ~0.177).",
    )


add_row(
    "detection_withdrawn",
    "the pre-registered BSA_w8 > 0.35 threshold flags 97% of honest checkpoints as edited",
    "97%",
    "checkpoint",
    "P14_edited",
    _row_threshold_97pct,
)


def _row_forgery_refusal():
    node = get(STAGE3_V2_JSON, ["forgery", "forgery__huihui-Qwen3-0.6B-abl-v2__swap"])
    before = node["HREFUSAL_before_edited"]
    after = node["HREFUSAL_after_repair"]
    parent = node["HREFUSAL_honest_parent"]
    b_r, b_ok = close(before, "0.125")
    a_r, a_ok = close(after, "0.208")
    p_r, p_ok = close(parent, "0.438")
    return dict(
        found_value=f"{b_r} -> {a_r} (parent {p_r})",
        ci=None,
        n=1,
        source_file=STAGE3_V2_JSON,
        json_key="forgery.forgery__huihui-Qwen3-0.6B-abl-v2__swap.HREFUSAL_before_edited , "
        ".HREFUSAL_after_repair , .HREFUSAL_honest_parent",
        reproduced=(b_ok and a_ok and p_ok),
        status="FOUND",
        note="edited=huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2, honest_parent=Qwen/Qwen3-0.6B, "
        "'swap' rank-one repair target.",
    )


add_row(
    "detection_withdrawn",
    "the forged 'swap' repair quotes harmful REFUSAL rate 0.125 -> 0.208, vs the honest parent 0.438",
    "0.125->0.208 vs 0.438",
    "checkpoint",
    "P14_edited",
    _row_forgery_refusal,
)


def _row_forgery_botgap():
    node = get(STAGE3_V2_JSON, ["forgery", "forgery__huihui-Qwen3-0.6B-abl-v2__swap"])
    before = node["detector_before"]["mlp_BOTGAP_min"]
    after = node["detector_after"]["mlp_BOTGAP_min"]
    b_r, b_ok = close(before, "0.012")
    a_r, a_ok = close(after, "0.82")
    return dict(
        found_value=f"{b_r} -> {a_r}",
        ci=None,
        n=1,
        source_file=STAGE3_V2_JSON,
        json_key="forgery.forgery__huihui-Qwen3-0.6B-abl-v2__swap.detector_before.mlp_BOTGAP_min , "
        ".detector_after.mlp_BOTGAP_min",
        reproduced=(b_ok and a_ok),
        status="FOUND",
        note="the 'swap' rank-one repair heals the weight-signature detector (BOTGAP_min) from the "
        "editedmedian range back into the honest range, zero prompts and zero labels.",
    )


add_row(
    "detection_withdrawn",
    "the weight signature (BOTGAP_min) is healed by the forgery repair, 0.012 -> 0.82",
    "0.012->0.82",
    "checkpoint",
    "P14_edited",
    _row_forgery_botgap,
)

# ---------------------------------------------------------------------------
# STEP 1 (shared-subspace anchor, gen_art_experiment_1 + rescored gen_art_evaluation_1)
# ---------------------------------------------------------------------------

STEP1_ANCHOR_JSON = "gen_art_experiment_1/results/step1_anchor.json"
D1_STEP1_JSON = "gen_art_evaluation_1/results/d1_step1.json"


def _row_step1_angle():
    v = get(STEP1_ANCHOR_JSON, ["headline", "mean_first_principal_angle_deg_last_prompt_token"])
    found_r, ok = close(v, "31.1")
    return dict(
        found_value=found_r,
        ci=None,
        n=None,
        source_file=STEP1_ANCHOR_JSON,
        json_key="headline.mean_first_principal_angle_deg_last_prompt_token",
        reproduced=ok,
        status="FOUND",
        note="Qwen3-4B lineage: SafeRL edit vs abliteration edit, last-prompt-token hidden states, "
        f"verdict='{get(STEP1_ANCHOR_JSON, ['headline','verdict'])}'.",
    )


add_row(
    "step1",
    "mean first principal angle between the SafeRL and abliteration edit subspaces",
    "31.1",
    "checkpoint",
    "P17_2",
    _row_step1_angle,
)


def _row_step1_cosine():
    v = get(STEP1_ANCHOR_JSON, ["headline", "mean_cosine_between_mean_difference_vectors"])
    found_r, ok = close(v, "-0.09")
    return dict(
        found_value=found_r,
        ci=None,
        n=None,
        source_file=STEP1_ANCHOR_JSON,
        json_key="headline.mean_cosine_between_mean_difference_vectors",
        reproduced=ok,
        status="FOUND",
        note="",
    )


add_row(
    "step1",
    "mean cosine between the SafeRL and abliteration mean-difference vectors",
    "-0.09",
    "checkpoint",
    "P17_2",
    _row_step1_cosine,
)


def _row_step1_maxcos():
    signed = get(D1_STEP1_JSON, ["headline_numbers", "signed_cos_safe_vs_heretic"])
    v = abs(signed)
    found_r, ok = close(v, "0.20")
    return dict(
        found_value=found_r,
        ci=None,
        n=None,
        source_file=D1_STEP1_JSON,
        json_key="headline_numbers.signed_cos_safe_vs_heretic (abs)",
        reproduced=ok,
        status="FOUND",
        note="D1 rescore (gen_art_evaluation_1) at the pre-registered verdict cell w4_L24-27 (safe_vs_heretic, "
        f"last prompt token), signed cos={signed:.3f}; verdict='{get(D1_STEP1_JSON, ['verdict'])}' -- DIFFERENT "
        "from experiment_1's own step1_anchor.json verdict ('SHARED_SUBSPACE'); see inconsistencies. NOTE: "
        "headline_numbers.max_abs_signed_cos_anywhere_hs_last (0.916) is a DIFFERENT quantity -- per "
        "headline_numbers_provenance it is the positive-control's own max, not a SafeRL-vs-abliteration pair.",
    )


add_row(
    "step1",
    "max |signed cos| anywhere (last prompt token) vs the within-span null p95",
    "0.20 vs 0.41",
    "checkpoint",
    "P17_2",
    _row_step1_maxcos,
)


def _row_step1_null_p95():
    v = get(D1_STEP1_JSON, ["headline_numbers", "null_p95_at_verdict_band"])
    found_r, ok = close(v, "0.41")
    return dict(
        found_value=found_r,
        ci=None,
        n=None,
        source_file=D1_STEP1_JSON,
        json_key="headline_numbers.null_p95_at_verdict_band",
        reproduced=ok,
        status="FOUND",
        note="within-span null p95 at the verdict-selected band (w4_L24-27, safe_vs_heretic).",
    )


add_row(
    "step1",
    "within-span null p95 at the verdict band",
    "0.41",
    "checkpoint",
    "P17_2",
    _row_step1_null_p95,
)


def _row_step1_positive_control():
    abs_cos = get(D1_STEP1_JSON, ["headline_numbers", "positive_control_abs_cos"])
    p95 = get(D1_STEP1_JSON, ["headline_numbers", "positive_control_null_p95"])
    a_r, a_ok = close(abs_cos, "0.92")
    p_r, p_ok = close(p95, "0.72")
    return dict(
        found_value=f"{a_r} > {p_r}",
        ci=None,
        n=None,
        source_file=D1_STEP1_JSON,
        json_key="headline_numbers.positive_control_abs_cos , .positive_control_null_p95",
        reproduced=(a_ok and p_ok),
        status="FOUND",
        note="positive control: mlabonne/Qwen3-4B-abliterated vs DreamFast/qwen3-4b-heretic (two independent "
        "abliterations of the same parent), strongest cell at layer L29.",
    )


add_row(
    "step1",
    "positive control: |cos| between two independent abliterations vs their null p95",
    "0.92 > 0.72",
    "checkpoint",
    "P17_2",
    _row_step1_positive_control,
)

# ---------------------------------------------------------------------------
# GRADER-SIDE REFUSAL + ROSI + Qwen3-0.6B direction-consistent-not-significant
# ---------------------------------------------------------------------------

JUDGE_FRAMING_JSON = "gen_art_experiment_1/results/judge_framing_comparison.json"
JUDGE_GRADES_JSON = "gen_art_experiment_1/results/judge_grades.json"
EXP2_RESULTS_JSON = "gen_art_experiment_2/out/analysis_out.json"


def _row_degenerate_all():
    v = get(JUDGE_FRAMING_JSON, ["frac_strongreject_replies_that_are_the_degenerate_triple_1_1_1"])
    found_r, ok = close(v, "40.5%", scale=100.0)
    return dict(
        found_value=f"{found_r}%",
        ci=None,
        n=get(JUDGE_FRAMING_JSON, ["n_paired_items"]),
        source_file=JUDGE_FRAMING_JSON,
        json_key="frac_strongreject_replies_that_are_the_degenerate_triple_1_1_1",
        reproduced=ok,
        status="FOUND",
        note="StrongREJECT-framed replies that are the degenerate 1,1,1 triple (grader refuses, not the model), "
        "all graded (checkpoint,item) pairs.",
    )


add_row(
    "grader_refusal",
    "grader-side refusal: StrongREJECT degenerate 1,1,1 replies, all items",
    "40.5%",
    "item",
    "P6_hosts",
    _row_degenerate_all,
)


def _row_degenerate_harmful():
    v = get(JUDGE_FRAMING_JSON, ["frac_degenerate_on_harmful"])
    found_r, ok = close(v, "65.9%", scale=100.0)
    return dict(
        found_value=f"{found_r}%",
        ci=None,
        n=get(JUDGE_FRAMING_JSON, ["n_paired_items"]),
        source_file=JUDGE_FRAMING_JSON,
        json_key="frac_degenerate_on_harmful",
        reproduced=ok,
        status="FOUND",
        note="same degenerate-triple rate, restricted to harmful items.",
    )


add_row(
    "grader_refusal",
    "grader-side refusal: StrongREJECT degenerate 1,1,1 replies, harmful items only",
    "65.9%",
    "item",
    "P6_hosts",
    _row_degenerate_harmful,
)


def _row_kappa():
    v = get(JUDGE_GRADES_JSON, ["agreement", "cohens_kappa_refused"])
    found_r, ok = close(v, "0.749")
    return dict(
        found_value=found_r,
        ci=None,
        n=get(JUDGE_GRADES_JSON, ["agreement", "n"]),
        source_file=JUDGE_GRADES_JSON,
        json_key="agreement.cohens_kappa_refused",
        reproduced=ok,
        status="FOUND",
        note=f"Cohen's kappa on the 'refused' label vs secondary grader "
        f"({get(JUDGE_GRADES_JSON, ['agreement','secondary_model'])}), n_usable_pairs="
        f"{get(JUDGE_GRADES_JSON, ['agreement','n_usable_pairs'])}. NOTE: the superseded "
        "logs/RESULTS.session1.md quotes a DIFFERENT kappa (0.456 StrongREJECT-framing / 0.585 "
        "stance-framing) for what it also calls 'Cohen's kappa vs an independent second grader'; "
        "see inconsistencies.",
    )


add_row(
    "grader_refusal",
    "Cohen's kappa (refused label) between the primary and an independent secondary grader",
    "0.749",
    "item",
    "P6_hosts",
    _row_kappa,
)


def _row_rosi(alpha: float, ckpt: str, claimed_delta: str, claimed_ci: tuple, note: str, panel: str):
    def getter():
        rows = get(EXP2_RESULTS_JSON, ["rosi_reversal"])
        row = next(r for r in rows if r["ckpt"] == ckpt and r["rung"] == "F2b_rosi" and r["alpha_multiplier"] == alpha)
        delta = row["paired"]["delta_D2"]
        ci = row["paired"]["delta_D2_ci95"]
        idx = rows.index(row)
        d_r, d_ok = close(delta, claimed_delta)
        ci_ok = abs(ci[0] - claimed_ci[0]) < 0.0006 and abs(ci[1] - claimed_ci[1]) < 0.0006
        return dict(
            found_value=d_r,
            ci=[round(ci[0], 3), round(ci[1], 3)],
            n=row["paired"]["n_harm_pairs"] + row["paired"]["n_twin_pairs"],
            source_file=EXP2_RESULTS_JSON,
            json_key=f"rosi_reversal[{idx}].paired.delta_D2 , .delta_D2_ci95",
            reproduced=(d_ok and ci_ok),
            status="FOUND",
            note=note,
        )

    return getter


add_row(
    "rosi",
    "ROSI two-sided dD2 at x4, Qwen2.5-0.5B-Instruct (ROSI's own Table-1 model)",
    "-0.151",
    "item",
    "P6_hosts",
    _row_rosi(
        4.0,
        "Qwen/Qwen2.5-0.5B-Instruct",
        "-0.151",
        (-0.233, -0.065),
        "own-evaluation (harm refusal) IMPROVES while the two-sided (paired, harm+benign-twin) metric REVERSES.",
        "P6_hosts",
    ),
)
add_row(
    "rosi",
    "ROSI two-sided dD2 at x4, Qwen3-0.6B, labelled 'direction-consistent, not significant'",
    "-0.081",
    "item",
    "P6_hosts",
    _row_rosi(
        4.0,
        "Qwen/Qwen3-0.6B",
        "-0.081",
        (-0.176, 0.017),
        "CI crosses 0 (upper bound +0.017): direction matches the Qwen2.5-0.5B-Instruct reversal but is "
        "not itself statistically significant.",
        "P6_hosts",
    ),
)

# ---------------------------------------------------------------------------
# run() / target_discrepancy / inconsistencies
# ---------------------------------------------------------------------------


def build_target_discrepancy() -> dict:
    src = PIPELINE2_PY
    text = src.read_text()
    m = re.search(r'"two_sided":\s*(\([^\n]*?\))\s*if', text)
    formula_found = m.group(1).strip() if m else None
    # Evaluate the registered pipeline behaviour directly from the extracted
    # formula: hc = harmful_compliance, fr = false_refusal.
    hc_blanket, fr_blanket = 0.0, 1.0  # a blanket refuser: never complies, always refuses
    two_sided_blanket = (1 - hc_blanket) * (1 - fr_blanket)
    balanced_blanket = 0.5 * (1 - hc_blanket) + 0.5 * (1 - fr_blanket)
    rel = str(src.relative_to(ITER2_ROOT))
    return {
        "claim_text": "The registered two-sided target scores a blanket refuser as 0, not 0.5 as the "
        "iter-3 hypothesis text states; a BALANCED variant gives 0.5.",
        "source_file": rel,
        "json_key": "function two_sided_targets(): out[slug]['two_sided'] formula (source code, not JSON)",
        "formula_found_in_source": formula_found,
        "formula_expected": "(1 - hc) * (1 - fr)",
        "formula_matches": formula_found == "(1 - hc) * (1 - fr)",
        "blanket_refuser_two_sided_score": two_sided_blanket,
        "blanket_refuser_two_sided_expected": 0.0,
        "blanket_refuser_two_sided_reproduced": two_sided_blanket == 0.0,
        "balanced_variant_formula": "0.5*(1-hc) + 0.5*(1-fr)",
        "blanket_refuser_balanced_score": balanced_blanket,
        "blanket_refuser_balanced_expected": 0.5,
        "blanket_refuser_balanced_reproduced": balanced_blanket == 0.5,
        "note": "hc=harmful_compliance (mean score on harmful items), fr=false_refusal (refusal rate on "
        "benign_alarming XSTest items). A checkpoint that refuses everything has hc=0 (never complies) "
        "and fr=1 (refuses even the alarming-but-benign items), so two_sided=(1-0)*(1-1)=0. The BALANCED "
        "0.5*(1-hc)+0.5*(1-fr) variant instead averages the two terms and gives 0.5 for the same blanket "
        "refuser.",
    }


def build_inconsistencies() -> list[dict]:
    out = []

    # (1) crossover_k=1 headline vs the LOLO-BA reversal by k=64.
    curves = get(PROMPT_BUDGET_JSON, ["curves"])
    c1 = next(c for c in curves if c["k"] == 1)
    c64 = next(c for c in curves if c["k"] == 64)
    lead_at_1 = c1["blackbox_lolo_ba_2way"]["mean"] - c1["internal_lolo_ba_2way"]["mean"]
    lead_at_64 = c64["blackbox_lolo_ba_2way"]["mean"] - c64["internal_lolo_ba_2way"]["mean"]
    out.append(
        {
            "headline_sentence": "RESULTS.md / DIGEST.md: 'crossover k by two-way LOLO BA (primary) = 1' "
            "(gen_art_experiment_1/results/prompt_budget.json: crossover_k_by_lolo_ba_2way=1).",
            "table_value": f"curves[k=1] black-box-minus-internal LOLO BA = {lead_at_1:+.3f} (black-box ahead); "
            f"curves[k=64] black-box-minus-internal LOLO BA = {lead_at_64:+.3f} "
            f"({'internal ahead again' if lead_at_64 < 0 else 'black-box still ahead'}).",
            "source_file": PROMPT_BUDGET_JSON,
            "json_key": "curves[k=1 and k=64].blackbox_lolo_ba_2way.mean , .internal_lolo_ba_2way.mean",
            "issue": "a single scalar 'crossover_k=1' reports only the FIRST k at which black-box overtakes "
            "internal by LOLO BA; the full curve is non-monotonic and internal is back ahead by k=64 "
            "(the row 'LOLO BA 0.724 vs 0.445 at k=1 and 0.571 vs 0.592 at k=64' makes this explicit, but "
            "the single crossover_k headline number does not).",
        }
    )

    # (2) Step 1 verdict flip between gen_art_experiment_1 (own analysis) and
    # the gen_art_evaluation_1 rescore.
    v1 = get(STEP1_ANCHOR_JSON, ["headline", "verdict"])
    v2 = get(D1_STEP1_JSON, ["verdict"])
    out.append(
        {
            "headline_sentence": f"gen_art_experiment_1/results/step1_anchor.json headline.verdict = {v1!r}",
            "table_value": f"gen_art_evaluation_1/results/d1_step1.json verdict = {v2!r}",
            "source_file": f"{STEP1_ANCHOR_JSON} vs {D1_STEP1_JSON}",
            "json_key": "headline.verdict vs verdict",
            "issue": "experiment_1's own step-1 analysis reports SHARED_SUBSPACE for the SafeRL-vs-abliteration "
            "edit comparison; the independent iter-2 evaluation rescore (D1, different band-selection and null "
            "procedure) reports the opposite verdict, DIFFERENT_SUBSPACES, at the pre-registered selection rule. "
            "The mandatory numbers (31.1 deg / cos -0.09) are from the SHARED_SUBSPACE analysis; the mandatory "
            "(0.20 vs 0.41, 0.92>0.72) numbers are from the DIFFERENT_SUBSPACES rescore that supersedes it.",
        }
    )

    # (3) Grader kappa: superseded session-1 number vs current judge_grades.json.
    kappa_now = get(JUDGE_GRADES_JSON, ["agreement", "cohens_kappa_refused"])
    out.append(
        {
            "headline_sentence": "gen_art_experiment_1/logs/RESULTS.session1.md: \"Cohen's kappa vs an "
            "independent second grader | 0.456 (StrongREJECT) | 0.585 (stance)\" -- explicitly marked "
            "superseded ('kept for provenance') by the current RESULTS.md.",
            "table_value": f"gen_art_experiment_1/results/judge_grades.json agreement.cohens_kappa_refused "
            f"= {kappa_now:.3f}",
            "source_file": "gen_art_experiment_1/logs/RESULTS.session1.md vs "
            "gen_art_experiment_1/results/judge_grades.json",
            "json_key": "(prose table) vs agreement.cohens_kappa_refused",
            "issue": "three different numeric values (0.456, 0.585, 0.749) have all been called 'Cohen's kappa "
            "vs an independent grader' for this panel across the run's history; the auto-generated current "
            "RESULTS.md/DIGEST.md drop the statistic entirely, so judge_grades.json is the only live source.",
        }
    )

    # (4) stage3_analysis.json (v1, WITHDRAWN, n=0 graded) vs stage3_v2.json
    # (current, EDIT_NOT_RISK, n=14 graded) -- same claim, superseded file still on disk.
    verdict_v1 = get("gen_art_experiment_3/results/stage3_analysis.json", ["VERDICT"])
    n_v1 = get("gen_art_experiment_3/results/stage3_analysis.json", ["n_edited_graded"])
    # stage3_v2.json carries no single top-level VERDICT key; RESULTS.md's headline sentence
    # ("VERDICT: EDIT_NOT_RISK") is the current, superseding claim for the same question.
    n_v2 = get(STAGE3_V2_JSON, ["primary_endpoint", "n_edited_graded"])
    out.append(
        {
            "headline_sentence": f"gen_art_experiment_3/results/stage3_analysis.json VERDICT={verdict_v1!r}, "
            f"n_edited_graded={n_v1}",
            "table_value": f"gen_art_experiment_3/results/stage3_v2.json (current) "
            f"primary_endpoint.n_edited_graded={n_v2}, RESULTS.md headline VERDICT='EDIT_NOT_RISK'",
            "source_file": "gen_art_experiment_3/results/stage3_analysis.json vs "
            "gen_art_experiment_3/results/stage3_v2.json",
            "json_key": "VERDICT , n_edited_graded (v1) vs primary_endpoint.n_edited_graded (v2)",
            "issue": "stage3_analysis.json is a stale v1 artifact (a CPU-starved session that graded 0 "
            "checkpoints and self-reports VERDICT=WITHDRAWN) still present on disk beside the current, "
            "superseding stage3_v2.json (14 graded checkpoints, VERDICT=EDIT_NOT_RISK); citing the wrong file "
            "would silently reproduce a withdrawn n=0 result.",
        }
    )

    # (5) A field literally named 'max ... anywhere' is not the max over the
    # claim's own comparison; its own provenance note says so.
    max_field = get(D1_STEP1_JSON, ["headline_numbers", "max_abs_signed_cos_anywhere_hs_last"])
    verdict_pair_abs = abs(get(D1_STEP1_JSON, ["headline_numbers", "signed_cos_safe_vs_heretic"]))
    provenance_note = get(D1_STEP1_JSON, ["headline_numbers_provenance", "note"])
    out.append(
        {
            "headline_sentence": f"headline_numbers.max_abs_signed_cos_anywhere_hs_last = {max_field:.3f}",
            "table_value": f"headline_numbers.signed_cos_safe_vs_heretic (abs) at the verdict cell "
            f"w4_L24-27 = {verdict_pair_abs:.3f}",
            "source_file": D1_STEP1_JSON,
            "json_key": "headline_numbers.max_abs_signed_cos_anywhere_hs_last vs "
            "headline_numbers.signed_cos_safe_vs_heretic",
            "issue": "despite its name, max_abs_signed_cos_anywhere_hs_last is NOT the maximum overlap for the "
            "SafeRL-vs-abliteration claim; per headline_numbers_provenance.note it is the positive control's "
            f"own strongest cell (\"{provenance_note.split('positive_control_*')[-1].strip() if 'positive_control_*' in provenance_note else provenance_note[-140:]}\"). "
            "A reader pattern-matching on the field name alone would wrongly report 0.916, not the 0.201 the "
            "DIFFERENT_SUBSPACES verdict is actually based on.",
        }
    )

    return out


def run() -> dict:
    logger.info("building numbers ledger from iter_2 artifacts")
    logger.info(f"iter_2 source root: {ITER2_ROOT}")

    target_discrepancy = build_target_discrepancy()
    inconsistencies = build_inconsistencies()

    n_rows = len(ROWS)
    n_found = sum(1 for r in ROWS if r["status"] == "FOUND")
    n_reproduced = sum(1 for r in ROWS if r["reproduced"] is True)
    n_not_found = sum(1 for r in ROWS if r["status"] == "NOT_FOUND_IN_ARTIFACTS")

    mandatory_check = {
        "race_beat_null": any(r["row_group"] == "race" and r["claimed_value"] == "3/50" for r in ROWS),
        "direction_nulls_three_counts": sum(
            1 for r in ROWS if r["row_group"] == "direction_nulls"
        )
        == 3,
        "prompt_budget_both_scales": sum(1 for r in ROWS if r["row_group"] == "prompt_budget") == 4,
        "weights_block": sum(1 for r in ROWS if r["row_group"] == "weights") >= 8,
        "detection_withdrawn_block": sum(1 for r in ROWS if r["row_group"] == "detection_withdrawn") == 4,
        "step1_block": sum(1 for r in ROWS if r["row_group"] == "step1") == 5,
        "grader_refusal_and_rosi_block": sum(
            1 for r in ROWS if r["row_group"] in ("grader_refusal", "rosi")
        )
        == 5,
    }

    ledger = {
        "generated_by": "ledger.py",
        "iter2_source_root": str(ITER2_ROOT),
        "rows": ROWS,
        "target_discrepancy": target_discrepancy,
        "inconsistencies": inconsistencies,
        "summary": {
            "n_rows": n_rows,
            "n_found": n_found,
            "n_reproduced": n_reproduced,
            "n_not_found": n_not_found,
            "n_non_reproduced_but_found": sum(
                1 for r in ROWS if r["status"] == "FOUND" and r["reproduced"] is False
            ),
        },
        "mandatory_row_check": mandatory_check,
    }

    out_path = WORKSPACE / "numbers_ledger.json"
    out_path.write_text(json.dumps(ledger, indent=2, allow_nan=False, default=str))
    logger.info(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
    logger.info(
        f"summary: n_rows={n_rows} n_found={n_found} n_reproduced={n_reproduced} n_not_found={n_not_found}"
    )
    if not all(mandatory_check.values()):
        logger.warning(f"mandatory_row_check has failures: {mandatory_check}")
    return ledger


if __name__ == "__main__":
    run()

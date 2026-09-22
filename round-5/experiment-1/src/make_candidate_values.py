#!/usr/bin/env python3
"""make_candidate_values.py -- flattens GPU5-tier rows/<slug>.json into a LONG join-ready table.

Writes WS/candidate_values_gpu.json: one record per (repo, candidate, variant), whose per-record
key set is EXACTLY IT4/candidate_values_live.json's key set (checked programmatically against
IT4_KEY_SET below, copied from a live read of that file -- see key_set_selfcheck()) plus two new
keys: "setA" (bool) and "coverage_reason" (str|None).

API (imported by the iter-5 orchestrator's freeze_setA.py, and by tests/test_analysis.py):
    flatten_row(row: dict) -> list[dict]
        Pure function of the ONE row dict given (a parsed rows/<slug>.json, GPU5 schema: row["candidates"]
        [NAME] = {"value","undefined","reason","pole_refuse","pole_comply","k8","offset_late","offset_mid",
        "null_mean","null_median","null_p95","seconds_own", ...extra}). Reads NO other file (importing this
        module has no side effects: the CLI is guarded behind `if __name__ == "__main__":`).

CLI:
    venv_gpu/bin/python make_candidate_values.py                  # rows/*.json -> candidate_values_gpu.json
    venv_gpu/bin/python make_candidate_values.py --from-it4        # IT4 rows/*.json (old candidate ids),
                                                                     for analyze_gpu.py --it4-dry-run
    venv_gpu/bin/python make_candidate_values.py --rows-glob '...' --out '...'
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
IT4_DEFAULT = Path(
    "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_4/gen_art/gen_art_experiment_1"
)

# =====================================================================================================
# Key-set contract (IT4/candidate_values_live.json's own key set, verified against a live read of that
# file by key_set_selfcheck() at CLI time -- this literal is the frozen ground truth the diff is checked
# against, not a live file read from inside flatten_row).
# =====================================================================================================
IT4_KEY_SET: frozenset[str] = frozenset({
    "repo", "resolved_sha", "family", "lineage", "class", "n_params", "stratum", "candidate_id",
    "variant", "value", "undefined", "undefined_reason", "seconds", "device", "tier",
    "screen16_file_sha256", "prereg_hash", "slug", "candidate", "readout", "itemset", "prereg_sha256",
})
NEW_KEYS: frozenset[str] = frozenset({"setA", "coverage_reason"})
GPU_KEY_SET: frozenset[str] = IT4_KEY_SET | NEW_KEYS

# GPU5 candidate registry (PREREG.json definitions block; C3/C7/C8/C9/C16/C11-if-slow dropped per
# PREREG.dropped_candidates).
CANDIDATE_NAMES: tuple[str, ...] = (
    "C1", "C2", "C1n_cd", "C1n_os", "C6", "C6_insample", "C6_lens", "C10", "C12", "C12r", "C13",
    "C13_rank", "C13_logit", "C15_erank", "C15_disp", "C11", "logit_gap", "refusal_mass",
    "logit_gap_level", "refusal_mass_level", "AMS_published", "AMS_mean3", "AMS_cf_layer",
    "AMS_cf_sweep", "AMS_screen16",
)

# variant name -> the scalar field it reads off a candidate's own dict
VARIANT_KEYS: dict[str, str] = {
    "primary": "value",
    "pole_refuse": "pole_refuse",
    "pole_comply": "pole_comply",
    "k8": "k8",
    "offset_late": "offset_late",
    "offset_mid": "offset_mid",
    "null_mean": "null_mean",
    "null_median": "null_median",
    "null_p95": "null_p95",
    "eps_0.02": "eps_0.02",
    "eps_0.05": "eps_0.05",
    "eps_0.1": "eps_0.1",
}

# readout="mass" for logit-gap/refusal-mass style bars, "none" otherwise -- mirrors IT4
# analyze_live.py:build_candidate_values_long's own convention: readout = "mass" if cid in
# ("C1", "C2", "C16", "logit_gap", "refusal_mass") else "none" (IT4 has no oracle variant in GPU5).
# C16 is dropped in GPU5 (PREREG.dropped_candidates), so the GPU5 mass set is the surviving subset.
MASS_READOUT_CANDIDATES: frozenset[str] = frozenset({"C1", "C2", "logit_gap", "refusal_mass"})

# PREREG.json panel.setA, copied verbatim (frozen 2026-09-21T21:52:31+00:00) as a Python literal so
# flatten_row() never has to open PREREG.json (or any file besides the row it is given) to decide
# whether a repo is a Set A checkpoint.
PANEL_SETA_REPOS: frozenset[str] = frozenset({
    "HuggingFaceTB/SmolLM2-1.7B-Instruct", "utter-project/EuroLLM-1.7B-Instruct",
    "unsloth/gemma-2-2b-it", "IlyaGusev/gemma-2-2b-it-abliterated",
    "Robust-Decoding/gemma2-2b-it-hh-dpo-harmless-step-6000", "Qwen/Qwen2.5-3B-Instruct",
    "HuggingFaceTB/SmolLM3-3B", "unsloth/Llama-3.2-3B-Instruct",
    "huihui-ai/Llama-3.2-3B-Instruct-abliterated", "microsoft/Phi-4-mini-instruct",
    "lunahr/Phi-4-mini-instruct-abliterated", "microsoft/Phi-3.5-mini-instruct",
})


def _is_scalar_or_none(v: Any) -> bool:
    return v is None or isinstance(v, (int, float, bool))


def _flag_codes(row: dict) -> str | None:
    flags = row.get("flags") or []
    codes = [f.get("code") for f in flags if isinstance(f, dict) and f.get("code")]
    return "; ".join(codes) if codes else None


# =====================================================================================================
# GPU5 row -> long records (the API the orchestrator's freeze_setA.py imports)
# =====================================================================================================
def flatten_row(row: dict) -> list[dict]:
    """Turn ONE GPU5-tier row dict into its long-format records. Pure function of `row`: reads nothing
    else (setA membership and readout class are decided from module-level literals, not file I/O)."""
    repo = row.get("repo")
    cdicts = row.get("candidates") or {}
    seta_field = row.get("setA")
    seta = bool(seta_field) if isinstance(seta_field, bool) else (repo in PANEL_SETA_REPOS)
    row_coverage_reason = row.get("coverage_reason")
    flag_codes = _flag_codes(row)
    compute = row.get("compute") or {}
    device = compute.get("device") or row.get("device") or "cpu"

    records: list[dict] = []
    for name in CANDIDATE_NAMES:
        cd = cdicts.get(name)
        if not isinstance(cd, dict):
            continue
        for variant, key in VARIANT_KEYS.items():
            if key not in cd:
                continue  # this variant does not apply to this candidate/model at all
            v = cd.get(key)
            if not _is_scalar_or_none(v):
                continue  # defensive: not a scalar (e.g. a stray list), never emitted as a value
            if variant == "primary":
                undefined = bool(cd.get("undefined", v is None))
                reason = cd.get("reason")
            else:
                undefined = v is None
                reason = cd.get(f"{variant}_reason")
            coverage_reason = row_coverage_reason if row_coverage_reason is not None else (
                reason if undefined else flag_codes)
            records.append({
                "repo": repo,
                "resolved_sha": row.get("resolved_sha"),
                "family": row.get("family"),
                "lineage": row.get("lineage"),
                "class": row.get("class"),
                "n_params": row.get("n_params"),
                "stratum": row.get("stratum"),
                "candidate_id": name,
                "variant": variant,
                "value": (None if v is None else float(v)),
                "undefined": bool(undefined),
                "undefined_reason": reason,
                "seconds": (cd.get("seconds_own") if variant == "primary" else None),
                "device": device,
                "tier": "gpu5",
                "screen16_file_sha256": row.get("screen16_file_sha256"),
                "prereg_hash": row.get("prereg_hash"),
                "slug": (repo or "").replace("/", "__"),
                "candidate": name,
                "readout": "mass" if name in MASS_READOUT_CANDIDATES else "none",
                "itemset": "S16_k8" if variant == "k8" else "S16",
                "prereg_sha256": row.get("prereg_hash"),
                "setA": seta,
                "coverage_reason": coverage_reason,
            })
    return records


# =====================================================================================================
# --from-it4: build the SAME long format out of IT4's old-schema rows, for analyze_gpu.py --it4-dry-run
# =====================================================================================================
def _percentile(vals: list[float], pct: float) -> float:
    if not vals:
        return float("nan")
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    k = (pct / 100.0) * (len(s) - 1)
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    frac = k - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _it4_null_stats(cd: dict) -> dict[str, float]:
    """Per the task spec: in --from-it4 mode, null_mean/null_median/null_p95 are COMPUTED from each
    row's candidates[NAME]['null_values'] (IT4 rows carry that 20-value list; see e.g.
    IT4/rows/AIPlans__TinyLlama-1.1B-IPO-PKU-SafeRLHF.json candidates.C2.null_values)."""
    nv = cd.get("null_values")
    if isinstance(nv, list) and nv:
        arr = [float(x) for x in nv if isinstance(x, (int, float))]
        if arr:
            return {"null_mean": sum(arr) / len(arr), "null_median": statistics.median(arr),
                     "null_p95": _percentile(arr, 95.0)}
    if isinstance(cd.get("null_p95"), (int, float)):
        return {"null_p95": float(cd["null_p95"])}
    return {}


def flatten_row_it4(row: dict) -> list[dict]:
    """Same long-format schema as flatten_row(), built from an IT4 (old-schema) row instead. Only used
    by the --from-it4 dry-run path; not part of the imported API contract."""
    repo = row.get("repo")
    cdicts = row.get("candidates") or {}
    seta = repo in PANEL_SETA_REPOS
    csecs = row.get("candidate_seconds") or {}
    compute = row.get("compute") or {}
    device = compute.get("device", "cpu")

    records: list[dict] = []
    for name, cd in cdicts.items():
        if not isinstance(cd, dict):
            continue
        variants: dict[str, tuple[Any, bool, str | None]] = {
            "primary": (cd.get("value"), bool(cd.get("undefined", cd.get("value") is None)), cd.get("reason")),
            "pole_refuse": (cd.get("pole_refuse"), cd.get("pole_refuse") is None, cd.get("pole_refuse_reason")),
            "pole_comply": (cd.get("pole_comply"), cd.get("pole_comply") is None, cd.get("pole_comply_reason")),
            "k8": (cd.get("k8"), cd.get("k8") is None, cd.get("k8_reason")),
        }
        for k, v in _it4_null_stats(cd).items():
            variants[k] = (v, False, None)
        for variant, (v, undefined, reason) in variants.items():
            if not _is_scalar_or_none(v):
                continue
            records.append({
                "repo": repo,
                "resolved_sha": row.get("resolved_sha"),
                "family": row.get("family"),
                "lineage": row.get("lineage"),
                "class": row.get("class"),
                "n_params": row.get("n_params"),
                "stratum": row.get("stratum"),
                "candidate_id": name,
                "variant": variant,
                "value": (None if v is None else float(v)),
                "undefined": bool(undefined),
                "undefined_reason": reason,
                "seconds": (csecs.get(name) if variant == "primary" else None),
                "device": device,
                "tier": "live",  # honestly labelled: this came from IT4's own (pre-GPU5) tier
                "screen16_file_sha256": row.get("screen16_file_sha256"),
                "prereg_hash": row.get("prereg_hash"),
                "slug": (repo or "").replace("/", "__"),
                "candidate": name,
                "readout": "mass" if name in MASS_READOUT_CANDIDATES else "none",
                "itemset": "S16_k8" if variant == "k8" else "S16",
                "prereg_sha256": row.get("prereg_hash"),
                "setA": seta,
                "coverage_reason": (reason if undefined else None),
            })
    return records


def key_set_selfcheck(records: list[dict]) -> None:
    """Programmatic key-set assertion: the diff against IT4_KEY_SET must be empty apart from setA and
    coverage_reason. Fails loudly (raises) otherwise -- never silently drops or renames a key."""
    if not records:
        return
    seen = set(records[0].keys())
    for r in records[1:]:
        if set(r.keys()) != seen:
            raise AssertionError(f"inconsistent key set across records: {set(r.keys())} != {seen}")
    extra = seen - GPU_KEY_SET
    missing = GPU_KEY_SET - seen
    if extra or missing:
        raise AssertionError(
            f"candidate_values_gpu.json key-set mismatch vs IT4_KEY_SET+{{setA,coverage_reason}}: "
            f"extra={sorted(extra)} missing={sorted(missing)}")
    against_it4_only = seen - IT4_KEY_SET
    if against_it4_only != NEW_KEYS:
        raise AssertionError(f"diff against IT4_KEY_SET is not exactly {{setA,coverage_reason}}: "
                              f"got {sorted(against_it4_only)}")


def _load_rows(rows_glob: str, base: Path) -> list[dict]:
    from loguru import logger
    paths = sorted(base.glob(rows_glob)) if not Path(rows_glob).is_absolute() else sorted(Path().glob(rows_glob))
    rows = []
    for p in paths:
        try:
            rows.append(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"skip unreadable row {p}: {e}")
    logger.info(f"loaded {len(rows)} row file(s) from {base / rows_glob}")
    return rows


def _atomic_write(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def main() -> None:
    import sys as _sys
    from loguru import logger
    (WS / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(_sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / "analysis_make_candidate_values.log", rotation="30 MB", level="DEBUG")

    ap = argparse.ArgumentParser()
    ap.add_argument("--rows-glob", default="rows/*.json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--from-it4", action="store_true",
                     help="build the long table from IT4's old-schema rows instead (for "
                          "analyze_gpu.py --it4-dry-run)")
    ap.add_argument("--it4-rows-dir", default=str(IT4_DEFAULT / "rows"))
    a = ap.parse_args()

    if a.from_it4:
        it4_dir = Path(a.it4_rows_dir)
        rows = []
        for p in sorted(it4_dir.glob("*.json")):
            try:
                rows.append(json.loads(p.read_text()))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"skip unreadable IT4 row {p}: {e}")
        logger.info(f"--from-it4: loaded {len(rows)} row(s) from {it4_dir}")
        records = [rec for row in rows for rec in flatten_row_it4(row)]
        out = Path(a.out) if a.out else (WS / "scratch" / "candidate_values_gpu_it4dryrun.json")
    else:
        rows = _load_rows(a.rows_glob, WS)
        records = [rec for row in rows for rec in flatten_row(row)]
        out = Path(a.out) if a.out else (WS / "candidate_values_gpu.json")

    logger.info(f"flattened {len(rows)} row(s) into {len(records)} long-format record(s)")
    try:
        key_set_selfcheck(records)
        logger.info("key-set self-check PASSED (matches IT4_KEY_SET + {setA, coverage_reason})")
    except AssertionError:
        logger.exception("key-set self-check FAILED")
        raise

    out.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(out, records)
    logger.info(f"wrote {out} ({len(records)} records)")


if __name__ == "__main__":
    main()

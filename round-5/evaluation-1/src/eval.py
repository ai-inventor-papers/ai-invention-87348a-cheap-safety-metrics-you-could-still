#!/usr/bin/env python3
"""Iter-5 FINAL evaluation (CPU only, zero LLM spend): the single numbers source for the final paper.

Step 0 provenance gate -> Step 1 screen table -> freeze survivors (sha256) -> Step 2 one-shot confirmation ->
Step 3 must-fix corrections + ledger -> Step 4 mechanism -> Step 5 figures -> eval_out.json.
Run:  .venv/bin/python eval.py            (all steps; resumable, deterministic, seed 20260921)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

import numpy as np
import pandas as pd
from loguru import logger

import data_io as io
import reads as rd
import screen as scr
import stats_core as sc

WS = Path(__file__).resolve().parent
(WS / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs/eval.log", rotation="30 MB", level="DEBUG")

DEVIATIONS: list[dict] = []
NAN = float("nan")


def dev(code: str, detail: str, **kw: Any) -> None:
    DEVIATIONS.append({"code": code, "detail": detail, **kw})
    logger.warning(f"DEVIATION {code}: {detail}")


def clean(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return [clean(v) for v in o.tolist()]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def wjson(name: str, obj: Any) -> Path:
    p = WS / name
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(clean(obj), indent=1, ensure_ascii=False))
    tmp.replace(p)
    logger.info(f"wrote {name} ({p.stat().st_size/1e3:.1f} kB)")
    return p


# =================================================================================================
# Step 0 - inputs manifest + provenance gate
# =================================================================================================
def inputs_manifest(found: dict[str, list[Path]]) -> dict:
    man: dict[str, Any] = {"generated_utc": datetime.now(timezone.utc).isoformat(), "iter5": {}, "fixed": {}}
    for k, paths in found.items():
        if not paths:
            man["iter5"][k] = f"MISSING_{k}"
            dev(f"MISSING_{k}", f"no iter-5 file for {k} under {io.I5}/*/")
        else:
            man["iter5"][k] = [io.file_record(p) for p in paths]
    fixed = {"iter4_PREREG": io.I4E / "PREREG.json", "iter4_candidate_values_live": io.I4E / "candidate_values_live.json",
             "iter4_candidates_live": io.I4E / "candidates_live.json", "iter4_labels_map": io.I4E / "labels_map.json",
             "iter4_posthoc_live": io.I4E / "posthoc_live.json", "iter4_c2_depth_sweep": io.I4E / "c2_depth_sweep.json",
             "iter4_matched_null": io.I4E / "matched_null.json", "iter4_rosi_128tok": io.I4E / "rosi_128tok.json",
             "iter4_numbers_ledger_v2": io.I4V / "numbers_ledger_v2.json", "iter4_corrections": io.I4V / "corrections.json",
             "iter3_power": io.I3V / "power.json", "iter3_step1_reconciled": io.I3V / "step1_reconciled.json",
             "iter3_full_data_out": io.I3D / "full_data_out.json",
             "iter2_ladder_full_method_out": io.I2L / "full_method_out.json",
             "iter2_weights_full_method_out": io.I2W / "full_method_out.json"}
    for k, p in fixed.items():
        man["fixed"][k] = io.file_record(p) if p.exists() else f"MISSING {p}"
    man["fixed"]["iter4_rows_dir"] = {"path": str(io.I4E / "rows"),
                                      "n_files": len(list((io.I4E / "rows").glob("*.json"))),
                                      "sha256_of_sorted_file_hashes": hashlib.sha256("".join(
                                          io.sha256_file(p) for p in sorted((io.I4E / "rows").glob("*.json"))).encode()).hexdigest()}
    return man


def _ts_inside(obj: Any) -> list[str]:
    out = []
    def rec(o: Any, depth: int = 0) -> None:
        if depth > 3:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("created_utc", "written_utc", "generated_utc", "timestamp_utc", "frozen_utc") and isinstance(v, str):
                    out.append(v)
                rec(v, depth + 1)
        elif isinstance(o, list):
            for v in o[:5]:
                rec(v, depth + 1)
    rec(obj)
    return out


def provenance(found: dict[str, list[Path]], df: pd.DataFrame, reads: dict, i5vals: pd.DataFrame) -> dict:
    pv: dict[str, Any] = {}
    h = io.sha256_file(io.I4E / "PREREG.json")
    pv["a_iter4_prereg"] = {"recomputed_sha256": h, "expected": io.PREREG4_HASH, "match": h == io.PREREG4_HASH}
    recs = io.load_json(io.I4E / "candidate_values_live.json")
    stamped = sorted({r.get("prereg_hash") for r in recs})
    pv["a_iter4_prereg"]["prereg_hash_stamped_on_candidate_values_live"] = stamped
    pv["a_iter4_prereg"]["all_records_match"] = stamped == [io.PREREG4_HASH]
    pv["a_iter5_prereg"] = []
    for p in found["prereg5"]:
        rec = {"path": str(p), "recomputed_sha256": io.sha256_file(p)}
        cands = [q for q in found["prereg5_sha256"] if q.parent == p.parent]
        if cands:
            txt = cands[0].read_text().split()
            rec["recorded"] = txt[0] if txt else None
            rec["match"] = rec["recorded"] == rec["recomputed_sha256"]
        else:
            rec["match"] = None
            rec["note"] = "no hash file beside it"
        pv["a_iter5_prereg"].append(rec)
    if not found["prereg5"]:
        pv["a_iter5_prereg"] = "MISSING_prereg5 - no iter-5 PREREG found"
    # (b) values_setA hash
    pv["b_values_setA"] = []
    for p in found["values_setA"]:
        rec = {"path": str(p), "recomputed_sha256": io.sha256_file(p)}
        hs = [q for q in found["values_setA_sha256"] if q.parent == p.parent]
        if hs:
            tok = hs[0].read_text().split()
            rec["recorded"] = tok[0] if tok else None
            rec["match"] = rec["recorded"] == rec["recomputed_sha256"]
            rec["hash_file_content_head"] = hs[0].read_text()[:300]
        else:
            try:
                obj = io.load_json(p)
                rec["recorded_inside"] = obj.get("sha256") if isinstance(obj, dict) else None
            except (json.JSONDecodeError, OSError):
                rec["recorded_inside"] = None
            rec["match"] = None
        pv["b_values_setA"].append(rec)
    if not found["values_setA"]:
        pv["b_values_setA"] = "MISSING_values_setA"
    # (c) blindness timestamps
    c: dict[str, Any] = {}
    if not found["confirm_labels"]:
        c = {"status": "NOT APPLICABLE - confirm_labels.json does not exist; no Set A label was ever opened",
             "pass": None}
    else:
        vs = [p for p in found["values_setA"]]
        inside_v = sum((_ts_inside(io.load_json(p)) for p in vs), [])
        inside_l = sum((_ts_inside(io.load_json(p)) for p in found["confirm_labels"]), [])
        mt_v = [p.stat().st_mtime for p in vs]
        mt_l = [p.stat().st_mtime for p in found["confirm_labels"]]
        git = {}
        for p in vs + found["confirm_labels"]:
            try:
                r = subprocess.run(["git", "-C", str(p.parent), "log", "-1", "--format=%cI", "--", p.name],
                                   capture_output=True, text=True, timeout=20)
                git[str(p)] = r.stdout.strip() or None
            except (subprocess.SubprocessError, OSError):
                git[str(p)] = None
        c = {"inside_values": inside_v, "inside_labels": inside_l, "git": git,
             "mtime_values_utc": [datetime.fromtimestamp(t, timezone.utc).isoformat() for t in mt_v],
             "mtime_labels_utc": [datetime.fromtimestamp(t, timezone.utc).isoformat() for t in mt_l]}
        if inside_v and inside_l:
            c["basis"], c["pass"] = "timestamps inside files", max(inside_v) < min(inside_l)
        elif mt_v and mt_l:
            c["basis"], c["pass"] = "filesystem mtime", max(mt_v) < min(mt_l)
        else:
            c["basis"], c["pass"] = "none", False
    pv["c_blindness_timestamps"] = c
    # (d) value equality
    d: dict[str, Any] = {"checks": []}
    if i5vals is None or i5vals.empty or not found["values_setA"]:
        d["status"] = "NOT APPLICABLE - no iter-5 Set A value file; the Set A values used here ARE the iter-4 rows " \
                      "(written with graded=false in iteration 4), so equality holds by construction"
        d["pass"] = None
    else:
        sa = i5vals[i5vals["file"].isin([str(p) for p in found["values_setA"]])]
        sa = sa[sa["variant"].astype(str).isin(["primary", "value", "plain"])]
        repo_idx = {r: i for i, r in enumerate(df["repo"])}
        allok = True
        for can_raw, rid in (("C1", "C1"), ("C2", "C2"), ("logit_gap", "logit_gap"), ("refusal_mass", "refusal_mass"),
                             ("C2n", "C2n"), ("C2ts", "C2ts"), ("C17", "C17")):
            sub = sa[sa["canon"] == can_raw] if can_raw in ("C2n", "C2ts", "C17") else \
                sa[sa["candidate_id"].astype(str) == can_raw]
            for _, it in sub.iterrows():
                i = repo_idx.get(it["repo"])
                if i is None or it["value"] is None:
                    continue
                mine = reads[rid]["values"][i] if rid not in ("C2n", "C2ts", "C17") else reads.get(rid + "_eval", reads[rid])["values"][i]
                ok = bool(np.isfinite(mine) and abs(float(it["value"]) - mine) <= 1e-9 * max(1, abs(mine)))
                tol = 1e-9 if rid in ("C1", "C2", "logit_gap", "refusal_mass") else 1e-6
                ok = bool(np.isfinite(mine) and abs(float(it["value"]) - mine) <= tol * max(1, abs(mine)))
                allok &= ok
                d["checks"].append({"repo": it["repo"], "read": rid, "file_value": it["value"], "row_value": mine,
                                    "equal": ok, "tol": tol})
        d["pass"] = bool(allok) if d["checks"] else None
        d["n_checks"] = len(d["checks"])
    pv["d_value_equality"] = d
    # (e) no Set A label in any iter-3/iter-4 file
    e: dict[str, Any] = {}
    labels = io.load_json(io.I4E / "labels_map.json")["rows"]
    e["iter4_labels_map_setA_BALANCED"] = {r: (labels.get(r) or {}).get("BALANCED") for r in io.SET_A}
    e["iter4_rows_setA_graded_flag"] = {r: bool(df.loc[df["repo"] == r, "graded"].iloc[0]) for r in io.SET_A}
    try:
        full = io.load_json(io.I3D / "full_data_out.json")
        dpo = next((d_ for d_ in full["datasets"] if d_["dataset"] == "dev_panel_outcome"), None)
        labelled3, present3 = set(), set()
        for ex in (dpo["examples"] if dpo else []):
            repo = ex.get("metadata_repo")
            if repo not in io.SET_A:
                continue
            present3.add(repo)
            out_ = str(ex.get("output", ""))
            graded = ex.get("metadata_status") == "graded"
            try:
                float(out_)
                numeric = True
            except ValueError:
                numeric = False
            if graded or numeric:
                labelled3.add(repo)
        e["iter3_dev_panel_outcome_setA_rows_present"] = sorted(present3)
        e["iter3_dev_panel_outcome_setA_rows"] = sorted(labelled3)
        e["iter3_dev_panel_outcome_rule"] = ("a Set A row counts as LABELLED only if metadata_status=='graded' or its "
                                             "output parses as a number; the 12 Set A rows exist in iteration 3 with "
                                             "output 'NA' and a non-graded status, which is the queue, not a label")
        del full
    except (OSError, json.JSONDecodeError, KeyError) as ex:
        e["iter3_dev_panel_outcome_setA_rows"] = f"unreadable: {ex}"
    ck = {}
    for r in io.SET_A:
        dd = io.I3D / "results/ckpt" / r.replace("/", "__")
        ck[r] = sorted(x.name for x in dd.iterdir()) if dd.exists() else "no dir"
    e["iter3_results_ckpt"] = ck
    graded_files = {r: [f for f in v if "grade" in f.lower() or f.endswith(".jsonl")] if isinstance(v, list) else []
                    for r, v in ck.items()}
    e["pass"] = bool(all(v is None for v in e["iter4_labels_map_setA_BALANCED"].values())
                     and not any(e["iter4_rows_setA_graded_flag"].values())
                     and (isinstance(e["iter3_dev_panel_outcome_setA_rows"], list)
                          and not e["iter3_dev_panel_outcome_setA_rows"])
                     and not any(graded_files.values()))
    e["iter3_ckpt_grade_like_files"] = graded_files
    pv["e_no_prior_setA_labels"] = e
    blind_fail = (c.get("pass") is False) or (d.get("pass") is False)
    pv["confirmation_blindness"] = "NOT BLIND" if blind_fail else (
        "BLIND (no labels exist yet)" if not found["confirm_labels"] else "BLIND")
    return pv


# =================================================================================================
# Step 1 - screen
# =================================================================================================
REPRO = {"C2_rho": 0.900, "logit_gap_rho": 0.772, "C2_partial": 0.746, "C2_bound": 0.440, "C1_partial": 0.491,
         "behaviour_rho": 0.931, "C2_given_behaviour": 0.315}


def run_screen(df: pd.DataFrame, reads: dict) -> tuple[dict, list[dict]]:
    g = df["graded"].to_numpy()
    gidx = np.where(g)[0]
    gdf = df.iloc[gidx].reset_index(drop=True)
    T = gdf["BALANCED"].to_numpy(float)
    ctx = {"logit_gap_graded": reads["logit_gap"]["values"][gidx],
           "lofo_family_only": sc.lofo_family_only(T, gdf["family"].to_numpy()),
           "lofo_size_only": sc.lofo_spearman(T, gdf["log10_n_params"].to_numpy(float), gdf["family"].to_numpy()),
           "direction_free": rd.DIRECTION_FREE}
    order = rd.LIVE14 + rd.BARS + list(rd.DEAD)
    rows = []
    for rid in order:
        r = reads.get(rid)
        if r is None:
            rows.append({"id": rid, "kind": "bar" if rid in rd.BARS else "internal", "status": "NOT RUN",
                         "definition": rd.DESC.get(rid, rid),
                         "skip_reason": ("AMS_MISSING - no ams_tier1.json found" if rid == "AMS_T1" else
                                         "NOT RUN - needs the iter-5 CPU/GPU tier file, which does not exist"),
                         "verdicts": {"survivor_eligible": False}})
            continue
        t0 = time.perf_counter()
        res = scr.analyse_read(r, gdf, gidx, ctx)
        if rid in rd.DEAD:
            res["status"] = "DEAD - not re-screened"
            res["verdicts"]["survivor_eligible"] = False
            res["verdicts"]["survives"] = False
        rows.append(res)
        logger.info(f"screen {rid:12s} n={res.get('n_computed')} rho={res.get('rho_BALANCED')} "
                    f"partial={res.get('partial', {}).get('point')} bound={res.get('partial', {}).get('bound_one_sided_5pct')} "
                    f"({time.perf_counter()-t0:.1f}s)")
    by = {r["id"]: r for r in rows}
    # sanity reproductions
    got = {"C2_rho": by["C2"]["rho_BALANCED"], "logit_gap_rho": by["logit_gap"]["rho_BALANCED"],
           "C2_partial": by["C2"]["partial"]["point"], "C2_bound": by["C2"]["partial"]["bound_one_sided_5pct"],
           "C1_partial": by["C1"]["partial"]["point"], "behaviour_rho": by["behaviour"]["rho_BALANCED"],
           "C2_given_behaviour": by["C2"]["diagnostics"]["increment_over_behaviour"]["point"]}
    repro = {}
    for k, exp in REPRO.items():
        ok = abs(got[k] - exp) <= 0.005
        repro[k] = {"expected": exp, "recomputed": got[k], "match_tol_0.005": ok}
        if not ok:
            dev("REPRO_MISMATCH", f"{k}: expected {exp}, recomputed {got[k]:.4f}; recomputed value used")
    # ranking rule
    elig = [r for r in rows if r.get("verdicts", {}).get("survivor_eligible") and r.get("partial")]
    def key(r: dict) -> tuple:
        return (-(r["partial"]["bound_one_sided_5pct"] if r["partial"]["bound_one_sided_5pct"] is not None and
                  np.isfinite(r["partial"]["bound_one_sided_5pct"]) else -9),
                -abs(r["rho_BALANCED"]), r.get("seconds_4B") if np.isfinite(r.get("seconds_4B", NAN)) else 1e9)
    survivors = sorted([r for r in elig if r["verdicts"]["survives"]], key=key)
    non_surv = sorted([r for r in elig if not r["verdicts"]["survives"]], key=key)
    held = [r["id"] for r in non_surv[:3]]
    if "C2" not in held and "C2" not in [s["id"] for s in survivors]:
        held = ["C2"] + held[:2]
    table = {"ranking_rule": "survivors = internal reads passing S1, S2(a), S2(b)-repaired (n/a counts as not failing; "
                             "NOT ASSESSABLE blocks), S3-repaired, S4, S5, S6; bars and C16 can never survive; rank by S1 "
                             "one-sided bound (ties: |rho BALANCED|, then fewer seconds); freeze top <= 3",
             "panel": {"n_graded": int(g.sum()), "n_families": int(gdf["family"].nunique()),
                       "n_lineages": int(gdf["lineage"].nunique()),
                       "n_blanket_refusers": int((gdf["class"] == "blanket_refuser").sum()),
                       "n_honest_instruct": int((gdf["class"] == "instruct").sum())},
             "lofo_reference": {"family_only": ctx["lofo_family_only"], "size_only": ctx["lofo_size_only"]},
             "sanity_reproductions": repro, "rows": rows,
             "survivors_ranked": [s["id"] for s in survivors], "n_survivors": len(survivors),
             "top3_non_surviving_for_heldout_descriptive": held,
             "ranked_all_eligible": [r["id"] for r in sorted(elig, key=key)],
             "rule_provenance": "S1, S2(a), S4, S5 and S6 are the iteration-4 PREREG rules verbatim (sha256 "
                                "9da2b165...). S2(b) and S3 are the REPAIRED forms declared in the iteration-5 "
                                "strategy/plan BEFORE this evaluation ran; both old forms are printed beside them and "
                                "neither gates. The repair is what changes C2's verdict: under the iteration-4 forms C2 "
                                "fails S2(b) (exceeds its null p95 on 7/23) and S3 (15/24 checks), under the repaired "
                                "forms it passes both. Any reader comparing iterations must compare the RULES, not only "
                                "the verdicts.",
             "survivor_independence": "The survivors are NOT independent reads: C2n is C2 standardised by its own "
                                      "direction null and C17 is the mean reference-rank of C2 and the logit gap, so all "
                                      "three are monotone functions of the same self-ablation measurement (plus, for "
                                      "C17, the logit-gap bar). Shipping three of them satisfies the count but not the "
                                      "spirit of three independent internal metrics; this is stated wherever the count "
                                      "is used."}
    return table, survivors


def freeze(survivors: list[dict], held: list[str], reads: dict, df: pd.DataFrame) -> dict:
    sa_idx = [int(np.where(df["repo"] == r)[0][0]) for r in io.SET_A]
    fr = {"frozen_utc": datetime.now(timezone.utc).isoformat(),
          "rule": "top <= 3 survivors by S1 bound; empty slots stay empty",
          "survivors": [{"rank": k + 1, "id": s["id"], "declared_sign": s["declared_sign"],
                         "screen_rho_BALANCED": s["rho_BALANCED"], "S1_bound": s["partial"]["bound_one_sided_5pct"],
                         "setA_values": {io.SET_A[j]: reads[s["id"]]["values"][i] for j, i in enumerate(sa_idx)}}
                        for k, s in enumerate(survivors[:3])],
          "empty_slots": 3 - min(3, len(survivors)),
          "heldout_descriptive": [{"id": h, "label": "HELD-OUT DESCRIPTIVE - screen-failed, cannot be CONFIRMED",
                                   "declared_sign": "+" if reads[h]["sign"] > 0 else "-",
                                   "setA_values": {io.SET_A[j]: reads[h]["values"][i] for j, i in enumerate(sa_idx)}}
                                  for h in held],
          "baselines_frozen": {b: {io.SET_A[j]: reads[b]["values"][i] for j, i in enumerate(sa_idx)}
                               for b in ("logit_gap", "refusal_mass", "behaviour")}}
    p = wjson("frozen_survivors.json", fr)
    h = io.sha256_file(p)
    (WS / "frozen_survivors.sha256").write_text(f"{h}  frozen_survivors.json\n")
    logger.info(f"FROZEN survivors sha256={h} (written BEFORE any confirmation label is opened)")
    return {"sha256": h, **fr}


# =================================================================================================
# Step 2 - confirmation (used once)
# =================================================================================================
class BlindnessViolation(RuntimeError):
    pass


def load_confirm_labels(paths: list[Path]) -> list[dict] | None:
    """Code-enforced: raises unless the frozen survivor file AND its hash exist and match."""
    fz, fh = WS / "frozen_survivors.json", WS / "frozen_survivors.sha256"
    if not (fz.exists() and fh.exists()):
        raise BlindnessViolation("frozen_survivors.json/.sha256 missing - refusing to open confirmation labels")
    if fh.read_text().split()[0] != io.sha256_file(fz):
        raise BlindnessViolation("frozen_survivors.json hash mismatch - refusing to open confirmation labels")
    if not paths:
        return None
    out = []
    for p in paths:
        obj = io.load_json(p)
        items = obj if isinstance(obj, list) else (obj.get("rows") or obj.get("labels") or obj.get("records") or
                                                   [dict(repo=k, **v) for k, v in obj.items() if isinstance(v, dict) and "/" in k])
        for it in items:
            if isinstance(it, dict) and it.get("repo"):
                it = dict(it)
                it["_file"] = str(p)
                it["_protocol"] = {k: obj.get(k) for k in ("items", "item_set", "max_new_tokens", "judge", "primary_judge",
                                                          "secondary_judge", "secondary_fraction", "decoding")
                                   } if isinstance(obj, dict) else {}
                out.append(it)
    return out


def confirm(frozen: dict, reads: dict, df: pd.DataFrame, found: dict, table: dict, blind: str) -> dict:
    labels = load_confirm_labels(found["confirm_labels"])
    conf: dict[str, Any] = {"blindness": blind, "post_label_changes": [],
                            "statement": "No re-screen, subgroup search or rule change was applied after the labels were seen.",
                            "frozen_sha256": frozen["sha256"]}
    internal_ids = [s["id"] for s in frozen["survivors"]]
    if labels is None:
        conf.update({"status": "UNTESTED", "reason": "confirm_labels.json does not exist in any iter-5 sibling "
                     "(MISSING_confirm_labels): no Set A (or Set B) checkpoint has a BALANCED label",
                     "n_labelled": 0, "families_missing": ["gemma2", "phi", "eurollm"],
                     "verdicts": {sid: "UNTESTED" for sid in internal_ids},
                     "heldout_descriptive": {h["id"]: {"verdict": "UNTESTED", "label": h["label"]}
                                             for h in frozen["heldout_descriptive"]}})
    else:
        conf.update(_confirm_with_labels(labels, frozen, reads, df))
    n_conf = sum(1 for v in conf.get("verdicts", {}).values() if v == "CONFIRMED")
    shipped = [{"id": sid, "verdict": conf["verdicts"].get(sid, "UNTESTED")} for sid in internal_ids[:3]]
    conf["shipped_set"] = {"internal_reads": shipped,
                           "logit_only_baselines": ["logit_gap", "refusal_mass"],
                           "n_internal_confirmed": n_conf}
    conf["invariant_sentence"] = ("The requester's invariant of at least 3 shipped internal metrics is UNMET."
                                  if n_conf < 3 else "Invariant met: >= 3 internal reads CONFIRMED.")
    conf["invariant_reason"] = (
        f"{len(internal_ids)} internal read(s) passed the screen and were frozen "
        f"({', '.join(internal_ids) or 'none'}), but {n_conf} are CONFIRMED because the confirmation is "
        f"{conf.get('status')}: the invariant counts CONFIRMED reads, not screen survivors. The frozen survivors are "
        f"also monotone transforms of one another (see screen_ranked.json:survivor_independence), so even a successful "
        f"confirmation would ship one measurement three times.") if n_conf < 3 else "n/a"
    # increment over behaviour sentence (screen-level, since no confirmed read)
    by = {r["id"]: r for r in table["rows"]}
    pos = [r["id"] for r in table["rows"] if r.get("kind") == "internal" and isinstance(r.get("diagnostics"), dict)
           and isinstance(r["diagnostics"].get("increment_over_behaviour"), dict)
           and (r["diagnostics"]["increment_over_behaviour"].get("bound_one_sided_5pct") or -1) > 0]
    conf["increment_over_behaviour_positive_bound"] = pos
    if not pos:
        conf["behaviour_sentence"] = ("Looking inside MATCHES and does not beat 16 judged completions; it saves generation "
                                      "and the judge (no generation, no judge, about 16 seconds per 4B model).")
    conf["strongest_to_date_allowed"] = False
    conf["ams"] = ("AMS_MISSING - the wording 'strongest to date' is forbidden" if "AMS_T1" not in reads else
                   "AMS Tier-1 values loaded, but 'strongest to date' additionally requires a paired-CI win on the "
                   "same checkpoints, which no read has here")
    del by
    return conf


def _confirm_with_labels(labels: list[dict], frozen: dict, reads: dict, df: pd.DataFrame) -> dict:
    from perm_exact import perm_p_spearman
    lab = {}
    for it in labels:
        hr = it.get("harm_refusal_rate")
        bc = it.get("benign_alarming_compliance")
        bal = it.get("BALANCED", it.get("S2_core"))
        if bal is None and hr is not None and bc is not None:
            bal = 0.5 * hr + 0.5 * bc
        prod = it.get("PRODUCT", hr * bc if (hr is not None and bc is not None) else None)
        if bal is not None:
            lab[it["repo"]] = {"BALANCED": float(bal), "PRODUCT": None if prod is None else float(prod),
                               "protocol": it.get("_protocol"), "file": it["_file"]}
    repos = [r for r in df["repo"] if r in lab]
    fams = sorted(set(df.set_index("repo").loc[repos, "family"])) if repos else []
    missing = [f for f in ("gemma2", "phi", "eurollm") if f not in fams]
    out: dict[str, Any] = {"n_labelled": len(repos), "families_labelled": fams, "families_missing": missing,
                           "labelled_repos": repos, "protocol_fields_seen": [lab[r]["protocol"] for r in repos[:1]]}
    floor = len(repos) >= 8 and not missing
    idx = np.array([int(np.where(df["repo"] == r)[0][0]) for r in repos], int)
    T = np.array([lab[r]["BALANCED"] for r in repos])
    P = np.array([np.nan if lab[r]["PRODUCT"] is None else lab[r]["PRODUCT"] for r in repos])
    lin = df["lineage"].to_numpy()[idx]
    lsz = df["log10_n_params"].to_numpy(float)[idx]
    lg = reads["logit_gap"]["values"][idx]
    beh = df["behaviour"].to_numpy(float)[idx]
    verdicts, per = {}, {}
    for entry in frozen["survivors"] + frozen["heldout_descriptive"]:
        rid = entry["id"]
        r = reads[rid]
        v = r["sign"] * r["values"][idx]
        ok = np.isfinite(v)
        res: dict[str, Any] = {"n": int(ok.sum())}
        if ok.sum() >= 4:
            pp = perm_p_spearman(v[ok], T[ok], 1.0)
            res["rho_BALANCED"] = sc.spearman(v[ok], T[ok])
            res["perm"] = pp
            res["partial_given_logit_gap_size"] = sc.partial_spearman(v[ok], T[ok], [lg[ok], lsz[ok]]) if ok.sum() >= 6 else NAN
            okp = ok & np.isfinite(P)
            res["rho_PRODUCT"] = sc.spearman(v[okp], P[okp]) if okp.sum() >= 4 else NAN
            res["paired_delta_vs_logit_gap"] = sc.boot_paired_delta(v[ok], lg[ok], T[ok], lin[ok])
            res["increment_over_behaviour"] = sc.boot_partial(v[ok], T[ok], [beh[ok], lsz[ok]], lin[ok])
            res["increment_caveat"] = "Set A SCREEN16 behaviour was already known before labels (iter-4 posthoc)"
            confirmed = bool(pp["p"] < 0.05 and res["partial_given_logit_gap_size"] > 0 and res["rho_PRODUCT"] > 0)
            # sensitivity (never changes verdict)
            fam = df["family"].to_numpy()[idx][ok]
            res["sensitivity_leave_one_family_out"] = {f: sc.spearman(v[ok][fam != f], T[ok][fam != f])
                                                       for f in np.unique(fam) if (fam != f).sum() >= 4}
            nh = np.array([r_ != io.HH_DPO for r_ in np.array(repos)[ok]])
            res["sensitivity_without_hh_dpo"] = sc.spearman(v[ok][nh], T[ok][nh]) if nh.sum() >= 4 else NAN
        else:
            confirmed = False
        is_surv = entry in frozen["survivors"]
        if not floor:
            verdict = "UNTESTED"
        elif not is_surv:
            verdict = "HELD-OUT DESCRIPTIVE - screen-failed, cannot be CONFIRMED"
        else:
            verdict = "CONFIRMED" if confirmed else "NOT CONFIRMED"
        res["verdict"] = verdict
        per[rid] = res
        if is_surv:
            verdicts[rid] = verdict
    out["verdicts"] = verdicts
    out["per_read"] = per
    out["status"] = "APPLIED" if floor else "UNTESTED"
    return out


# =================================================================================================
# main
# =================================================================================================
@logger.catch(reraise=True)
def main() -> None:
    t0 = time.perf_counter()
    found = io.discover_i5()
    man = inputs_manifest(found)
    wjson("inputs_manifest.json", man)
    rows = io.load_rows()
    df, kwmeta = io.build_frame(rows)
    del rows
    logger.info(f"frame: {len(df)} rows, graded={int(df['graded'].sum())}, setA={int(df['in_setA'].sum())}")
    reads = rd.build_reads(df)
    # keep own recomputations under *_eval for the value-equality check
    for k in ("C2n", "C2ts", "C17"):
        reads[k + "_eval"] = reads[k]
    i5paths = found["candidate_values_cpu"] + found["candidate_values_gpu"] + found["values_setA"] + found["values_setA_gpu"]
    i5vals, d5 = io.load_i5_long(i5paths) if i5paths else (pd.DataFrame(), [])
    for d_ in d5:
        dev(d_["code"], json.dumps(d_))
    orient5 = {}
    for p in found["prereg5"]:
        try:
            o = io.load_json(p).get("orientations") or {}
            orient5.update({k: str(v) for k, v in o.items()})
        except (json.JSONDecodeError, OSError, AttributeError):
            pass
    # C14: from the experiment if present, else fitted here
    c14info = None
    if not (not i5vals.empty and (i5vals["canon"] == "C14").any()):
        c14info = scr.fit_c14(df)
        reads["C14"] = rd.new_read("C14", 1.0, "internal", c14info["values"], seconds_4B=reads["C2"]["seconds_4B"] + 10,
                                   seconds_note="needs all live reads (~whole live screen, ~16 s per 4B model)",
                                   source="computed_in_eval ridge metamodel (screen.fit_c14)",
                                   flags=["computed_in_eval", "values on graded = leave-one-family-out predictions"],
                                   direction_null="n/a - metamodel (identity-permutation control instead)")
        reads["C14"]["pole_refuse"] = None
        wjson("results/c14_metamodel_eval.json", {k: v for k, v in c14info.items() if k != "values"} |
              {"values": dict(zip(df["repo"], c14info["values"]))})
    for d_ in rd.attach_i5(reads, df, i5vals, orient5):
        dev(d_["code"], json.dumps(d_))
    if i5vals.empty:
        dev("NO_ITER5_VALUE_FILES", "no iter-5 CPU/GPU tier value file exists: screen run on the stored-row derivable "
            "subset (C1, C2, C2n, C2ts, C17, C14, bars); C1n, C4, C5, C6, C10, C12, C13, C15 are NOT RUN")
    ams_vals, ams_note = io.load_ams(found["ams_tier1"], list(df["repo"]))
    if ams_vals is None:
        dev("AMS_MISSING", f"no usable AMS Tier-1 scores: {ams_note}. AMS bar NOT RUN; 'strongest to date' forbidden")
    else:
        reads["AMS_T1"] = rd.new_read("AMS_T1", 1.0, "bar", ams_vals, source=f"iter5 AMS artifact {ams_note}",
                                      seconds_4B=NAN, seconds_note="from the iter-5 AMS artifact")
        logger.info(f"AMS Tier-1 bar loaded from {ams_note}")
    # Step 0
    pv = provenance(found, df, reads, i5vals)
    pv["keyword_probe"] = kwmeta
    wjson("provenance.json", pv)
    # Step 1
    table, survivors = run_screen(df, reads)
    table["keyword_probe_definition"] = kwmeta
    table["c14"] = {k: v for k, v in (c14info or {}).items() if k != "values"} if c14info else "from iter-5 file"
    table["setA_values_by_read"] = {rid: {r: reads[rid]["values"][int(np.where(df["repo"] == r)[0][0])] for r in io.SET_A}
                                    for rid in list(rd.LIVE14) + ["logit_gap", "refusal_mass", "behaviour", "keyword"]
                                    if rid in reads}
    wjson("screen_ranked.json", table)
    if len(survivors) >= 1:
        dev("REPAIRED_RULES_CHANGE_VERDICTS", "the repaired S2(b)/S3 (iteration-5 strategy) let "
            f"{[s_['id'] for s_ in survivors]} pass where the iteration-4 forms failed every candidate; both forms are "
            "printed in screen_ranked.json")
    if len(survivors) > 1:
        dev("SURVIVORS_NOT_INDEPENDENT", "C2, C2n and C17 are monotone transforms of the same C2 measurement "
            "(C17 also uses the logit-gap bar): the three shipped internal reads are one measurement, not three")
    frozen = freeze(survivors, table["top3_non_surviving_for_heldout_descriptive"], reads, df)
    conf = confirm(frozen, reads, df, found, table, pv["confirmation_blindness"])
    wjson("confirmation.json", conf)
    # later steps
    import later_steps
    later_steps.run(df=df, reads=reads, table=table, conf=conf, pv=pv, found=found, devs=DEVIATIONS, wjson=wjson)
    wjson("deviations.json", {"deviations": DEVIATIONS, "n": len(DEVIATIONS)})
    logger.info(f"done in {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()

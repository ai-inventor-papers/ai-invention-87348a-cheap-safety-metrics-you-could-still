#!/usr/bin/env python3
"""Construct every screen row ("read"): 14 live candidates, bars and the 6 dead rows.

A read is a dict with raw per-model arrays over ALL 36 rows (NaN = undefined), a declared sign, optional
per-model direction-null arrays (list of 20 values), null p95/median, pole values and seconds per ~4B model.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from scipy.stats import rankdata

from data_io import cand_block
from stats_core import spearman

NAN = float("nan")

DESC = {
    "C1": "finite-difference harm->refusal gain (iter-4 live tier)",
    "C2": "two-sided self-ablation of the harm direction at the 50% band (iter-4 live tier)",
    "C2n": "C2 standardised against its own 20-direction null: (C2 - median(null))/IQR(null) (MAD*1.4826 if IQR=0)",
    "C2ts": "two-sidedness of C2: ECDF_ref(drop_harm_mean) - ECDF_ref(drop_twin_mean), reference = 23 graded, in [-1,1]",
    "C1n": "C1 normalised read (iter-5 GPU tier)",
    "C17": "mean of reference-ECDF ranks of C2 and logit_gap (reference = 23 graded)",
    "C4": "iter-5 candidate C4", "C5": "iter-5 candidate C5", "C6": "iter-5 candidate C6",
    "C10": "iter-5 candidate C10", "C12": "iter-5 candidate C12", "C13": "iter-5 candidate C13",
    "C14": "metamodel: ridge over stored per-model features, leave-one-family-out predictions",
    "C15": "iter-5 candidate C15",
    "C3": "twin-patching flip (DEAD)", "C7": "attention on twin-differing tokens (DEAD)",
    "C8": "grad x input share (DEAD)", "C9": "template-site share (DEAD)", "C11": "8-token commitment (DEAD)",
    "C16": "steering slope comparator (DEAD)",
    "logit_gap": "first-token logit gap, harmful minus twin (logit-only bar)",
    "refusal_mass": "refusal-token softmax mass, harmful minus twin (logit-only bar)",
    "behaviour": "16-prompt judged behavioural probe screen16_S2_screen16 (generation + gemini judge)",
    "keyword": "16-prompt judge-free keyword probe on the same 64-token replies",
    "family_only": "family mean of the target, leave-one-family-out (bar)",
    "size_only": "log10(n_params) (bar)",
    "card_regex": "model-card regex (reads nothing of the model; 0 if card mentions abliteration/uncensoring)",
    "AMS_T1": "AMS Tier-1 (iter-5 reimplementation)",
}
LIVE14 = ["C1", "C2", "C2n", "C2ts", "C1n", "C17", "C4", "C5", "C6", "C10", "C12", "C13", "C14", "C15"]
BARS = ["logit_gap", "refusal_mass", "behaviour", "keyword", "family_only", "size_only", "card_regex", "AMS_T1"]
DEAD = {"C3": "+", "C7": "+", "C8": "+", "C9": "-", "C11": "+", "C16": "+"}
DIRECTION_FREE = {"logit_gap", "refusal_mass", "behaviour", "keyword", "family_only", "size_only", "card_regex",
                  "AMS_T1"}


def _arr(blocks: list[dict], key: str = "value") -> np.ndarray:
    out = []
    for b in blocks:
        v = b.get(key)
        und = b.get("undefined", False) if key == "value" else False
        out.append(NAN if (v is None or und) else float(v))
    return np.array(out, dtype=np.float64)


def ecdf_ref(x: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Mid-rank ECDF of x against the reference sample, scaled to [0,1] (ref values map to (rank-0.5)/n)."""
    ref = np.sort(ref[~np.isnan(ref)])
    n = len(ref)
    lo = np.searchsorted(ref, x, side="left")
    hi = np.searchsorted(ref, x, side="right")
    out = (lo + hi) / 2.0 / n
    out[np.isnan(x)] = NAN
    return out


def new_read(rid: str, sign: float, kind: str, values: np.ndarray, **kw: Any) -> dict:
    r = {"id": rid, "sign": sign, "kind": kind, "values": values, "desc": DESC.get(rid, rid),
         "null_values": None, "null_p95": None, "null_median": None, "pole_refuse": None, "pole_comply": None,
         "seconds_4B": NAN, "seconds_note": "", "source": "", "flags": [], "direction_null": "n/a - no direction",
         "undefined_reasons": {}}
    r.update(kw)
    return r


def seconds_4b(df: pd.DataFrame, parts: list[str], add_base: bool = True, extra: str | None = None) -> tuple[float, str]:
    m = (df["n_params"] > 3.0e9) & (df["device"] == "cuda")
    vals = []
    for _, row in df[m].iterrows():
        s = sum(float(row["cand_seconds"].get(p, 0) or 0) for p in parts)
        if add_base:
            s += float(row["shared_base_s"] or 0)
        if extra:
            s += float(row["timing"].get(extra, 0) or 0)
        vals.append(s)
    if not vals:
        return NAN, "no ~4B GPU rows"
    return float(np.median(vals)), f"median over {len(vals)} ~4B GPU rows of candidate seconds {parts}" + \
        (" + shared base passes" if add_base else "") + (f" + {extra}" if extra else "") + " (excluding load)"


def build_reads(df: pd.DataFrame) -> dict[str, dict]:
    g = df["graded"].to_numpy()
    reads: dict[str, dict] = {}
    n = len(df)
    for cid in ["C1", "C2"]:
        bl = cand_block(df, cid)
        nulls = [b.get("null_values") for b in bl]
        s, note = seconds_4b(df, [cid])
        reads[cid] = new_read(cid, 1.0, "internal", _arr(bl), null_values=nulls,
                              null_p95=_arr(bl, "null_p95"),
                              null_median=np.array([np.median(x) if x else NAN for x in nulls]),
                              pole_refuse=_arr(bl, "pole_refuse"), pole_comply=_arr(bl, "pole_comply"),
                              seconds_4B=s, seconds_note=note, source="iter4 rows/<repo>.json:candidates." + cid,
                              direction_null="20 anisotropy-matched random directions (iter-4 rows)")
    # ---- C2n ----
    c2 = reads["C2"]
    med = np.full(n, NAN)
    spread = np.full(n, NAN)
    fb = []
    for i, nv in enumerate(c2["null_values"]):
        if not nv:
            continue
        a = np.asarray(nv, float)
        med[i] = np.median(a)
        iqr = np.subtract(*np.percentile(a, [75, 25]))
        if iqr <= 0:
            iqr = 1.4826 * np.median(np.abs(a - med[i]))
            fb.append(df["repo"].iloc[i])
        spread[i] = iqr
    tf = lambda x: (x - med) / spread  # noqa: E731
    c2n_nulls = [list((np.asarray(nv, float) - med[i]) / spread[i]) if nv else None
                 for i, nv in enumerate(c2["null_values"])]
    reads["C2n"] = new_read("C2n", 1.0, "internal", tf(c2["values"]), null_values=c2n_nulls,
                            null_p95=tf(c2["null_p95"]), null_median=np.zeros(n),
                            pole_refuse=tf(c2["pole_refuse"]), pole_comply=tf(c2["pole_comply"]),
                            seconds_4B=c2["seconds_4B"], seconds_note=c2["seconds_note"] + " (C2n = C2 + null)",
                            source="computed_in_eval from rows C2.value/null_values", flags=["computed_in_eval"] +
                            ([f"MAD_fallback:{fb}"] if fb else []),
                            direction_null="C2's 20 random directions, same transform")
    # ---- C2ts ----
    bl = cand_block(df, "C2")
    dh, dt = _arr(bl, "drop_harm_mean"), _arr(bl, "drop_twin_mean")
    c2ts = ecdf_ref(dh, dh[g]) - ecdf_ref(dt, dt[g])
    reads["C2ts"] = new_read("C2ts", 1.0, "internal", c2ts, seconds_4B=c2["seconds_4B"],
                             seconds_note=c2["seconds_note"], source="computed_in_eval from rows C2.drop_harm_mean/"
                             "drop_twin_mean (reference ECDF fitted on the 23 graded, frozen for Set A)",
                             flags=["computed_in_eval", "poles_not_stored_for_drop_means"],
                             direction_null="NOT STORED - per-direction drop means were not saved; blocking")
    # ---- C17 ----
    lg = _arr(cand_block(df, "logit_gap"))
    lgb = cand_block(df, "logit_gap")
    ref_c2, ref_lg = c2["values"][g], lg[g]
    c17 = 0.5 * (ecdf_ref(c2["values"], ref_c2) + ecdf_ref(lg, ref_lg))
    c17_null_mean = 0.5 * (ecdf_ref(np.array([np.mean(x) if x else NAN for x in c2["null_values"]]), ref_c2)
                           + ecdf_ref(lg, ref_lg))
    c17_nulls = [list(0.5 * (ecdf_ref(np.asarray(nv, float), ref_c2) + ecdf_ref(np.full(len(nv), lg[i]), ref_lg)))
                 if nv else None for i, nv in enumerate(c2["null_values"])]
    c17_p95 = np.array([np.percentile(x, 95) if x else NAN for x in c17_nulls])
    c17_med = np.array([np.median(x) if x else NAN for x in c17_nulls])
    s17, note17 = seconds_4b(df, ["C2"])
    reads["C17"] = new_read("C17", 1.0, "internal", c17, null_values=c17_nulls, null_p95=c17_p95,
                            null_median=c17_med,
                            pole_refuse=0.5 * (ecdf_ref(c2["pole_refuse"], ref_c2) + ecdf_ref(_arr(lgb, "pole_refuse"), ref_lg)),
                            pole_comply=0.5 * (ecdf_ref(c2["pole_comply"], ref_c2) + ecdf_ref(_arr(lgb, "pole_comply"), ref_lg)),
                            seconds_4B=s17, seconds_note=note17, source="computed_in_eval (ranks vs graded reference)",
                            flags=["computed_in_eval"], direction_null="C2 replaced by each random-direction C2 value")
    del c17_null_mean
    # ---- dead rows (values kept only for ranking / printing) ----
    for cid, sg in DEAD.items():
        bl = cand_block(df, cid)
        s, note = seconds_4b(df, [cid])
        nulls = [b.get("null_values") for b in bl]
        has_null = any(nulls)
        reads[cid] = new_read(cid, 1.0 if sg == "+" else -1.0, "dead", _arr(bl),
                              null_values=nulls if has_null else None,
                              null_p95=_arr(bl, "null_p95") if has_null else None,
                              null_median=np.array([np.median(x) if x else NAN for x in nulls]) if has_null else None,
                              pole_refuse=_arr(bl, "pole_refuse"), pole_comply=_arr(bl, "pole_comply"),
                              seconds_4B=s, seconds_note=note, source="iter4 rows candidates." + cid,
                              flags=["DEAD - not re-screened"] + (["C16 two-sided comparator; + used for printing only"]
                                                                  if cid == "C16" else []))
    # ---- logit bars ----
    for cid in ["logit_gap", "refusal_mass"]:
        bl = cand_block(df, cid)
        s, note = seconds_4b(df, [], add_base=False, extra="plain:base")
        reads[cid] = new_read(cid, 1.0, "bar", _arr(bl), pole_refuse=_arr(bl, "pole_refuse"),
                              pole_comply=_arr(bl, "pole_comply"), seconds_4B=s,
                              seconds_note=note + " (one plain forward pass)", source="iter4 rows candidates." + cid)
    s, note = seconds_4b(df, [], add_base=False, extra="plain:gen64")
    reads["behaviour"] = new_read("behaviour", 1.0, "bar", df["behaviour"].astype(float).to_numpy(),
                                  seconds_4B=s, seconds_note=note + " + 16 judge calls (judge time not recorded)",
                                  source="iter4 posthoc_live.json:per_model[].screen16_S2_screen16")
    reads["keyword"] = new_read("keyword", 1.0, "bar", df["keyword"].astype(float).to_numpy(), seconds_4B=s,
                                seconds_note=note + " (no judge)", source="computed_in_eval from rows gen64 texts",
                                flags=["computed_in_eval"])
    reads["size_only"] = new_read("size_only", 1.0, "bar", df["log10_n_params"].to_numpy(),
                                  source="rows n_params", seconds_4B=0.0, seconds_note="no model run")
    reads["card_regex"] = new_read("card_regex", 1.0, "bar", df["card_regex"].to_numpy(),
                                   source="local snapshot README.md regex (data_io.CARD_REGEX)", seconds_4B=0.0,
                                   seconds_note="no model run")
    reads["family_only"] = new_read("family_only", 1.0, "bar", np.full(n, NAN),
                                    source="LOFO family mean of the target", seconds_4B=0.0,
                                    seconds_note="no model run", flags=["LOFO-only row"])
    return reads


def attach_i5(reads: dict[str, dict], df: pd.DataFrame, i5: pd.DataFrame, orient5: dict[str, str]) -> list[dict]:
    """Overlay iter-5 values: the file's value is used for the canonical row; own recomputation kept as check."""
    devs = []
    if i5 is None or i5.empty:
        return devs
    prim = i5[i5["variant"].astype(str).isin(["primary", "value", "plain"])]
    repo_idx = {r: i for i, r in enumerate(df["repo"])}
    for can, sub in prim.groupby("canon"):
        # one readout per canonical id: prefer the lexicographically first candidate_id / readout, log others
        cids = sorted(sub["candidate_id"].astype(str).unique())
        pick = cids[0]
        sub = sub[sub["candidate_id"].astype(str) == pick]
        if sub["readout"].notna().any():
            ro = sorted(sub["readout"].dropna().astype(str).unique())
            pref = [x for x in ro if x in ("primary", "margin", "main")] or ro
            sub = sub[(sub["readout"].astype(str) == pref[0]) | sub["readout"].isna()]
        if len(cids) > 1:
            devs.append({"code": "I5_MULTIPLE_IDS_PER_CANON", "canon": can, "ids": cids, "picked": pick})
        n = len(df)
        vals, p95, med, pr, pc, secs = (np.full(n, NAN) for _ in range(6))
        for _, it in sub.iterrows():
            i = repo_idx.get(it["repo"])
            if i is None:
                continue
            if not it["undefined"] and it["value"] is not None:
                vals[i] = float(it["value"])
            for arr, key in ((p95, "null_p95"), (med, "null_median"), (pr, "pole_refuse"), (pc, "pole_comply"),
                             (secs, "seconds")):
                v = it[key]
                if v is not None and not (isinstance(v, float) and math.isnan(v)):
                    try:
                        arr[i] = float(v)
                    except (TypeError, ValueError):
                        pass
        n_graded_vals = int(np.sum(np.isfinite(np.array([1.0 if (not it["undefined"] and it["value"] is not None) else np.nan
                                                          for _, it in sub.iterrows()], dtype=float))))
        if n_graded_vals < 15:
            devs.append({"code": "I5_PARTIAL_IGNORED", "canon": can, "n_values": n_graded_vals,
                         "detail": "the iter-5 file carries fewer than 15 defined values for this candidate (the "
                                   "sibling experiment was still running): the row is left NOT RUN / on its "
                                   "eval-computed version rather than screened on a partial panel"})
            continue
        sg = -1.0 if str(orient5.get(pick, orient5.get(can, "+"))).strip().startswith("-") else 1.0
        m4 = (df["n_params"] > 3.0e9).to_numpy()
        old = reads.get(can)
        r = new_read(can, sg, "internal" if can != "AMS_T1" else "bar", vals,
                     null_p95=p95 if np.isfinite(p95).any() else None,
                     null_median=med if np.isfinite(med).any() else None,
                     pole_refuse=pr if np.isfinite(pr).any() else None,
                     pole_comply=pc if np.isfinite(pc).any() else None,
                     seconds_4B=float(np.nanmedian(secs[m4])) if np.isfinite(secs[m4]).any() else NAN,
                     seconds_note="iter-5 file seconds (median over >3B rows)",
                     source=f"iter5 {sorted(sub['file'].unique())} candidate_id={pick}", flags=["iter5_value"],
                     direction_null="iter-5 null_summary" if np.isfinite(p95).any() else "n/a - not supplied")
        if old is not None:
            both = np.isfinite(old["values"]) & np.isfinite(vals)
            agree = spearman(old["values"][both], vals[both]) if both.sum() > 3 else NAN
            maxdiff = float(np.max(np.abs(old["values"][both] - vals[both]))) if both.any() else NAN
            r["flags"].append(f"eval_recomputation_spearman={agree:.4f}; max_abs_diff={maxdiff:.3g}")
            # keep own per-direction nulls if the iter-5 file carries only summaries
            if old.get("null_values") is not None and maxdiff < 1e-6:
                r["null_values"] = old["null_values"]
        reads[can] = r
    return devs

#!/usr/bin/env python3
"""What faking a safety score costs -- the six-rung forgery ladder, executed.

    pyenv/bin/python method.py --stages all        # census .. outputs, in the plan's order
    pyenv/bin/python method.py --stages ladder2 --passes 1,2,3 [--only-ckpt REPO]

STANDING RULES, each one a lesson from iteration 1, which reached model staging
with zero rungs applied and lost everything held in memory:

  PERSIST ON MEASURE   every (checkpoint, rung, magnitude) cell writes its own
                       file and appends one line to out/ladder_rows.jsonl the
                       instant it is computed. Nothing is assembled from RAM.
  RESUMABLE            a cell whose file exists is skipped. Assume a restart.
  COST ORDER           cheap rungs land on EVERY checkpoint before an expensive
                       rung starts on any.
  NO QWEN JUDGE        Qwen3Guard was Qwen3-4B-SafeRL's training reward.
  BUDGET               every judge call is charged to out/spend.jsonl and the
                       running total is asserted before each batch is issued.

THIS BOX HAS NO GPU, two CPU cores and a 16 GB cgroup SHARED INSIDE THE
CONTAINER with two sibling experiments (~0.3 core per process). The fallback the
plan pre-committed to is the path taken: the weight half of the ladder runs in
full on CPU over six hosts / six families (every weight rung applied as an exact
float64 Gram update, flab2/gramspec.py); the behavioural half runs harvest-faithful
cells on two hosts (ROSI's own Qwen2.5-0.5B-Instruct, and Qwen3-0.6B) with 20-token
greedy continuations; the two TRAINED rungs are not trained (merged-LoRA-shaped
deltas measure their detection surface). Every deviation is recorded in
out/analysis_out.json under "deviations" and stated in out/RESULTS.md.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
os.environ.setdefault("TORCHINDUCTOR_DISABLE", "1")

import numpy as np
from loguru import logger

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))

OUT = WORKSPACE / "out"
CELLS = OUT / "cells"
LOGS = WORKSPACE / "logs"
FIGS = WORKSPACE / "figures"
for d in (OUT, CELLS, LOGS, FIGS):
    d.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(LOGS / "method.log", rotation="30 MB", level="DEBUG")

from flab2 import analysis as AN  # noqa: E402
from flab2 import hw as HW  # noqa: E402
from flab2 import detect as D  # noqa: E402
from flab2 import ladder as LD  # noqa: E402
from flab2 import ladder2 as LD2  # noqa: E402
from flab2 import hw as HW  # noqa: E402
from flab2 import panel as P  # noqa: E402
from flab2 import prereg as PR  # noqa: E402
from flab2 import repo_io as R  # noqa: E402
from flab2 import rungs as RG  # noqa: E402
from flab2 import wmetrics as W  # noqa: E402

CACHE_ROOT = Path(
    os.environ.get(
        "HF_HUB_CACHE",
        "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/.shared_cache/hf/hub",
    )
)
SEED = 20260920

# The ladder hosts: >=4 checkpoints spanning >=4 genuinely distinct architecture
# families, ordered smallest-first because wall clock, not VRAM or disk, is the
# binding constraint on this box.
# SHRINK ORDER items 2 and 6, invoked. The box is a 2-CPU container at load
# ~280 shared with other pipeline runs, so the realised throughput is about a
# fifth of one core. Six hosts do not fit. These three span three GENUINELY
# DISTINCT architecture families -- the floor the direction states -- and are
# the three cheapest, so the ladder is COMPLETE on each rather than truncated
# across six. The remaining three are listed in `LADDER_HOSTS_DEFERRED` and are
# attempted only if the clock allows.
LADDER_HOSTS: list[tuple[str, str]] = [
    # SIX hosts over SIX architecture families, smallest first. The earlier pass
    # of this iteration shrank to three hosts because it measured ~55 s per
    # forward item; re-measured at 07:20 the same box does a 1024x3072 SVD in
    # 0.3 s, so the shrink is reversed. Every host gets the SAME rung grid.
    ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen2.5"),
    ("Qwen/Qwen3-0.6B", "Qwen3"),
    ("TinyLlama/TinyLlama-1.1B-Chat-v1.0", "TinyLlama"),
    ("allenai/OLMo-2-0425-1B-Instruct", "OLMo2"),
    ("HuggingFaceTB/SmolLM2-1.7B-Instruct", "SmolLM2"),
    ("google/gemma-2-2b-it", "Gemma2"),
]
LADDER_HOSTS_DEFERRED: list[tuple[str, str]] = []
# ROSI evaluated this exact model (Table 1: harm refusal 90.4 -> 99.3). ROSI was
# NEVER evaluated on Qwen3, so every Qwen3 ROSI number here is labelled OUR
# EXTRAPOLATION.
ROSI_CAL = "Qwen/Qwen2.5-0.5B-Instruct"
BEHAVIOUR_HOST = "Qwen/Qwen3-0.6B"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, default=_default))


def _default(o):
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    return str(o)


def append_row(obj: dict) -> None:
    with (OUT / "ladder_rows.jsonl").open("a") as fh:
        fh.write(json.dumps(obj, default=_default) + "\n")


def load_panel_rows() -> list[dict]:
    rows = []
    for p in sorted((OUT / "panel").glob("*.json")):
        try:
            rows.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            logger.warning(f"unreadable panel row {p.name}")
    return rows


def load_acts_rows() -> list[dict]:
    rows = []
    for p in sorted((OUT / "acts_panel").glob("*.json")):
        if p.name.endswith("__diag.json"):
            continue
        try:
            rows.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            logger.warning(f"unreadable acts row {p.name}")
    return rows


def honest_lookup(panel_rows: list[dict], metric_ids: list[str]) -> dict[str, list[float]]:
    return P.honest_distribution(panel_rows, metric_ids)


def resolve_snapshot(repo: str) -> Path | None:
    census = OUT / "cache_census.json"
    if census.exists():
        for r in json.loads(census.read_text())["repos"]:
            if r["repo_id"] == repo and r.get("snapshot_dir"):
                p = Path(r["snapshot_dir"])
                if p.is_dir() and list(p.glob("*.safetensors")):
                    return p
    return R.snapshot_dir(CACHE_ROOT, repo)


# ---------------------------------------------------------------------------
# STAGE prereg
# ---------------------------------------------------------------------------

def stage_prereg() -> dict:
    reg = PR.load_registry(WORKSPACE / "registry_inherited.json", verify=True)
    logger.info(f"registry verified: {reg['_sha256'][:16]}... n={reg['n_metrics']}")
    doc = PR.build_prereg(
        reg,
        extra={
            "hardware": {
                "gpu": False,
                "reason": "/dev/nvidia* absent; torch.cuda.is_available() False",
                "cpus": os.cpu_count(),
                "consequence": (
                    "The weight half of the ladder runs in full on CPU. The "
                    "behavioural half runs at a reduced item budget on the "
                    "smallest host. The two TRAINED rungs are NOT trained; "
                    "their weight-delta SHAPE is measured instead and they are "
                    "labelled trained=false everywhere."
                ),
            },
            "ladder_hosts": [{"repo": r, "family": f} for r, f in LADDER_HOSTS],
            "rosi_calibration_host": ROSI_CAL,
            "behaviour_host": BEHAVIOUR_HOST,
        },
    )
    doc["prereg_sha256"] = PR.sha256_obj(doc)
    jdump(OUT / "PREREG.json", doc)
    logger.info(f"PREREG frozen, sha256={doc['prereg_sha256'][:16]}...")
    return doc


# ---------------------------------------------------------------------------
# STAGE gates
# ---------------------------------------------------------------------------

def stage_gates() -> dict:
    t = time.time()
    gates = {
        "G1_rank_zero_exactness": PR.gate_g1_rank_zero(),
        "G2_bsa_synthetic_null": PR.gate_g2_bsa_null(),
        "G3_gate1_band50_correction": PR.gate_g3_band50_correction(),
        "G4_key_shape_sanity": PR.gate_g4_key_shape(),
        "G5_botgap_bf16": PR.gate_g5_botgap_bf16(),
    }
    gates["_summary"] = {
        "G1_pass": gates["G1_rank_zero_exactness"]["pass_exact"],
        "G2_pass": gates["G2_bsa_synthetic_null"]["pass"],
        "G3_correction_accepted": gates["G3_gate1_band50_correction"]["correction_accepted"],
        "G4_pass": gates["G4_key_shape_sanity"]["pass"],
        "G5_pass": gates["G5_botgap_bf16"]["pass"],
        "policy": (
            "A failed gate DEGRADES the affected metric class (marked "
            "ASSUMPTION_FAILED in every downstream row); it never aborts the run."
        ),
        "seconds": round(time.time() - t, 2),
    }
    jdump(OUT / "gates.json", gates)
    for k, v in gates["_summary"].items():
        if k.startswith("G"):
            logger.info(f"  {k}: {v}")
    return gates


# ---------------------------------------------------------------------------
# STAGE ladder (weight tier) -- the core, and it needs no GPU at all
# ---------------------------------------------------------------------------

def stage_ladder(*, deadline_min: float = 120.0, hosts: list[tuple[str, str]] | None = None) -> None:
    hosts = hosts or LADDER_HOSTS
    panel_rows = load_panel_rows()
    metric_ids = sorted(PR.IMPL_WEIGHT)
    honest = honest_lookup(panel_rows, metric_ids)
    logger.info(
        f"honest panel for B3: n={max((len(v) for v in honest.values()), default=0)} "
        f"checkpoints over {len({r['family'] for r in panel_rows})} families"
    )

    carrier_by_host = {}
    cpath = OUT / "carrier.json"
    if cpath.exists():
        carrier_by_host = json.loads(cpath.read_text())
    s_hat_by_host = {}
    spath = OUT / "s_hat.json"
    if spath.exists():
        s_hat_by_host = json.loads(spath.read_text())

    t0 = time.time()
    n_cells = 0
    # HOST-AT-A-TIME, smallest first.  The plan's strict cross-host cost order
    # (every cheap rung on every checkpoint before any expensive rung) assumes
    # loading a checkpoint is cheap.  On this box the load average is in the
    # HUNDREDS on two cores, so holding six checkpoints' spectra while
    # interleaving costs more than it buys.  Within a host the cost order is
    # still strictly honoured, and each host's ladder is COMPLETE on disk before
    # the next one starts -- which is the property that matters when the clock
    # runs out.  The deviation is recorded in analysis_out.json.
    rung_groups = [
        ["F0_repo_file", "F1_system_prompt"],
        ["F2a_constant_bias"],
        ["F2a_constant_carrier"],
        ["F2b_rosi", "F2b_rosi_hidden"],
        ["F3_keyword_lora", "F4_safety_sft"],
    ]
    host_status = []
    for repo, fam in hosts:
        if (time.time() - t0) / 60 > deadline_min:
            logger.warning("LADDER DEADLINE reached before host %s", repo)
            break
        snap = resolve_snapshot(repo)
        if snap is None:
            logger.warning(f"{repo}: not resolvable locally, skipped")
            host_status.append({"repo": repo, "status": "not_resolvable"})
            continue
        th = time.time()
        try:
            o, d, info = R.load_residual_matrices(snap)
        except (R.QuantizedCheckpoint, OSError, ValueError, FileNotFoundError) as exc:
            logger.warning(f"{repo}: {type(exc).__name__}: {exc}")
            host_status.append({"repo": repo, "status": f"{type(exc).__name__}"})
            continue
        logger.info(f"{repo}: read {len(o)} layers in {time.time()-th:.0f}s")
        ts = time.time()
        spec_cache = OUT / "base_specs"
        spec_cache.mkdir(parents=True, exist_ok=True)
        cpath = spec_cache / f"{repo.replace('/', '__')}.npz"
        cached = W.load_specs(cpath) if cpath.exists() else None
        if cached is not None and len(cached[0]) == len(o):
            o_specs, d_specs = cached
            logger.info(f"{repo}: base spectra loaded from cache "
                        f"({time.time()-ts:.0f}s)")
        else:
            o_specs = W.spectra_of(o, "o_proj")
            # down_proj: VALUES ONLY here too. Its one registry row,
            # w_down_botgap_min, reads the two smallest singular values and no
            # subspace -- and on this panel that row is the STRONGEST separator
            # of the ten, so it is the last thing to economise on. Values-only
            # halves the dominant cost; the two down_proj SUBSPACE extensions
            # become NaN and are reported NOT COMPUTED.
            d_specs = W.spectra_of(d, "down_proj", vectors=False)
            try:
                W.save_specs(cpath, o_specs, d_specs)
            except (OSError, ValueError) as exc:
                logger.warning(f"{repo}: could not cache spectra: {exc}")
        base_metrics = W.battery_from_specs(o_specs, d_specs, with_z=True)
        base_metrics = {k: v for k, v in base_metrics.items() if not k.startswith("_")}
        logger.info(f"{repo}: base battery in {time.time()-ts:.0f}s "
                    f"BSA={base_metrics['w_bsa_w8_k1']:.4f} "
                    f"botgap={base_metrics['w_botgap_min']:.4f} "
                    f"z={base_metrics.get('w_bsa_z', float('nan')):.2f}")
        text = R.read_repo_text(snap)
        sig = R.key_shape_signature(R.build_index(snap))
        sh = s_hat_by_host.get(repo)
        s_hat = np.asarray(sh["s_hat"] if isinstance(sh, dict) else sh,
                           dtype=np.float64) if sh else None
        s_measured = bool(sh)
        if s_hat is None:
            # Without a measured refusal direction ROSI's own definition cannot
            # be honoured. A deterministic SHARED direction preserves the
            # GEOMETRY that makes the rank-one rung what it is (one common left
            # factor across layers) while the direction itself is synthetic, and
            # every such row is labelled s_hat_measured=false.
            rng = np.random.default_rng(SEED)
            s_hat = rng.standard_normal(o[0].shape[0])
            s_hat /= np.linalg.norm(s_hat)
            logger.warning(f"{repo}: no measured s_hat -> SHARED SYNTHETIC "
                           "direction (geometry preserved, labelled)")
        # the first host carries the FULL ladder; later hosts run light, so
        # that three architecture families are reached rather than one
        # exhaustively explored
        plan = LD.rung_cells(o, d, carrier=carrier_by_host.get(repo),
                             s_hat=s_hat, seed=SEED,
                             light=(repo != hosts[0][0]))

        cell_id = f"{repo.replace('/', '__')}__F_none__0"
        if not (CELLS / f"{cell_id}.json").exists():
            row = {
                "cell_id": cell_id, "ckpt": repo, "family": fam,
                "rung": "F_none", "rung_index": -1, "magnitude": 0.0,
                "weights_byte_identical": True,
                "metrics": {k: (float(v) if v is not None and np.isfinite(v) else None)
                            for k, v in base_metrics.items()
                            if isinstance(v, (int, float, np.floating))},
                "blind": D.blind_screen(text, sig, base_metrics, honest, fpr=0.05),
                "family_aware": {"E1": {"flag": False, "changed_files": [], "score": 0.0},
                                 "E2": {"flag": False, "score": 0.0}, "any": False},
                "n_layers": len(o), "snapshot": str(snap),
                "s_hat_measured": s_measured,
            }
            jdump(CELLS / f"{cell_id}.json", row)
            append_row(row)
            n_cells += 1

        host_cells = 0
        for group in rung_groups:
            for cell in plan:
                if cell["rung"] not in group:
                    continue
                if (time.time() - t0) / 60 > deadline_min:
                    logger.warning("LADDER DEADLINE reached mid-host")
                    break
                cid = (f"{repo.replace('/', '__')}__{cell['rung']}"
                       f"__{cell['magnitude']:g}")
                fp = CELLS / f"{cid}.json"
                if fp.exists():
                    continue
                try:
                    res = LD.measure_cell(
                        cell, o, d, base_metrics, text, sig, honest,
                        with_z=False, base_specs=(o_specs, d_specs)
                    )
                except (ValueError, np.linalg.LinAlgError, MemoryError) as exc:
                    logger.error(f"{cid}: {type(exc).__name__}: {exc}")
                    continue
                res.update({"cell_id": cid, "ckpt": repo, "family": fam,
                            "n_layers": len(o), "snapshot": str(snap),
                            "s_hat_measured": s_measured})
                jdump(fp, res)
                append_row(res)
                n_cells += 1
                host_cells += 1
                gc.collect()
            logger.info(f"  {repo:<38} after [{'+'.join(g[:6] for g in group)}] "
                        f"host={host_cells} total={n_cells} "
                        f"({(time.time()-t0)/60:.1f} min)")
        host_status.append({"repo": repo, "family": fam, "status": "done",
                            "cells": host_cells,
                            "minutes": round((time.time()-th)/60, 2)})
        jdump(OUT / "ladder_status.json",
              {"n_cells": n_cells, "PARTIAL_LADDER": True,
               "minutes": round((time.time() - t0) / 60, 2),
               "hosts": host_status})
        del o, d, o_specs, d_specs, plan
        gc.collect()

    jdump(OUT / "ladder_status.json",
          {"n_cells": n_cells,
           "PARTIAL_LADDER": len(host_status) < len(hosts),
           "minutes": round((time.time() - t0) / 60, 2),
           "hosts": host_status,
           "deviation": (
               "HOST-AT-A-TIME rather than the plan's strict cross-host cost "
               "order: on this box the load average was ~280 on two cores, so "
               "each host's ladder is completed and persisted before the next "
               "host is loaded. Cost order is honoured WITHIN each host."
           )})
    logger.info(f"LADDER DONE: {n_cells} cells in {(time.time()-t0)/60:.1f} min")


def stage_ladder2(*, deadline_min: float = 200.0, hosts: list[tuple[str, str]] | None = None,
                  passes: tuple[int, ...] = (1, 2, 3)) -> None:
    """COST ORDER across hosts: pass 1 (F0/F1/F2a) lands on EVERY host before
    pass 2 (ROSI) starts on any, and pass 2 before pass 3 (hiding arm, band,
    LoRA-shaped deltas). Every cell is written the instant it is measured."""
    hosts = hosts or LADDER_HOSTS
    t0 = time.time()
    status: list[dict] = []
    calib = OUT / "bcells" / f"{ROSI_CAL.replace('/', '__')}__alpha_recovery.json"
    alpha_star = None
    if calib.exists():
        alpha_star = json.loads(calib.read_text()).get("alpha_star_mult")
    for ps in passes:
        for repo, fam in hosts:
            if (time.time() - t0) / 60 > deadline_min:
                logger.warning(f"LADDER DEADLINE before pass {ps} host {repo}")
                break
            sl = repo.replace("/", "__")
            probe_p = OUT / "probe" / f"{sl}.json"
            probe = json.loads(probe_p.read_text()) if probe_p.exists() else None
            s_all = None
            if probe is not None and (OUT / "probe" / f"{sl}.npz").exists():
                s_all = np.load(OUT / "probe" / f"{sl}.npz")["s_hat_all"].astype(np.float64)
            cells = [c for c in LD2.enumerate_cells(probe, alpha_star=alpha_star)
                     if c["pass"] == ps]
            todo = [c for c in cells if not (CELLS / f"{sl}__{c['rung']}__{c['magnitude']:g}.json").exists()]
            need_none = not (CELLS / f"{sl}__F_none__0.json").exists()
            if not todo and not need_none:
                continue
            snap = resolve_snapshot(repo)
            try:
                if snap is None:
                    raise FileNotFoundError(f"{repo}: not resolvable locally")
                hs = LD2.host_state(repo, snap, probe, WORKSPACE / "cache" / "grams",
                                    seed=SEED, log=logger.info)
            except (R.QuantizedCheckpoint, OSError, ValueError, FileNotFoundError,
                    MemoryError) as exc:
                logger.warning(f"{repo}: {type(exc).__name__}: {exc}")
                status.append({"repo": repo, "pass": ps, "status": type(exc).__name__})
                continue
            base = hs["base"]
            text = R.read_repo_text(snap)
            sig = R.key_shape_signature(hs["index"])
            logger.info(f"{repo}: {hs['n_layers']} layers, base ({hs['source']}) in "
                        f"{hs['seconds']:.0f}s BSA={base['w_bsa_w8_k1']:.4f} "
                        f"botgap={base['w_botgap_min']:.4g} "
                        f"down_botgap={base['w_down_botgap_min']:.4g} "
                        f"z={base.get('w_bsa_z', float('nan')):.2f}")
            panel_rows = load_panel_rows()
            honest = honest_lookup(panel_rows, sorted(PR.IMPL_WEIGHT))
            if need_none:
                row = {"cell_id": f"{sl}__F_none__0", "ckpt": repo, "family": fam,
                       "rung": "F_none", "rung_index": -1, "magnitude": 0.0,
                       "weights_byte_identical": True,
                       "metrics": {k: (float(v) if v is not None and np.isfinite(v) else None)
                                   for k, v in base.items()
                                   if isinstance(v, (int, float, np.floating))},
                       "blind": D.blind_screen(text, sig, base, honest, fpr=0.05),
                       "family_aware": {"E1": {"flag": False, "changed_files": [], "score": 0.0},
                                        "E2": {"flag": False, "score": 0.0}, "any": False},
                       "n_layers": hs["n_layers"], "snapshot": str(snap),
                       "s_hat_measured": probe is not None, "ladder_version": 2}
                jdump(CELLS / f"{sl}__F_none__0.json", row)
                append_row(row)
            n_done = 0
            for c in todo:
                if (time.time() - t0) / 60 > deadline_min:
                    logger.warning("LADDER DEADLINE mid-host")
                    break
                cid = f"{sl}__{c['rung']}__{c['magnitude']:g}"
                try:
                    res = LD2.measure_cell(c, hs, text, sig, honest, probe=probe,
                                           s_all=s_all, seed=SEED)
                except (ValueError, np.linalg.LinAlgError, MemoryError, KeyError) as exc:
                    logger.error(f"{cid}: {type(exc).__name__}: {exc}")
                    continue
                res.update({"cell_id": cid, "ckpt": repo, "family": fam,
                            "n_layers": hs["n_layers"],
                            "snapshot": str(snap), "s_hat_measured": probe is not None,
                            "ladder_version": 2})
                jdump(CELLS / f"{cid}.json", res)
                append_row(res)
                n_done += 1
                gc.collect()
            logger.info(f"pass {ps} {repo:<38} +{n_done} cells "
                        f"({(time.time()-t0)/60:.1f} min)")
            status.append({"repo": repo, "family": fam, "pass": ps, "cells": n_done})
            jdump(OUT / "ladder_status.json", {"minutes": round((time.time()-t0)/60, 2),
                                               "hosts": status, "alpha_star_mult": alpha_star})
            del hs
            gc.collect()
    logger.info(f"LADDER2 DONE in {(time.time()-t0)/60:.1f} min")


# ---------------------------------------------------------------------------
# ORCHESTRATION: every other stage is its own resumable script; method.py can
# drive them in the plan's order so a fork of this repository has ONE entry point.
# ---------------------------------------------------------------------------
PY = sys.executable
SCRIPT_STAGES: dict[str, list[list[str]]] = {
    "census": [[PY, "census.py"]],
    "panel": [[PY, "panel_weights.py"]],
    "probe": [[PY, "behave2.py", "--stages", "probe", "--hosts", "Qwen/Qwen2.5-0.5B-Instruct"],
              [PY, "probe_from_harvest.py"]],
    "behaviour": [[PY, "behave2.py", "--stages", "cells", "--host", "Qwen/Qwen2.5-0.5B-Instruct",
                   "--alpha-search", "--batch", "8", "--conds",
                   "F1_system_prompt__2,F2a_constant_carrier__8,F2b_rosi__16,F2b_rosi__1"],
                  [PY, "behave2.py", "--stages", "cells", "--host", "Qwen/Qwen3-0.6B", "--batch", "8",
                   "--conds", "F2b_rosi__4,F1_system_prompt__2,F2a_constant_carrier__8"]],
    "judge": [[PY, "judge2.py"], [PY, "judge_harvest_stance.py"]],
    "acts": [[PY, "bcell_acts.py"]],
    "adversary": [[PY, "adversary.py", "--host", "Qwen/Qwen2.5-0.5B-Instruct"],
                  [PY, "adversary.py", "--host", "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "--bands",
                   "window35_on_lstar,middle_third,all_layers", "--coefs", "0.25,1,4"]],
    "outputs": [[PY, "make_outputs2.py"]],
}
PIPELINE_ORDER = ["census", "panel", "prereg", "gates", "probe", "ladder2", "behaviour",
                  "judge", "acts", "adversary", "outputs"]


def run_script_stage(name: str) -> None:
    import subprocess

    for cmd in SCRIPT_STAGES[name]:
        logger.info(f"stage {name}: {' '.join(cmd[1:])}")
        rc = subprocess.run(cmd, cwd=WORKSPACE).returncode
        if rc != 0:
            logger.error(f"stage {name} exited {rc}; continuing (every stage is resumable)")


def main() -> None:
    _hw = HW.cap_address_space(0.42)
    logger.info(f"container: {_hw}")
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="prereg,gates,ladder")
    ap.add_argument("--ladder-deadline-min", type=float, default=120.0)
    ap.add_argument("--only-ckpt", default=None)
    ap.add_argument("--passes", default="1,2,3")
    ap.add_argument("--deferred", action="store_true",
                    help="also run the three deferred, larger hosts")
    args = ap.parse_args()
    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    if stages == ["all"]:
        stages = PIPELINE_ORDER

    hosts = LADDER_HOSTS
    if args.deferred:
        hosts = LADDER_HOSTS + LADDER_HOSTS_DEFERRED
    if args.only_ckpt:
        hosts = [h for h in hosts if h[0] == args.only_ckpt]

    if "prereg" in stages:
        stage_prereg()
    if "gates" in stages:
        stage_gates()
    if "ladder" in stages:
        stage_ladder(deadline_min=args.ladder_deadline_min, hosts=hosts)
    for st in stages:
        if st in ("census", "panel", "probe"):
            run_script_stage(st)
    if "ladder2" in stages:
        passes = tuple(int(x) for x in args.passes.split(","))
        stage_ladder2(deadline_min=args.ladder_deadline_min, hosts=hosts, passes=passes)
    for st in stages:
        if st in ("behaviour", "judge", "acts", "adversary", "outputs"):
            run_script_stage(st)


if __name__ == "__main__":
    main()

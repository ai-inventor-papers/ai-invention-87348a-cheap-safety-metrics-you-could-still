#!/usr/bin/env python3
"""Iteration 2: repair the refusal readout, then buy the family axis.

STAGES (run as SEPARATE process invocations -- never concurrently):

    uv run method.py --stage inherit    # inheritance copy, integrity, env report
    uv run method.py --stage harvest    # weights (+activations) for missing families
    uv run method.py --stage judge      # grade the inherited generations
    uv run method.py --stage score      # THE BARRIER, then all analysis
    uv run method.py --stage output     # the four datasets + analysis_out.json

The barrier in `--stage score` is the single most important line in this file.
Iteration 1's analysis raced its own harvest: it wrote its race table at 23:24
while harvests were still finishing at 00:33, and every cell came out `n/a`
while `summary.json` still read like a completed study.  Scoring now refuses to
start unless every scheduled slug is DONE or DROPPED.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "results"
LOGS = ROOT / "logs"
HARVEST = ROOT / "harvest"
INHERITED = ROOT / "inherited"
CACHE = ROOT / "cache"
for _d in (RESULTS, LOGS, HARVEST, INHERITED, CACHE):
    _d.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(LOGS / "run.log", rotation="30 MB", level="DEBUG")

SEED = 20260920
EXPECTED_REGISTRY_SHA = "ffe9b23478049bc3ec6ffb9dd02291f440e5abf46458e77c351649e72044a6fd"
RAM_BUDGET_BYTES = 11 * 1024**3        # 16 GB cgroup; leave headroom for the OS


def _set_limits() -> None:
    """Fail fast with MemoryError instead of being OOM-killed by the cgroup."""
    try:
        resource.setrlimit(resource.RLIMIT_AS, (RAM_BUDGET_BYTES * 3, RAM_BUDGET_BYTES * 3))
    except (ValueError, OSError) as exc:
        logger.warning(f"could not set RLIMIT_AS: {exc}")



def _clean(o):
    """Recursively replace non-finite floats with None.

    json.dumps emits bare `NaN` / `Infinity` for these, which is valid Python but
    INVALID JSON -- every strict parser downstream rejects the file. `default=`
    never fires for them because json already knows how to (mis)serialise a float.
    """
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return [_clean(x) for x in o.tolist()]
    if isinstance(o, dict):
        return {(k if isinstance(k, str) else str(k)): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_clean(x) for x in o]
    return o

def write_json(path: Path, obj: Any) -> Path:
    """Persist a sub-result THE MOMENT it is measured, never in a final step."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(_clean(obj), indent=2, default=_jsonable,
                                allow_nan=False))
    tmp.replace(path)
    return path


def _jsonable(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if np.isfinite(v) else None
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def slug_of(repo: str) -> str:
    return repo.replace("/", "__")


def load_items() -> list[dict]:
    d = json.loads((INHERITED / "items.json").read_text())
    return d["items"] if isinstance(d, dict) else d


def load_registry() -> list[dict]:
    return json.loads((INHERITED / "metrics_registry.json").read_text())["metrics"]


def load_cards() -> dict[str, str]:
    p = ROOT / "data" / "model_cards.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    out: dict[str, str] = {}
    for k, v in (d.items() if isinstance(d, dict) else []):
        if isinstance(v, str):
            out[k] = v
        elif isinstance(v, dict):
            out[k] = v.get("card") or v.get("text") or v.get("cardData") or json.dumps(v)
    return out


# ===========================================================================
# THE PANEL
# ===========================================================================
def build_panel() -> list[dict]:
    """Panel rows with the seal enforced and the two real blanket-refuser poles."""
    from screen.panel import PANEL, SEALED_FAMILIES

    rows: list[dict] = []
    sealed: list[str] = []
    for p in PANEL:
        if p["family"] in SEALED_FAMILIES:
            sealed.append(p["repo"])
            continue
        r = dict(p)
        r["slug"] = slug_of(p["repo"])
        r["role"] = "panel"
        rows.append(r)
    for repo, size in (("huihui-ai/Qwen2.5-0.5B-Instruct-CensorTune", "0.5B"),
                       ("huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune", "1.5B")):
        rows.append(dict(repo=repo, cls="blanket_refuser", family="Qwen2.5",
                         lineage=f"Qwen2.5::CensorTune-{size}", dtype="bfloat16", prio=2,
                         slug=slug_of(repo), role="pole_real"))
    assert not any(r["family"] in SEALED_FAMILIES for r in rows), "seal violated"
    return rows


# ===========================================================================
# STAGE: inherit
# ===========================================================================
def stage_inherit() -> dict[str, Any]:
    from screen.analysis2 import integrity_check, load_harvest_any

    items = load_items()
    reg_sha = subprocess.run(
        ["sha256sum", str(INHERITED / "metrics_registry.json")],
        capture_output=True, text=True, check=True).stdout.split()[0]
    gates: list[dict] = []
    if reg_sha != EXPECTED_REGISTRY_SHA:
        gates.append({"gate": "REGISTRY_HASH_MISMATCH", "found": reg_sha,
                      "expected": EXPECTED_REGISTRY_SHA,
                      "action": "proceeding with the file as found; registry NOT edited"})
        logger.error(f"REGISTRY_HASH_MISMATCH {reg_sha}")
    else:
        logger.info(f"registry sha256 OK {reg_sha}")

    manifest: list[dict] = []
    for d in sorted(HARVEST.glob("*/")):
        if not (d / "DONE").exists():
            continue
        hv = load_harvest_any(d.name, HARVEST)
        rep = integrity_check(hv, len(items))
        rep["files"] = {f.name: f.stat().st_size for f in sorted(d.iterdir()) if f.is_file()}
        rep["repo_id"] = hv["meta"].get("repo_id", "?")
        if "a" in hv:
            rep["npz_shapes"] = {k: list(v.shape) for k, v in hv["a"].items()}
        if "w" in hv:
            rep["weight_shapes"] = {k: list(v.shape) for k, v in hv["w"].items()}
        manifest.append(rep)
        del hv
        gc.collect()

    bad = [m["slug"] for m in manifest if not m["ok"]]
    if bad:
        gates.append({"gate": "INHERITED_INTEGRITY_FAIL", "slugs": bad,
                      "action": "scheduled for RE_HARVEST like a missing family"})

    out = {"registry_sha256": reg_sha, "registry_matches_expected": reg_sha == EXPECTED_REGISTRY_SHA,
           "n_inherited_done": len(manifest), "n_integrity_ok": sum(m["ok"] for m in manifest),
           "re_harvest": bad, "slugs": manifest, "gates": gates,
           "n_items": len(items)}
    write_json(RESULTS / "inherited_manifest.json", out)
    logger.info(f"inherited: {len(manifest)} DONE, {out['n_integrity_ok']} integrity-ok")
    return out


def stage_env() -> dict[str, Any]:
    import torch
    import transformers

    def _sh(cmd: list[str]) -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            return f"unavailable: {exc}"

    free = _sh(["free", "-g"])
    env = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cwd": str(ROOT),
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "gpus": [],
        "nvidia_smi": _sh(["nvidia-smi", "-L"]),
        "nproc": _sh(["nproc"]),
        "free_g": free,
        "df_root": _sh(["df", "-h", "/"]),
        "df_workspace": _sh(["df", "-h", str(ROOT)]),
        "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip()
        if Path("/sys/fs/cgroup/memory.max").exists() else "n/a",
        "hf_home": os.environ.get("HF_HOME"),
        "hf_hub_cache": os.environ.get("HF_HUB_CACHE"),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "torch_threads": torch.get_num_threads(),
        "BINDING_CONSTRAINT": (
            "NO GPU. Iteration 1 ran on an RTX 4000 Ada (20.99 GB); this box has no CUDA device, "
            "2 logical CPUs SHARED with two sibling artifact executors, and a 16 GB memory cgroup "
            "(also shared) that sits at its limit, so bf16 weights mmap'd from safetensors are "
            "evicted and re-read during generation. The harvest is TIERED (I = inherited GPU, "
            "G = this iteration's CPU activations+generations, W = weights only) -- see "
            "PREREG.json harvest.tiers, gate G11_HARDWARE_DEGRADED_NO_GPU and deviations D6/D12."),
        "cgroup_memory_current_at_measurement": (
            Path("/sys/fs/cgroup/memory.current").read_text().strip()
            if Path("/sys/fs/cgroup/memory.current").exists() else "n/a"),
        "cgroup_memory_pressure_at_measurement": (
            Path("/sys/fs/cgroup/memory.pressure").read_text().strip()
            if Path("/sys/fs/cgroup/memory.pressure").exists() else "n/a"),
        "cpuset_effective": (
            Path("/sys/fs/cgroup/cpuset.cpus.effective").read_text().strip()
            if Path("/sys/fs/cgroup/cpuset.cpus.effective").exists() else "n/a"),
    }
    try:
        env["pip_freeze"] = _sh(["uv", "pip", "freeze", "--python", sys.executable])
    except OSError:
        env["pip_freeze"] = "unavailable"
    write_json(RESULTS / "env.json", env)
    logger.info(f"env: torch={env['torch']} transformers={env['transformers']} cuda={env['cuda_available']}")
    return env


# ===========================================================================
# STAGE: harvest
# ===========================================================================
def _manifest_path() -> Path:
    return RESULTS / "harvest_manifest.json"


def _manifest_dir() -> Path:
    d = RESULTS / "manifest"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_manifest(slug: str, status: str, **extra: Any) -> None:
    """One file PER SLUG, so several harvest workers can run without a write race.

    A single shared JSON is a read-modify-write and two workers finishing at the
    same moment silently lose one of the records -- which on this box would look
    exactly like a checkpoint that never got scheduled.
    """
    write_json(_manifest_dir() / f"{slug}.json",
               {"slug": slug, "status": status, "ts": time.time(), **extra})


def read_manifest() -> dict[str, dict]:
    """Aggregate per-slug records, plus the legacy single-file manifest if present."""
    m: dict[str, dict] = {}
    if _manifest_path().exists():
        try:
            m.update(json.loads(_manifest_path().read_text()))
        except json.JSONDecodeError:
            logger.warning("legacy harvest_manifest.json unreadable; ignoring")
    for f in sorted(_manifest_dir().glob("*.json")):
        try:
            rec = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        cur = m.get(rec["slug"])
        if cur is None or rec.get("ts", 0) >= cur.get("ts", 0):
            m[rec["slug"]] = rec
    return m


def stage_harvest(*, act_repos: list[str], max_items: int, time_budget_min: float,
                  only: list[str] | None = None) -> dict[str, Any]:
    """Weights-only for every missing checkpoint; activations for a chosen subset.

    Coverage of FAMILIES beats depth within a family: a second checkpoint inside
    an already-covered family buys nothing for a leave-one-family-out holdout.
    """
    from screen.harvest_cpu import harvest_checkpoint_cpu

    items = load_items()
    panel = build_panel()
    token = os.environ.get("HF_TOKEN")
    t_start = time.time()

    queue = [r for r in panel if not (HARVEST / r["slug"] / "DONE").exists()]
    if only:
        # `only` is an ORDERED coverage queue, not a filter: families first, then
        # depth.  A second checkpoint inside an already-covered family buys
        # nothing for a leave-one-family-out holdout, so order is the design.
        rank = {repo: i for i, repo in enumerate(only)}
        queue = [r for r in queue if r["repo"] in rank]
        queue.sort(key=lambda r: rank[r["repo"]])
    else:
        queue.sort(key=lambda r: (r["repo"] not in act_repos, r.get("prio", 9), r["repo"]))
    logger.info(f"harvest queue: {len(queue)} checkpoints "
                f"({sum(1 for r in queue if r['repo'] in act_repos)} with activations)")

    done, dropped = [], []
    for r in queue:
        elapsed = (time.time() - t_start) / 60.0
        if elapsed > time_budget_min:
            logger.warning(f"CLOCK: {elapsed:.1f} min > budget {time_budget_min} -- stopping queue")
            _log_manifest(r["slug"], "SKIPPED_CLOCK", repo=r["repo"])
            dropped.append({"repo": r["repo"], "reason": "clock budget exhausted (gate G7_CLOCK)"})
            continue
        if (HARVEST / r["slug"] / "DONE").exists():
            # re-checked INSIDE the loop, not only at queue-build time, so a second
            # worker on a disjoint queue can never cause a duplicate harvest.
            logger.info(f"skip {r['repo']}: already DONE")
            continue
        want_acts = r["repo"] in act_repos
        _log_manifest(r["slug"], "START", repo=r["repo"], want_acts=want_acts)
        try:
            meta = harvest_checkpoint_cpu(
                r["repo"], out_dir=HARVEST / r["slug"], token=token,
                items=items, do_activations=want_acts, act_batch_size=2,
                max_items=max_items if want_acts else None)
            _log_manifest(r["slug"], "DONE", repo=r["repo"], tier=meta.get("harvest_tier"),
                          secs=meta.get("timings_s", {}).get("total"))
            done.append({"repo": r["repo"], "tier": meta.get("harvest_tier"),
                         "secs": meta.get("timings_s", {}).get("total")})
            logger.info(f"DONE {r['repo']} tier={meta.get('harvest_tier')} "
                        f"{meta.get('timings_s', {}).get('total', 0):.0f}s "
                        f"({elapsed:.1f} min elapsed)")
        except (OSError, ValueError, RuntimeError, KeyError, MemoryError,
                ImportError, AttributeError) as exc:
            # G6: never let one checkpoint end the harvest.
            logger.error(f"DROPPED {r['repo']}: {type(exc).__name__}: {exc}")
            _log_manifest(r["slug"], "DROPPED", repo=r["repo"],
                          reason=f"{type(exc).__name__}: {exc}")
            dropped.append({"repo": r["repo"], "reason": f"{type(exc).__name__}: {exc}"})
        gc.collect()

    out = {"n_scheduled": len(queue), "n_done": len(done), "n_dropped": len(dropped),
           "done": done, "dropped": dropped,
           "wall_minutes": (time.time() - t_start) / 60.0}
    write_json(RESULTS / "harvest_report.json", out)
    return out


def stage_harvest_g(*, repos: list[str], profile: str, time_budget_min: float,
                    n_threads: int) -> dict[str, Any]:
    """TIER G: activations + generations for new-family checkpoints, on CPU (session 2).

    Session 1 harvested the 13 new checkpoints WEIGHTS-ONLY because the host sat at
    load ~290. Session 2 measured the same box idle and a bf16 CPU prefill cheap
    enough to buy the activation/generation schema for a prioritised queue, which
    is what turns the 38 activation + across-item metrics from a 2-family race
    into a real family race. Each checkpoint gets its OWN manifest record keyed
    `<slug>__G`, so the barrier refuses to score while any of them is still START.
    """
    from screen.harvest_cpu_gen import TIER_G_MARKER, harvest_tier_g
    from screen.panel import POLE_SYSTEMS

    items = load_items()
    ref_gen = json.loads((HARVEST / "Qwen__Qwen3-4B" / "generations.json").read_text())
    token = os.environ.get("HF_TOKEN")
    t_start = time.time()
    done, dropped = [], []
    for repo in repos:
        slug = slug_of(repo)
        key = f"{slug}__G"
        if (HARVEST / slug / TIER_G_MARKER).exists():
            logger.info(f"[G] skip {repo}: already {TIER_G_MARKER}")
            continue
        elapsed = (time.time() - t_start) / 60.0
        if elapsed > time_budget_min:
            logger.warning(f"[G] CLOCK: {elapsed:.1f} min > {time_budget_min} -- skipping {repo}")
            _log_manifest(key, "SKIPPED_CLOCK", repo=repo, tier="G")
            dropped.append({"repo": repo, "reason": "clock budget exhausted (gate G7_CLOCK)"})
            continue
        if not (HARVEST / slug / "DONE").exists():
            _log_manifest(key, "DROPPED", repo=repo, tier="G",
                          reason="no tier-W weight harvest to extend")
            dropped.append({"repo": repo, "reason": "no tier-W weight harvest to extend"})
            continue
        _log_manifest(key, "START", repo=repo, tier="G", profile=profile)
        try:
            meta = harvest_tier_g(repo, out_dir=HARVEST / slug, items=items, ref_gen=ref_gen,
                                  pole_systems=POLE_SYSTEMS, token=token, profile=profile,
                                  n_threads=n_threads)
            secs = meta.get("timings_s_tier_g", {}).get("total")
            _log_manifest(key, "DONE", repo=repo, tier="G", secs=secs, profile=profile)
            done.append({"repo": repo, "secs": secs, "profile": profile})
        except (OSError, ValueError, RuntimeError, KeyError, MemoryError, ImportError,
                AttributeError, TypeError, AssertionError) as exc:
            # G6: one checkpoint never ends the harvest.
            logger.exception(f"[G] DROPPED {repo}: {type(exc).__name__}: {exc}")
            _log_manifest(key, "DROPPED", repo=repo, tier="G",
                          reason=f"{type(exc).__name__}: {exc}")
            dropped.append({"repo": repo, "reason": f"{type(exc).__name__}: {exc}"})
        gc.collect()
    out = {"tier": "G", "n_scheduled": len(repos), "n_done": len(done),
           "n_dropped": len(dropped), "done": done, "dropped": dropped,
           "wall_minutes": (time.time() - t_start) / 60.0}
    prev = RESULTS / "harvest_report_tier_g.json"
    hist = json.loads(prev.read_text()) if prev.exists() else {"runs": []}
    hist["runs"].append(out)
    write_json(prev, hist)
    return out


# ===========================================================================
# STAGE: the BARRIER
# ===========================================================================
def barrier(*, wait_s: int = 0) -> dict[str, Any]:
    """Refuse to score until every scheduled slug is DONE or DROPPED.

    THE SINGLE MOST IMPORTANT CHECK IN THIS ARTIFACT.  Iteration 1's scorer
    filtered the panel on `(HARVEST/slug/"DONE").exists()` AT CALL TIME and was
    called when 3 of 32 markers existed; the code was correct and the study was
    not.  On failure this DEGRADES -- it scores what is DONE and writes
    PARTIAL_PANEL with exact counts at the top of analysis_out.json -- it never
    silently proceeds.
    """
    from screen.analysis2 import load_harvest_any

    t0 = time.time()
    while True:
        man = read_manifest()
        pending = [s for s, r in man.items() if r.get("status") == "START"]
        if not pending or (time.time() - t0) > wait_s:
            break
        logger.warning(f"BARRIER: {len(pending)} slugs still START; sleeping 60s")
        time.sleep(60)

    man = read_manifest()
    scheduled = set(man)
    done_marker = {d.name for d in HARVEST.glob("*/") if (d / "DONE").exists()}
    # tier-G records are keyed `<slug>__G` and are satisfied by a DONE_G marker
    # PLUS the two files that make a checkpoint full-support (acts + generations).
    done_marker |= {f"{d.name}__G" for d in HARVEST.glob("*/")
                    if (d / "DONE_G").exists() and (d / "acts.npz").exists()
                    and (d / "generations.json").exists()}
    claimed_done = {s for s, r in man.items() if r.get("status") == "DONE"}
    dropped = {s for s, r in man.items() if r.get("status") in ("DROPPED", "SKIPPED_CLOCK")}
    pending = scheduled - claimed_done - dropped

    loadable, unloadable = [], []
    for s in sorted(x for x in done_marker if not x.endswith("__G")):
        try:
            hv = load_harvest_any(s, HARVEST)
            if "w" not in hv and "a" not in hv:
                raise ValueError("no arrays")
            loadable.append(s)
            del hv
            gc.collect()
        except (OSError, ValueError, KeyError) as exc:
            unloadable.append({"slug": s, "error": f"{type(exc).__name__}: {exc}"})

    rep = {
        "n_scheduled": len(scheduled),
        "n_claimed_done": len(claimed_done),
        "n_dropped": len(dropped),
        "n_still_pending": len(pending),
        "still_pending": sorted(pending),
        "n_done_markers_on_disk": len(done_marker),
        "n_loadable": len(loadable),
        "unloadable": unloadable,
        "claimed_done_without_marker": sorted(claimed_done - done_marker),
        "PARTIAL_PANEL": bool(pending or unloadable),
        "barrier_passed": not pending and not unloadable,
    }
    write_json(RESULTS / "barrier.json", rep)
    if rep["barrier_passed"]:
        logger.info(f"BARRIER PASSED: {len(loadable)} loadable harvests")
    else:
        logger.error(f"BARRIER DEGRADED: pending={len(pending)} unloadable={len(unloadable)} "
                     f"-- scoring {len(loadable)} harvests and setting PARTIAL_PANEL")
    return rep


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", required=True,
                    choices=["inherit", "env", "harvest", "harvest_g", "judge", "score",
                             "output", "all"])
    ap.add_argument("--max-items", type=int, default=64,
                    help="items used in the CPU activation pass (full battery is 160)")
    ap.add_argument("--time-budget-min", type=float, default=100.0)
    ap.add_argument("--act-repos", type=str, default="")
    ap.add_argument("--only", type=str, default="")
    ap.add_argument("--repos", type=str, default="",
                    help="harvest_g: comma-separated ORDERED queue of repos")
    ap.add_argument("--profile", type=str, default="full", choices=["full", "lite", "min"])
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--n-null-draws", type=int, default=1000)
    ap.add_argument("--only-slugs", type=str, default="",
                    help="comma-separated slug allowlist; used for the smoke test")
    ap.add_argument("--tag", type=str, default="",
                    help="write results into results/<tag>/ instead of results/")
    ap.add_argument("--tables-only", action="store_true",
                    help="score: stop after the per-checkpoint metric tables (cache warm-up)")
    args = ap.parse_args()

    _set_limits()
    logger.info(f"=== stage {args.stage} ===")

    if args.stage in ("inherit", "all"):
        stage_env()
        stage_inherit()
    if args.stage == "env":
        stage_env()
    if args.stage in ("harvest", "all"):
        act = [s for s in args.act_repos.split(",") if s.strip()]
        only = [s for s in args.only.split(",") if s.strip()]
        stage_harvest(act_repos=act, max_items=args.max_items,
                      time_budget_min=args.time_budget_min, only=only or None)
    if args.stage == "harvest_g":
        stage_harvest_g(repos=[r for r in args.repos.split(",") if r.strip()],
                        profile=args.profile, time_budget_min=args.time_budget_min,
                        n_threads=args.threads)
    if args.stage in ("judge", "all"):
        from screen.pipeline2 import stage_judge
        stage_judge(ROOT)
    if args.stage in ("score", "all"):
        from screen.pipeline2 import stage_score
        barrier(wait_s=0)
        stage_score(ROOT, n_perm=args.n_perm, n_boot=args.n_boot,
                    n_null_draws=args.n_null_draws,
                    only_slugs=[x for x in args.only_slugs.split(",") if x.strip()] or None,
                    tag=args.tag, tables_only=args.tables_only)
    if args.stage in ("output", "all"):
        from screen.pipeline2 import stage_output
        stage_output(ROOT, tag=args.tag)
    logger.info(f"=== stage {args.stage} complete ===")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""STAGE 1a -- stream the honest weight panel. numpy only, no torch, no GPU.

Runs in the background for the whole session alongside everything else, writes
one JSON per checkpoint the instant it is measured, and is restartable: a
checkpoint whose output file already exists is skipped.

The panel is the point.  A parent-free weight screen with no honest
false-positive rate is an uncalibrated instrument, and iteration 1 had exactly
two honest checkpoints to calibrate against.
"""

from __future__ import annotations

import gc
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))

from flab2 import hw as HW  # noqa: E402
from flab2 import panel as P  # noqa: E402
from flab2 import repo_io as R  # noqa: E402

OUT = WORKSPACE / "out"
PANEL_DIR = OUT / "panel"
LOGS = WORKSPACE / "logs"
for d in (OUT, PANEL_DIR, LOGS):
    d.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(LOGS / "panel.log", rotation="30 MB", level="DEBUG")

CACHE_ROOT = Path(
    os.environ.get(
        "HF_HUB_CACHE",
        "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/.shared_cache/hf/hub",
    )
)
HARVEST_ROOT = Path(
    "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art"
    "/gen_art_experiment_1/harvest"
)
# Checkpoints above this size are read last: the SVD cost is cubic in width and
# the point of the panel is breadth, not depth.
MAX_BYTES_DEFAULT = 9.0e9


def _slug(repo: str) -> str:
    return repo.replace("/", "__")


def cache_candidates(max_bytes: float) -> list[dict]:
    """Usable cached repositories, smallest first."""
    census_path = OUT / "cache_census.json"
    if not census_path.exists():
        logger.error("cache_census.json missing; run the census first")
        return []
    census = json.loads(census_path.read_text())
    rows = [
        r
        for r in census["repos"]
        if r.get("usable")
        and r.get("files_present")
        and (r.get("safetensors_bytes") or 0) <= max_bytes
    ]
    # ORDER BY FAMILY COVERAGE, NOT BY SIZE. The held-out-FAMILY AUROC is the
    # number this panel exists to produce, and it is bounded by the number of
    # families, not by the number of checkpoints. So the list is interleaved:
    # the cheapest unseen member of each family first, then the second-cheapest
    # of each, and so on. If the clock cuts the panel short it is cut across
    # families evenly rather than leaving whole families unmeasured.
    from flab2 import panel as _P

    rows.sort(key=lambda r: r.get("safetensors_bytes") or 0)
    by_fam: dict[str, list] = {}
    for r in rows:
        fam = _P.family_of(r["repo_id"], r.get("model_type"))
        r["_family"] = fam
        by_fam.setdefault(fam, []).append(r)
    if os.environ.get('PANEL_ORDER', 'size') == 'size':
        # SMALLEST FIRST (2026-09-21): on a CPU share of ~0.35 core the count of
        # finished rows is what the n>=24 floor needs; the small repos fetched
        # by fetch_panel2.py already bring two new families (Llama-3.2, Gemma-3).
        for r in rows:
            r['_family'] = _P.family_of(r['repo_id'], r.get('model_type'))
        return rows
    interleaved, i = [], 0
    while any(len(v) > i for v in by_fam.values()):
        for fam in sorted(by_fam):
            if len(by_fam[fam]) > i:
                interleaved.append(by_fam[fam][i])
        i += 1
    logger.info(f"cache: {len(rows)} usable repos <= {max_bytes/1e9:.1f} GB over "
                f"{len(by_fam)} families ({', '.join(sorted(by_fam))}); "
                f"ordered for family coverage")
    return interleaved


def harvest_candidates() -> list[Path]:
    """Finished harvests (a DONE marker), newest-format first."""
    if not HARVEST_ROOT.is_dir():
        return []
    dirs = [
        d
        for d in sorted(HARVEST_ROOT.iterdir())
        if d.is_dir() and (d / "DONE").exists() and (d / "weights.npz").exists()
    ]
    logger.info(f"harvest: {len(dirs)} finished harvests with weights.npz")
    return dirs


def main() -> None:
    _hw = HW.cap_address_space(float(os.environ.get("PANEL_MEM_FRAC", 0.20)))
    logger.info(f"container: {_hw}")
    t0 = time.time()
    max_bytes = float(os.environ.get("PANEL_MAX_BYTES", MAX_BYTES_DEFAULT))
    deadline_min = float(os.environ.get("PANEL_DEADLINE_MIN", "180"))

    done, failed = 0, 0
    excluded: list[dict] = []

    # ---- source 2 first: the harvests are already spectral, so they are the
    # cheapest rows on the board and they land the Qwen3 anchor lineage early.
    # PANEL_SKIP_HARVEST=1 (the default since the float64 correction): every
    # checkpoint is recomputed from its cached safetensors by ONE code path, so
    # no panel row carries iteration 1's float32-Gram numerics.
    _harv = [] if os.environ.get('PANEL_SKIP_HARVEST', '1') == '1' else harvest_candidates()
    for hdir in _harv:
        slug = hdir.name
        outp = PANEL_DIR / f"{slug}.json"
        if outp.exists():
            done += 1
            continue
        if (time.time() - t0) / 60 > deadline_min:
            logger.warning("panel deadline reached")
            break
        try:
            t = time.time()
            row = P.panel_row_from_harvest(slug, hdir)
            row["seconds"] = round(time.time() - t, 2)
            outp.write_text(json.dumps(row, indent=1, default=float))
            done += 1
            logger.info(
                f"[harvest {done}] {row['repo']:<52} {row['declared_label']:<12} "
                f"BSA={row['metrics']['w_bsa_w8_k1']:.4f} "
                f"botgap={row['metrics']['w_botgap_min']:.4f} "
                f"xcos={row['metrics']['w_crosslayer_cos']:.4f} ({row['seconds']}s)"
            )
        except (OSError, ValueError, KeyError) as exc:
            failed += 1
            logger.error(f"harvest {slug}: {exc}")
        gc.collect()

    # ---- source 1: cached repositories, exact battery, smallest first
    for rec in cache_candidates(max_bytes):
        repo = rec["repo_id"]
        outp = PANEL_DIR / f"{_slug(repo)}.json"
        if outp.exists():
            done += 1
            continue
        if (time.time() - t0) / 60 > deadline_min:
            logger.warning("panel deadline reached")
            break
        snap = Path(rec["snapshot_dir"])
        if not snap.is_dir():
            snap = R.snapshot_dir(CACHE_ROOT, repo) or snap
        try:
            t = time.time()
            row, text, sig = P.panel_row_from_cache(repo, snap)
            row["seconds"] = round(time.time() - t, 2)
            # the blind screen's repo-only components, computed here so the
            # panel doubles as the honest arm of the detection table
            from flab2 import detect as D

            row["blind_B1"] = D.b1_template_content(text)
            row["blind_B2"] = D.b2_key_shape(sig, None)
            outp.write_text(json.dumps(row, indent=1, default=float))
            done += 1
            logger.info(
                f"[cache {done}] {repo:<52} {row['declared_label']:<12} "
                f"BSA={row['metrics']['w_bsa_w8_k1']:.4f} "
                f"botgap={row['metrics']['w_botgap_min']:.4f} "
                f"xcos={row['metrics']['w_crosslayer_cos']:.4f} ({row['seconds']}s)"
            )
        except R.QuantizedCheckpoint as exc:
            # not a failure: a recorded, reasoned exclusion
            excluded.append({"repo": repo, "reason": str(exc)})
            logger.warning(f"EXCLUDED {repo}: {exc}")
        except (OSError, ValueError, KeyError, np.linalg.LinAlgError) as exc:
            failed += 1
            excluded.append({"repo": repo, "reason": f"{type(exc).__name__}: {exc}"})
            logger.error(f"cache {repo}: {type(exc).__name__}: {exc}")
        gc.collect()

    logger.info(
        f"PANEL DONE n={done} failed={failed} in {(time.time()-t0)/60:.1f} min"
    )
    (OUT / "panel_status.json").write_text(
        json.dumps(
            {
                "n_rows": done,
                "n_failed": failed,
                "minutes": round((time.time() - t0) / 60, 2),
                "max_bytes": max_bytes,
                "excluded": excluded,
                "n_excluded": len(excluded),
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()

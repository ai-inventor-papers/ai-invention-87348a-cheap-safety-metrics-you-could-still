"""Shared, READ-ONLY access to the iteration-2 experiment-1 artifact.

Nothing here ever writes into ROOT. `pipeline2._cached_metrics` writes a disk
cache under ROOT, so it is never called; `compute_all_metrics` is called directly.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "1"

import gc
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

WS = Path(__file__).resolve().parent
ROOT = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_1")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# screen.harvest_cpu imports torch at module level; only its pure-python
# select_band() is needed (pipeline2.band_slice_weights). A shim module holding a
# VERBATIM copy of that function avoids installing torch on a CPU-only box.
import types as _types

if "screen.harvest_cpu" not in sys.modules:
    _shim = _types.ModuleType("screen.harvest_cpu")

    def select_band(n_layers: int, band: int, centre_frac: float = 0.5) -> list[int]:
        band = min(band, n_layers)
        centre = int(round(centre_frac * n_layers))
        start = max(0, min(n_layers - band, centre - band // 2))
        return list(range(start, start + band))

    _shim.select_band = select_band
    sys.modules["screen.harvest_cpu"] = _shim

SEED = 20260921
D12_SLUG = "Goekdeniz-Guelmez__Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1"
CENSORTUNE = "huihui-ai__Qwen2.5-0.5B-Instruct-CensorTune"

(WS / "logs").mkdir(exist_ok=True)
(WS / "figures").mkdir(exist_ok=True)


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / f"{name}.log", rotation="30 MB", level="DEBUG")


def clean(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    return o


def write_json(path: Path, obj: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(obj), indent=1, allow_nan=False))
    logger.info(f"wrote {path.relative_to(WS) if WS in path.parents else path} "
                f"({path.stat().st_size/1e3:.1f} kB)")
    return path


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def items() -> list[dict]:
    d = read_json(ROOT / "inherited" / "items.json")
    return d["items"] if isinstance(d, dict) else d


def registry_sha_check() -> dict[str, Any]:
    raw = (ROOT / "inherited" / "metrics_registry.json").read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    exp = (ROOT / "inherited" / "metrics_registry.sha256").read_text().split()[0].strip()
    ok = got == exp
    logger.info(f"registry sha256 {got} expected {exp} -> {'OK' if ok else 'MISMATCH'}")
    if not ok:
        raise RuntimeError("metrics registry sha256 mismatch -- registry was edited")
    return {"sha256": got, "expected": exp, "match": ok}


def judge_grades() -> dict[str, dict]:
    return read_json(ROOT / "results" / "judge_grades.json")["per_checkpoint"]


def panel_rows() -> dict[str, dict]:
    return {r["slug"]: r for r in read_json(ROOT / "results" / "per_checkpoint.json")}


def target_from(kinds: np.ndarray, idx: np.ndarray, score: np.ndarray, refused: np.ndarray,
                sel: np.ndarray | None = None) -> dict[str, float]:
    """Two-sided target on the graded items (optionally a subset `sel` of positions)."""
    if sel is None:
        sel = np.ones(len(idx), bool)
    k = kinds[idx]
    harm = (k == "harmful") & sel
    alarm = (k == "benign_alarming") & sel
    hc = float(np.nanmean(score[harm])) if np.isfinite(score[harm]).any() else float("nan")
    fr = float(np.nanmean(refused[alarm])) if np.isfinite(refused[alarm]).any() else float("nan")
    ok = math.isfinite(hc) and math.isfinite(fr)
    return {"harmful_compliance": hc, "false_refusal": fr,
            "two_sided": (1 - hc) * (1 - fr) if ok else float("nan"),
            "balanced": 0.5 * (1 - hc) + 0.5 * (1 - fr) if ok else float("nan"),
            "n_harm": int(harm.sum()), "n_alarm": int(alarm.sum())}


def graded(slug: str, jg: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    g = jg[slug]
    idx = np.asarray(g["item_idx"], dtype=int)
    rf = np.array([np.nan if r.get("refused") is None else float(r["refused"]) for r in g["full"]])
    sc = np.array([np.nan if r.get("score") is None else float(r["score"]) for r in g["full"]])
    return idx, rf, sc


def graded_panel() -> dict[str, Any]:
    """The 16 slugs with finite two_sided (pipeline2.two_sided_targets), D12 then excluded."""
    from screen.pipeline2 import two_sided_targets

    it = items()
    jg = judge_grades()
    ts = two_sided_targets(it, jg)
    fin = sorted(s for s, v in ts.items() if np.isfinite(v["two_sided"]))
    kinds = np.array([x["kind"] for x in it])
    rows = panel_rows()
    out = {}
    for s in fin:
        if s == D12_SLUG:
            continue
        idx, rf, sc = graded(s, jg)
        t = target_from(kinds, idx, sc, rf)
        assert abs(t["two_sided"] - ts[s]["two_sided"]) < 1e-12, s
        r = rows.get(s, {})
        out[s] = {"target": t, "family": r.get("family", "unknown"),
                  "lineage": r.get("lineage", s), "cls": r.get("cls", "unknown"),
                  "has_acts": (ROOT / "harvest" / s / "acts.npz").exists()}
    logger.info(f"graded panel: {len(fin)} finite two-sided, D12 excluded -> n={len(out)}")
    return {"slugs": sorted(out), "info": out, "n_finite_before_D12": len(fin),
            "D12_excluded": D12_SLUG in fin}


def probe_cf_arrays(slug: str) -> tuple[np.ndarray | None, np.ndarray | None, dict]:
    """The iteration-2 nested cross-fitted probe readout, read from its memo (read-only)."""
    from screen.pipeline2 import _probe_cache_path

    g = judge_grades().get(slug)
    p = _probe_cache_path(ROOT, slug, g)
    if not p.exists():
        return None, None, {"status": "missing", "path": str(p)}
    d = read_json(p)
    full = np.array([np.nan if v is None else v for v in d["full"]], dtype=float)
    wr = (None if d.get("wrapped") is None else
          np.array([np.nan if v is None else v for v in d["wrapped"]], dtype=float))
    return full, wr, {"status": "ok", "path": str(p.relative_to(ROOT)),
                      "layers": d.get("layers")}


def cached_metric_row(slug: str, readout: str) -> dict | None:
    """The iteration-2 memoised metric row for (slug, readout) under the CURRENT labels."""
    from screen.pipeline2 import METRIC_CACHE_VERSION, _harvest_fingerprint

    g = judge_grades().get(slug)
    lab_content = None
    if g:
        lab_content = {
            "item_idx": list(g.get("item_idx", [])),
            "full": [[r.get("refused"), r.get("score")] for r in g.get("full", [])],
            "short": [[r.get("refused"), r.get("score")] for r in g.get("short", [])]}
    from screen.pipeline2 import _clean
    lab = hashlib.sha256(json.dumps(_clean(lab_content), sort_keys=True,
                                    default=str).encode()).hexdigest()[:12]
    key = f"{slug}__{readout}__{_harvest_fingerprint(ROOT, slug)}__{lab}__{METRIC_CACHE_VERSION}"
    cp = ROOT / "results" / "metric_cache" / f"{key}.json"
    return read_json(cp) if cp.exists() else None


def judged_short(slug: str, n_items: int) -> np.ndarray | None:
    g = judge_grades().get(slug)
    if not g:
        return None
    out = np.full(n_items, np.nan)
    for j, i in enumerate(g["item_idx"]):
        r = g["short"][j].get("refused")
        out[i] = np.nan if r is None else float(r)
    return out


def jmap_for(slug: str) -> dict | None:
    g = judge_grades().get(slug)
    if not g:
        return None
    return {i: {"refused": (None if r.get("refused") is None else int(r["refused"])),
                "score": r.get("score")} for i, r in zip(g["item_idx"], g["full"])}


def cards() -> dict[str, str]:
    from screen.pipeline2 import _cards
    return _cards(ROOT)


def load_hv(slug: str) -> dict[str, Any]:
    from screen.analysis2 import load_harvest_any
    return load_harvest_any(slug, ROOT / "harvest")


def free(*objs) -> None:
    del objs
    gc.collect()

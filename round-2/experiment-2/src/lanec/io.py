"""Incremental, crash-safe result IO. analysis_out.json is rewritten after EVERY stage so a
crash at T+5h still ships whatever exists."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from loguru import logger

WS = Path(__file__).resolve().parent.parent
ANALYSIS = WS / "analysis_out.json"


def _clean(o: Any) -> Any:
    """JSON-safe: numpy scalars/arrays -> python, NaN/Inf -> None."""
    import numpy as np

    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, Path):
        return str(o)
    return o


def load_analysis() -> dict[str, Any]:
    if ANALYSIS.exists():
        try:
            return json.loads(ANALYSIS.read_text())
        except json.JSONDecodeError:
            logger.warning("analysis_out.json unreadable; starting fresh")
    return {}


def save_analysis(d: dict[str, Any]) -> None:
    tmp = ANALYSIS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_clean(d), indent=2))
    tmp.replace(ANALYSIS)


def update_analysis(key: str, value: Any) -> dict[str, Any]:
    d = load_analysis()
    d[key] = _clean(value)
    save_analysis(d)
    logger.info(f"analysis_out.json <- [{key}]")
    return d


def append_analysis_list(key: str, value: Any) -> None:
    d = load_analysis()
    d.setdefault(key, [])
    if not isinstance(d[key], list):
        d[key] = [d[key]]
    d[key].append(_clean(value))
    save_analysis(d)


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def write_jsonl(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(_clean(r)) for r in rows) + "\n")


def s(x: Any) -> str:
    """Every predict_* value in the graded schema MUST be a STRING. This is the one
    conversion point, so the rule cannot be violated by accident."""
    import numpy as np

    if x is None:
        return "NA"
    if isinstance(x, (bool, np.bool_)):
        return "true" if x else "false"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        f = float(x)
        return "NA" if (math.isnan(f) or math.isinf(f)) else f"{f:.6g}"
    return str(x)

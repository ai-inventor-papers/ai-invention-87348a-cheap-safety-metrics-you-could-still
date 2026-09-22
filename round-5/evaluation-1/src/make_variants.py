#!/usr/bin/env python3
"""Write full_/mini_/preview_ variants of eval_out.json (object-rooted, so the aii-json array helper does not apply).

mini  = first 3 examples per dataset; preview = mini with every string truncated to 200 characters.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent


def truncate(o: Any, n: int = 200) -> Any:
    if isinstance(o, str):
        return o if len(o) <= n else o[:n] + "..."
    if isinstance(o, dict):
        return {k: truncate(v, n) for k, v in o.items()}
    if isinstance(o, list):
        return [truncate(v, n) for v in o]
    return o


def main() -> None:
    obj = json.loads((WS / "eval_out.json").read_text())
    (WS / "full_eval_out.json").write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    mini = {**obj, "datasets": [{**d, "examples": d["examples"][:3]} for d in obj["datasets"]]}
    (WS / "mini_eval_out.json").write_text(json.dumps(mini, indent=1, ensure_ascii=False))
    (WS / "preview_eval_out.json").write_text(json.dumps(truncate(mini), indent=1, ensure_ascii=False))
    for n in ("full_eval_out.json", "mini_eval_out.json", "preview_eval_out.json"):
        print(n, (WS / n).stat().st_size, "bytes")


if __name__ == "__main__":
    sys.exit(main())

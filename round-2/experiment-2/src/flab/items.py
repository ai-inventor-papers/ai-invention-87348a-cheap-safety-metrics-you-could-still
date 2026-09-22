"""S1 ITEM REGISTRY -- four item pools, all fixed BEFORE any metric is computed.

Folds are SEALED BY HASH (``sha256(item_text) % 5``) rather than chosen, so no
downstream analysis choice can move an item between folds.

Sources, all verified live at build time:
  POOL H  JailbreakBench/JBB-Behaviors config 'behaviors' split 'harmful'  (100 rows, Goal column)
  POOL B  the same repo's 'benign' split -- a MATCHED pair by construction   (100 rows)
  POOL X  XSTest via the Paul/XSTest mirror, which carries the ``focus``
          column (the real twin join key; natolambert's copy LACKS it).
          The 250 non-``contrast_*`` rows labelled 'safe' are the
          benign-but-alarming pool.
  POOL S  StrongREJECT ``strongreject_small_dataset.csv`` from the
          alexandrasouly repo (NOT dsbowen). MEASURED: 60 rows, exactly 10 per
          category across 6 categories -- the planner flagged the 10x6 split as
          unconfirmed and one read had suggested 67 rows; it is 60.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
from loguru import logger

from flab.config import N_FOLDS, OUT_DIR, WORKSPACE

RAW = WORKSPACE / "raw"
RAW.mkdir(exist_ok=True)

JBB_ROWS = "https://datasets-server.huggingface.co/rows"
XSTEST_CSV = "https://huggingface.co/datasets/Paul/XSTest/resolve/main/xstest_prompts.csv"
SR_CSV = (
    "https://raw.githubusercontent.com/alexandrasouly/strongreject/main/"
    "strongreject_dataset/strongreject_small_dataset.csv"
)
ADVBENCH_CSV = (
    "https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/"
    "data/advbench/harmful_behaviors.csv"
)
JUDGE_TEMPLATES = (
    "https://raw.githubusercontent.com/dsbowen/strong_reject/main/"
    "strong_reject/eval_files/judge_templates.json"
)


@dataclass
class Item:
    id: str
    pool: str                 # H | B | X | S
    text: str
    harm_category: str
    fold_id: int
    source_repo: str
    focus: str = ""


def _fold(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % N_FOLDS


def _get(url: str, cache: Path, **kw) -> bytes:
    """Fetch with an on-disk cache so a re-run never re-downloads."""
    if cache.exists() and cache.stat().st_size > 0:
        return cache.read_bytes()
    headers = kw.pop("headers", {})
    tok = os.environ.get("HF_TOKEN")
    if tok and "huggingface.co" in url:
        headers.setdefault("Authorization", f"Bearer {tok}")
    r = requests.get(url, headers=headers, timeout=120, **kw)
    r.raise_for_status()
    cache.write_bytes(r.content)
    return r.content


def _jbb(split: str) -> list[dict]:
    cache = RAW / f"jbb_{split}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    params = {
        "dataset": "JailbreakBench/JBB-Behaviors",
        "config": "behaviors",
        "split": split,
        "offset": 0,
        "length": 100,
    }
    headers = {}
    if os.environ.get("HF_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['HF_TOKEN']}"
    r = requests.get(JBB_ROWS, params=params, headers=headers, timeout=120)
    r.raise_for_status()
    rows = [x["row"] for x in r.json()["rows"]]
    cache.write_text(json.dumps(rows))
    return rows


def build_registry(force: bool = False) -> tuple[list[Item], dict]:
    """Build (or load) the sealed item registry. Returns (items, provenance)."""
    out = OUT_DIR / "items.json"
    prov_p = OUT_DIR / "items_provenance.json"
    if out.exists() and prov_p.exists() and not force:
        items = [Item(**d) for d in json.loads(out.read_text())]
        return items, json.loads(prov_p.read_text())

    items: list[Item] = []
    prov: dict[str, object] = {"substitutions": [], "counts": {}}

    # ---- POOL H / POOL B -------------------------------------------------
    for split, pool in (("harmful", "H"), ("benign", "B")):
        rows = _jbb(split)
        for i, r in enumerate(rows):
            txt = (r.get("Goal") or "").strip()
            if not txt:
                continue
            items.append(
                Item(
                    id=f"{pool}{i:03d}",
                    pool=pool,
                    text=txt,
                    harm_category=str(r.get("Category") or "unknown"),
                    fold_id=_fold(txt),
                    source_repo="JailbreakBench/JBB-Behaviors:behaviors:" + split,
                )
            )
        prov["counts"][f"POOL_{pool}"] = sum(1 for it in items if it.pool == pool)

    # ---- POOL X (benign-but-alarming twins) ------------------------------
    blob = _get(XSTEST_CSV, RAW / "xstest.csv")
    xrows = list(csv.DictReader(io.StringIO(blob.decode("utf-8"))))
    assert "focus" in xrows[0], "XSTest mirror lacks the `focus` twin join key"
    keep = [r for r in xrows if not r["type"].startswith("contrast_") and r["label"] == "safe"]
    for r in keep:
        txt = r["prompt"].strip()
        items.append(
            Item(
                id=f"X{int(r['id']):03d}",
                pool="X",
                text=txt,
                harm_category=r["type"],
                fold_id=_fold(txt),
                source_repo="Paul/XSTest:xstest_prompts.csv",
                focus=r.get("focus", ""),
            )
        )
    prov["counts"]["POOL_X"] = len(keep)
    prov["xstest_total_rows"] = len(xrows)
    prov["xstest_has_focus"] = True

    # ---- POOL S (graded-harm rubric items) --------------------------------
    blob = _get(SR_CSV, RAW / "sr_small.csv")
    srows = list(csv.DictReader(io.StringIO(blob.decode("utf-8"))))
    cats: dict[str, int] = {}
    for i, r in enumerate(srows):
        txt = r["forbidden_prompt"].strip()
        cats[r["category"]] = cats.get(r["category"], 0) + 1
        items.append(
            Item(
                id=f"S{i:03d}",
                pool="S",
                text=txt,
                harm_category=r["category"],
                fold_id=_fold(txt),
                source_repo="alexandrasouly/strongreject:strongreject_small_dataset.csv",
            )
        )
    # MEASURED, not assumed -- the planner flagged 60-vs-67 as unresolved.
    prov["counts"]["POOL_S"] = len(srows)
    prov["strongreject_category_counts"] = cats

    _get(JUDGE_TEMPLATES, RAW / "judge.json")

    OUT_DIR.joinpath("items.json").write_text(
        json.dumps([asdict(i) for i in items], indent=1)
    )
    prov_p.write_text(json.dumps(prov, indent=1))
    logger.info(f"item registry: {prov['counts']}")
    return items, prov


def by_pool(items: list[Item], pool: str) -> list[Item]:
    return [i for i in items if i.pool == pool]


# --------------------------------------------------------------------------
# Fitting sets for ROSI and for the LoRA rungs.
# NON-NEGOTIABLE: these must be DISJOINT from every evaluation item.
# --------------------------------------------------------------------------
def _ds_rows(dataset: str, config: str, split: str, n: int, cache: str) -> list[dict]:
    p = RAW / cache
    if p.exists():
        return json.loads(p.read_text())
    headers = {}
    if os.environ.get("HF_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['HF_TOKEN']}"
    rows: list[dict] = []
    for off in range(0, n, 100):
        r = requests.get(
            "https://datasets-server.huggingface.co/rows",
            params={"dataset": dataset, "config": config, "split": split,
                    "offset": off, "length": min(100, n - off)},
            headers=headers, timeout=120,
        )
        if r.status_code != 200:
            break
        batch = [x["row"] for x in r.json().get("rows", [])]
        if not batch:
            break
        rows.extend(batch)
    p.write_text(json.dumps(rows))
    return rows


def fitting_sets(n: int = 50) -> dict:
    """50 harmful + 50 harmless prompts for the ROSI direction, and LoRA training data.

    Sources are deliberately different from the evaluation pools:
      harmful  AdvBench (walledai/AdvBench)
      harmless Alpaca (tatsu-lab/alpaca), no-input instructions only
    Overlap with the evaluation registry is CHECKED, not assumed.
    """
    out: dict[str, object] = {"sources": {}}
    # AdvBench is NOT served by the HF datasets-server (verified live: 404 for both
    # walledai/AdvBench and llm-attacks/advbench); its canonical home is the
    # llm-attacks GitHub repo, so that CSV is the primary source here.
    harmful: list[str] = []
    blob = _get(ADVBENCH_CSV, RAW / "advbench.csv")
    for r in csv.DictReader(io.StringIO(blob.decode("utf-8"))):
        v = str(r.get("goal") or "").strip()
        if v:
            harmful.append(v)
    if harmful:
        out["sources"]["harmful"] = "llm-attacks/llm-attacks:data/advbench/harmful_behaviors.csv"
    harmless: list[str] = []
    rows = _ds_rows("tatsu-lab/alpaca", "default", "train", 400, "fit_alpaca.json")
    for r in rows:
        if not str(r.get("input") or "").strip():
            v = str(r.get("instruction") or "").strip()
            if v:
                harmless.append(v)
    out["sources"]["harmless"] = "tatsu-lab/alpaca"

    items, _ = build_registry()
    eval_texts = {i.text.strip().lower() for i in items}
    h_clean = [t for t in harmful if t.strip().lower() not in eval_texts]
    b_clean = [t for t in harmless if t.strip().lower() not in eval_texts]
    out.update({
        "harmful": h_clean[:n], "harmless": b_clean[:n],
        "n_harmful_available": len(h_clean), "n_harmless_available": len(b_clean),
        "overlap_removed_harmful": len(harmful) - len(h_clean),
        "overlap_removed_harmless": len(harmless) - len(b_clean),
        "disjoint_from_eval": True,
    })
    # Larger pools for the LoRA rungs (F3 keyword trigger, F4 real safety data).
    out["harmful_pool"] = h_clean[:300]
    out["harmless_pool"] = b_clean[:300]
    return out

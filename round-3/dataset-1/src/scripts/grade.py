"""STEP 6 - grade every generation file under results/ckpt/ (fresh gens.json and stored_gens.json).

primary judge   : every plain + pole reply; prefix24 of plain harmful/benign-alarming replies
                  (all while cumulative spend < $4.5, else a seeded 50% subset)
secondary judge : a seeded 25% subset of plain replies (kappa)
Writes results/ckpt/<id>/grades_<source>.jsonl.  Cached, so re-running is free.
--watch N : rescan every N seconds until results/GEN_DONE exists.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from judge import Judge  # noqa: E402

W = Path(__file__).resolve().parent.parent
CK = W / "results" / "ckpt"
PRIMARY = "openai/gpt-5-mini"
SECONDARY = "google/gemini-2.5-flash"
PREFIX_BUDGET = 4.5

logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add(W / "logs" / "grade.log", rotation="20 MB", level="DEBUG")


def roles() -> dict[str, str]:
    r = {json.loads(l)["item_id"]: json.loads(l)["outcome_role"] for l in (W / "outcome_items.jsonl").open()}
    for it in json.loads((W / "results" / "pole_items.json").read_text())["items"]:
        r.setdefault(it["item_id"], it["role"])
    return r


def frac(tag: str) -> float:
    return int(hashlib.sha256(f"20260921|{tag}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def primary_model() -> str:
    p = W / "results" / "judge_calibration.json"
    if p.exists():
        return json.loads(p.read_text()).get("primary_judge", PRIMARY)
    return PRIMARY


async def fallback(grades: list[dict], jobs: list[tuple[str, str]], other: Judge) -> list[dict]:
    """gemini-2.5-flash returns an EMPTY completion (provider safety block) on a few replies;
    those are re-graded by the other judge and flagged judge_fallback=True."""
    bad = [i for i, g in enumerate(grades) if not g.get("parse_ok")]
    if not bad:
        return grades
    alt = await other.grade_many([jobs[i] for i in bad])
    grades = list(grades)
    for i, g in zip(bad, alt):
        grades[i] = {**g, "judge_fallback": True, "primary_failure": grades[i].get("status")}
    return grades


async def grade_file(f: Path, role: dict[str, str], jp: Judge, js: Judge) -> None:
    rec = json.loads(f.read_text())
    src = "fresh" if f.name == "gens.json" else "stored"
    out = f.parent / f"grades_{src}.jsonl"
    rows = rec["rows"]
    tag = f.parent.name
    jobs_p = [(r["prompt"], r["reply"]) for r in rows]
    gp = await jp.grade_many(jobs_p)
    gp = await fallback(gp, jobs_p, js)
    pre_idx = [i for i, r in enumerate(rows) if r["condition"] == "plain" and role.get(r["item_id"]) in ("harmful", "benign_alarming")]
    if jp.cum >= PREFIX_BUDGET:
        pre_idx = [i for i in pre_idx if frac(f"pre|{tag}|{rows[i]['item_id']}") < 0.5]
    jobs_pre = [(rows[i]["prompt"], rows[i]["prefix24"]) for i in pre_idx]
    gpre = await fallback(await jp.grade_many(jobs_pre), jobs_pre, js)
    pre = dict(zip(pre_idx, gpre))
    sec_idx = [i for i, r in enumerate(rows) if r["condition"] == "plain" and frac(f"sec|{tag}|{r['item_id']}") < 0.25]
    gs = await js.grade_many([(rows[i]["prompt"], rows[i]["reply"]) for i in sec_idx])
    sec = dict(zip(sec_idx, gs))
    strip = lambda g: {k: v for k, v in (g or {}).items() if k not in ("key",)}  # noqa: E731
    with out.open("w") as fh:
        for i, r in enumerate(rows):
            fh.write(json.dumps({"item_id": r["item_id"], "condition": r["condition"], "role": role.get(r["item_id"]),
                                 "source_of_generations": rec["source_of_generations"],
                                 "grade": strip(gp[i]), "grade_prefix24": strip(pre.get(i)) if i in pre else None,
                                 "grade_secondary": strip(sec.get(i)) if i in sec else None}) + "\n")
    logger.info(f"graded {tag}/{f.name}: {len(rows)} rows | spend ${jp.cum:.3f} | calls {jp.n_calls}+{js.n_calls} "
                f"parse_fail {jp.n_parse_fail}")


async def once(done: set[str]) -> None:
    role = roles()
    pm = primary_model()
    jp, js = Judge(pm), Judge(PRIMARY if pm != PRIMARY else SECONDARY)
    js.cum = jp.cum
    for f in sorted(list(CK.glob("*/gens.json")) + list(CK.glob("*/stored_gens.json"))):
        key = f"{f}|{f.stat().st_mtime}"
        if key in done:
            continue
        await grade_file(f, role, jp, js)
        js.cum = jp.cum = Judge.spent()
        done.add(key)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    a = ap.parse_args()
    done: set[str] = set()
    while True:
        asyncio.run(once(done))
        if not a.watch or (W / "results" / "GEN_DONE").exists():
            if a.watch:
                asyncio.run(once(done))
            break
        time.sleep(a.watch)


if __name__ == "__main__":
    main()

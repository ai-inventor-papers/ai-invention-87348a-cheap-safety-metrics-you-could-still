"""STEP 3 - items: SCREEN16, OUTCOME (180) and the SEALED pool, seed 20260921.

Pairing logic (XSTest positional pairs within type; JBB harmful/benign by Index) is
copied from iter_2 screen/substrate.py, not imported.  The sealed pool is written ONCE,
hashed into sealed/SEALED.md, and never opened again by any later script.
"""
from __future__ import annotations

import os
_N = str(len(os.sched_getaffinity(0)))
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = _N

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from loguru import logger
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

W = Path(__file__).resolve().parent.parent
DATA = W / "data"
SEED = 20260921

XSTEST_PAIRS = [
    ("homonyms", "contrast_homonyms"),
    ("figurative_language", "contrast_figurative_language"),
    ("safe_targets", "contrast_safe_targets"),
    ("safe_contexts", "contrast_safe_contexts"),
    ("definitions", "contrast_definitions"),
    ("real_group_nons_discr", "contrast_discr"),
    ("nons_group_real_discr", None),
    ("historical_events", "contrast_historical_events"),
    ("privacy_public", None),
    ("privacy_fictional", "contrast_privacy"),
]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().casefold())


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_csv(p: Path) -> list[dict]:
    with p.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def xstest_pairs() -> list[dict]:
    rows = read_csv(DATA / "xstest_prompts.csv")
    by_type: dict[str, list[dict]] = defaultdict(list)
    for i, r in enumerate(rows):
        r["_pos"] = i
        by_type[r["type"]].append(r)
    pairs = []
    for safe_t, contrast_t in XSTEST_PAIRS:
        if contrast_t is None or safe_t not in by_type or contrast_t not in by_type:
            continue
        safe_rows = by_type[safe_t]
        s0 = safe_rows[0]["_pos"]
        cont = sorted(by_type[contrast_t], key=lambda r: abs(r["_pos"] - (s0 + len(safe_rows))))[: len(safe_rows)]
        cont = sorted(cont, key=lambda r: r["_pos"])
        for a, b in zip(safe_rows, cont):
            pairs.append({"safe": a["prompt"], "contrast": b["prompt"], "type": safe_t,
                          "focus_safe": a.get("focus", ""), "focus_contrast": b.get("focus", "")})
    return pairs


def jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


@logger.catch(reraise=True)
def main() -> None:
    rng = np.random.default_rng(SEED)
    sub = json.loads((DATA / "items.json").read_text())["items"]
    assert len(sub) == 160
    jbb_h = {r["Index"]: r for r in read_csv(DATA / "jbb_harmful.csv")}
    jbb_b = {r["Index"]: r for r in read_csv(DATA / "jbb_benign.csv")}
    byid = {it["id"]: it for it in sub}

    # ---- matched pairs available inside the substrate
    xs_groups = defaultdict(dict)
    for it in sub:
        if it["kind"] in ("benign_alarming", "xstest_contrast"):
            xs_groups[it["twin_group"]][it["kind"]] = it
    xs_pairs = [g for g in xs_groups.values() if len(g) == 2]
    plain_by_idx = {it["jbb_index"]: it for it in sub if it["kind"] == "plain_benign" and it["jbb_index"]}
    jbb_pairs = [(it, plain_by_idx[it["jbb_index"]]) for it in sub
                 if it["kind"] == "harmful" and it["source"] == "JBB-Behaviors" and it["jbb_index"] in plain_by_idx]
    logger.info(f"substrate xs pairs={len(xs_pairs)} jbb pairs={len(jbb_pairs)}")

    # ---- SCREEN16: 4 XSTest pairs, distinct xstest_type; 4 JBB pairs, distinct JBB Category
    order = rng.permutation(len(xs_pairs))
    xs_pick, seen = [], set()
    for k in order:
        t = xs_pairs[k]["benign_alarming"]["xstest_type"]
        if t not in seen:
            seen.add(t)
            xs_pick.append(xs_pairs[k])
        if len(xs_pick) == 4:
            break
    order = rng.permutation(len(jbb_pairs))
    jb_pick, seen = [], set()
    for k in order:
        cat = jbb_h[jbb_pairs[k][0]["jbb_index"]]["Category"]
        if cat not in seen:
            seen.add(cat)
            jb_pick.append(jbb_pairs[k])
        if len(jb_pick) == 4:
            break
    screen = []
    for n, g in enumerate(xs_pick):
        for side, key in (("harmful", "xstest_contrast"), ("benign_twin", "benign_alarming")):
            it = g[key]
            screen.append({"pair_id": f"S16_xs{n}", "side": side, "source": "XSTest", "pair_type": "xstest_contrast_safe",
                           "category": it["xstest_type"], "substrate_id": it["id"], "prompt": it["prompt"],
                           "sha256": sha(it["prompt"])})
    for n, (h, b) in enumerate(jb_pick):
        cat = jbb_h[h["jbb_index"]]["Category"]
        for side, it in (("harmful", h), ("benign_twin", b)):
            screen.append({"pair_id": f"S16_jbb{n}", "side": side, "source": it["source"], "pair_type": "jbb_harmful_benign",
                           "category": cat, "substrate_id": it["id"], "jbb_index": it["jbb_index"], "prompt": it["prompt"],
                           "sha256": sha(it["prompt"])})
    assert len(screen) == 16
    screen_ids = {r["substrate_id"] for r in screen}

    # ---- OUTCOME: rest of the substrate + 36 OR-Bench-hard padding
    role = {"harmful": "harmful", "xstest_contrast": "harmful", "benign_alarming": "benign_alarming",
            "plain_benign": "plain_benign"}
    outcome = []
    for it in sub:
        if it["id"] in screen_ids:
            continue
        outcome.append({"item_id": f"sub{it['id']:03d}", "substrate_id": it["id"], "outcome_role": role[it["kind"]],
                        "kind": it["kind"], "source": it["source"], "category": it.get("category", ""),
                        "xstest_type": it.get("xstest_type", ""), "twin_group": it.get("twin_group", ""),
                        "jbb_index": it.get("jbb_index", ""), "prompt": it["prompt"], "sha256": sha(it["prompt"])})
    orb = json.loads((DATA / "orbench_hard1k.json").read_text())
    sub_norm = {norm(it["prompt"]) for it in sub}
    orb_ids = [i for i in range(len(orb)) if norm(orb[i]["prompt"]) not in sub_norm]
    orb_perm = [orb_ids[k] for k in rng.permutation(len(orb_ids))]
    for i in orb_perm[:36]:
        outcome.append({"item_id": f"orb{i:04d}", "substrate_id": None, "orbench_index": i, "outcome_role": "benign_alarming",
                        "kind": "orbench_hard", "source": "OR-Bench-hard-1k", "category": orb[i].get("category", ""),
                        "xstest_type": "", "twin_group": "", "jbb_index": "", "prompt": orb[i]["prompt"],
                        "sha256": sha(orb[i]["prompt"])})
    from collections import Counter
    rc = Counter(r["outcome_role"] for r in outcome)
    logger.info(f"outcome {len(outcome)} {dict(rc)}")
    assert len(outcome) == 180 and rc["harmful"] == 88 and rc["benign_alarming"] == 64 and rc["plain_benign"] == 28

    # ---- SEALED: fresh pairs never in the substrate
    used_norm = sub_norm | {norm(r["prompt"]) for r in outcome}
    sealed = []
    for p in xstest_pairs():
        if norm(p["safe"]) in used_norm or norm(p["contrast"]) in used_norm:
            continue
        pid = f"sx_{sha(p['safe'])[:10]}"
        sealed.append({"pair_id": pid, "side": "benign_twin", "source": "XSTest", "category": p["type"], "prompt": p["safe"]})
        sealed.append({"pair_id": pid, "side": "harmful", "source": "XSTest", "category": p["type"], "prompt": p["contrast"]})
    n_jbb = 0
    for idx in sorted(jbb_h, key=int):
        h, b = jbb_h[idx]["Goal"], jbb_b.get(idx, {}).get("Goal")
        if not b or norm(h) in used_norm or norm(b) in used_norm:
            continue
        sealed.append({"pair_id": f"sj_{idx}", "side": "harmful", "source": "JBB-Behaviors", "category": jbb_h[idx]["Category"], "prompt": h})
        sealed.append({"pair_id": f"sj_{idx}", "side": "benign_twin", "source": "JBB-benign", "category": jbb_h[idx]["Category"], "prompt": b})
        n_jbb += 1
        if n_jbb >= 68:
            break
    for i in orb_perm[36:236]:
        sealed.append({"pair_id": None, "side": "benign_alarming_reserve", "source": "OR-Bench-hard-1k",
                       "category": orb[i].get("category", ""), "prompt": orb[i]["prompt"]})
    n_pairs = len({r["pair_id"] for r in sealed if r["pair_id"]})
    assert n_pairs >= 120, n_pairs

    # ---- disjointness (normalised text)
    S = {norm(r["prompt"]) for r in screen}
    O = {norm(r["prompt"]) for r in outcome}
    Z = {norm(r["prompt"]) for r in sealed}
    checks = {"screen_outcome": len(S & O), "screen_sealed": len(S & Z), "outcome_sealed": len(O & Z),
              "sealed_in_substrate": len(Z & sub_norm)}
    assert all(v == 0 for v in checks.values()), checks

    jsonl(W / "screen16.jsonl", screen)
    jsonl(W / "outcome_items.jsonl", outcome)
    sp = W / "sealed" / "sealed_items.jsonl"
    jsonl(sp, sealed)
    sealed_sha = hashlib.sha256(sp.read_bytes()).hexdigest()
    code_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    per_src = Counter((r["source"], r["side"]) for r in sealed)
    (W / "sealed" / "sealed_items.sha256").write_text(sealed_sha + "\n")
    json.dump({"sealed_items_sha256": sealed_sha, "n_rows": len(sealed), "n_pairs": n_pairs,
               "rows_per_source_side": {f"{a}|{b}": c for (a, b), c in per_src.items()},
               "construction_code_sha256": code_sha, "disjointness": checks},
              open(W / "sealed" / "sealed_items_hashinfo.json", "w"), indent=1)

    # ---- twin-quality QC: bag-of-words LR
    def lopo_auc(rows):
        pids = sorted({r["pair_id"] for r in rows})
        y, s = [], []
        for p in pids:
            tr = [r for r in rows if r["pair_id"] != p]
            te = [r for r in rows if r["pair_id"] == p]
            vec = CountVectorizer(lowercase=True)
            X = vec.fit_transform([r["prompt"] for r in tr])
            clf = LogisticRegression(max_iter=2000).fit(X, [r["side"] == "harmful" for r in tr])
            s += list(clf.predict_proba(vec.transform([r["prompt"] for r in te]))[:, 1])
            y += [r["side"] == "harmful" for r in te]
        return float(roc_auc_score(y, s))
    two = [r for r in outcome if r["outcome_role"] in ("harmful", "benign_alarming")]
    groups = [r["twin_group"] if r["twin_group"].startswith("xs_") else (f"jbb{r['jbb_index']}" if r["jbb_index"] else r["item_id"]) for r in two]
    y = np.array([r["outcome_role"] == "harmful" for r in two])
    sc = np.zeros(len(two))
    for tr, te in GroupKFold(5).split(two, y, groups):
        vec = CountVectorizer(lowercase=True)
        X = vec.fit_transform([two[i]["prompt"] for i in tr])
        clf = LogisticRegression(max_iter=2000).fit(X, y[tr])
        sc[te] = clf.predict_proba(vec.transform([two[i]["prompt"] for i in te]))[:, 1]
    xs_only = [i for i, r in enumerate(two) if r["source"] == "XSTest"]
    tq = {"screen16_leave_one_pair_out_auroc": lopo_auc(screen),
          "outcome_harmful_vs_benign_alarming_groupkfold5_auroc": float(roc_auc_score(y, sc)),
          "outcome_xstest_only_auroc": float(roc_auc_score(y[xs_only], sc[xs_only])),
          "note": "Bag-of-words CountVectorizer+LogisticRegression; how much a SURFACE read already separates the sides. "
                  "SCREEN16 LOPO is over 8 pairs (16 prompts) and is very noisy."}
    json.dump(tq, open(W / "results" / "twin_quality.json", "w"), indent=1)
    logger.info(f"twin quality {tq}")
    logger.info(f"sealed sha {sealed_sha} rows {len(sealed)} pairs {n_pairs}")


if __name__ == "__main__":
    main()

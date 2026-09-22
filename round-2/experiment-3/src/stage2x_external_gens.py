#!/usr/bin/env python3
"""Convert stored model generations from three OTHER pipeline runs (D, E, F)
into a uniform per-checkpoint JSON format under WS/results/ext_gen/, so this
experiment's own judge can grade them.

Sources (all read-only):
  D = run_CbJDs3opF7E_/iter_4/gen_art_experiment_1  scored_iter4.jsonl (+panel_iter4.json)
  E = run_YqmEFECOIR3D/iter_1/gen_art_experiment_3   results/judged/*.jsonl (+ per_ckpt/sealed *.json)
  F = run_fEjgpc8BQoQS/iter_2/gen_art_experiment_2   generations/*/refusal_120.jsonl

Writes one JSON file per (source, checkpoint) plus a combined
results/ext_gen/_inventory.json summary, then re-reads and verifies every
written file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
OUT_DIR = WS / "results" / "ext_gen"
LOG_DIR = WS / "logs"

# ---------------------------------------------------------------------------
# source paths (read-only)
# ---------------------------------------------------------------------------
D_ROOT = Path("/ai-inventor/aii_data/runs/run_CbJDs3opF7E_/3_invention_loop/iter_4/gen_art/gen_art_experiment_1")
D_SCORED = D_ROOT / "scored_iter4.jsonl"
D_PANEL = D_ROOT / "results" / "panel_iter4.json"

E_ROOT = Path("/ai-inventor/aii_data/runs/run_YqmEFECOIR3D/3_invention_loop/iter_1/gen_art/gen_art_experiment_3")
E_JUDGED_DIR = E_ROOT / "results" / "judged"
E_PERCKPT_DIR = E_ROOT / "results" / "per_ckpt"
E_SEALED_DIR = E_ROOT / "results" / "sealed"

F_ROOT = Path("/ai-inventor/aii_data/runs/run_fEjgpc8BQoQS/3_invention_loop/iter_2/gen_art/gen_art_experiment_2/generations")

MIN_HARM_ROWS = 30

# level/role -> arm_guess maps observed in each source's own metadata
D_LEVEL_TO_ARM = {
    "abliterated": "edited",
    "uncensored": "edited",
    "behavioral_uncensored": "edited",
    "safety": "safety_tuned",
    "base": "base",
    "instruct": "honest",
}
E_ROLE_TO_ARM = {
    "abliterated": "edited",
    "uncensored": "edited",
    "behavioral_uncensored": "edited",
    "safety": "safety_tuned",
    "base": "base",
    "instruct": "honest",
}
F_ARM_TOKEN_TO_ARM = {
    "abliterated": "edited",
    "uncensored": "edited",
    "behavioral_uncensored": "edited",
    "safety": "safety_tuned",
    "base": "base",
    "instruct": "honest",
}


def sanitize_repo(repo_id: str) -> str:
    return repo_id.replace("/", "__")


def atomic_write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    tmp.rename(path)


# ---------------------------------------------------------------------------
# Source D: run_CbJDs3opF7E_ iter_4 gen_art_experiment_1 (plain_harmful panel)
# ---------------------------------------------------------------------------
def process_source_d(inventory: list, skipped: list) -> None:
    logger.info(f"[D] loading panel {D_PANEL}")
    panel = json.loads(D_PANEL.read_text())
    panel_by_key = {e["key"]: e for e in panel}

    logger.info(f"[D] streaming {D_SCORED}")
    by_member: dict[str, list[dict]] = {}
    n_lines = 0
    with D_SCORED.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_lines += 1
            row = json.loads(line)
            by_member.setdefault(row["member"], []).append(row)
    logger.info(f"[D] read {n_lines} rows across {len(by_member)} members")

    for member, rows in sorted(by_member.items()):
        panel_entry = panel_by_key.get(member)
        if panel_entry is None:
            reason = f"member '{member}' not found in panel_iter4.json keys"
            logger.warning(f"[D] SKIP {member}: {reason}")
            skipped.append({"source": "extD", "member": member, "reason": reason})
            continue
        repo_id = panel_entry["repo_used"]
        level = panel_entry.get("level")
        arm_guess = D_LEVEL_TO_ARM.get(level, "honest")
        arm_evidence = f"panel_iter4.json level='{level}' for member key '{member}'"

        out_rows = []
        n_skipped_rows = 0
        for r in rows:
            resp = r.get("completion")
            if resp is None:
                n_skipped_rows += 1
                continue
            out_rows.append(
                {
                    "item_id": str(r["uid"]),
                    "set": "H",  # all plain_harmful items
                    "prompt": r.get("prompt"),
                    "response": resp,
                    "category": None,
                    "their_label": r.get("judge_label"),
                }
            )
        n_H = sum(1 for rr in out_rows if rr["set"] == "H")
        n_B = sum(1 for rr in out_rows if rr["set"] == "B")
        if n_H < MIN_HARM_ROWS:
            reason = f"only {n_H} harmful rows (< {MIN_HARM_ROWS})"
            logger.warning(f"[D] SKIP {member} ({repo_id}): {reason}")
            skipped.append({"source": "extD", "member": member, "repo_id": repo_id, "reason": reason})
            continue

        out_id = f"extD__{sanitize_repo(repo_id)}"
        obj = {
            "id": out_id,
            "repo_id": repo_id,
            "source": "extD",
            "source_desc": (
                "run_CbJDs3opF7E_ iter_4 gen_art_experiment_1; plain_harmful item set; "
                f"n={len(out_rows)} harmful items; greedy (do_sample=False), "
                "chat_template(enable_thinking=False)"
            ),
            "source_path": f"{D_SCORED}; {D_PANEL}",
            "arm_guess": arm_guess,
            "arm_evidence": arm_evidence,
            "generation_settings": {
                "greedy": True,
                "do_sample": False,
                "temperature": 0.0,
                "max_new_tokens": 64,
                "template": rows[0].get("template"),
                "enable_thinking": False,
            },
            "rows": out_rows,
        }
        out_path = OUT_DIR / f"{out_id}.json"
        atomic_write_json(out_path, obj)
        logger.info(f"[D] wrote {out_path.name}: n_H={n_H} n_B={n_B} skipped_rows={n_skipped_rows} arm={arm_guess}")
        inventory.append(
            {
                "id": out_id,
                "repo_id": repo_id,
                "source": "extD",
                "arm_guess": arm_guess,
                "n_H": n_H,
                "n_B": n_B,
                "n_skipped_rows": n_skipped_rows,
            }
        )


# ---------------------------------------------------------------------------
# Source E: run_YqmEFECOIR3D iter_1 gen_art_experiment_3 (StrongREJECT harm + or-bench benign)
# ---------------------------------------------------------------------------
def load_e_role_meta() -> dict[str, dict]:
    """slug -> {repo, role, family, meta_path}, merged from per_ckpt/ and sealed/."""
    meta: dict[str, dict] = {}
    for d in (E_PERCKPT_DIR, E_SEALED_DIR):
        if not d.is_dir():
            continue
        for fp in sorted(d.glob("*.json")):
            entry = json.loads(fp.read_text())
            slug = entry.get("slug", fp.stem)
            meta[slug] = {
                "repo": entry.get("repo"),
                "role": entry.get("role"),
                "family": entry.get("family"),
                "meta_path": str(fp),
            }
    return meta


def judge_primary_label(jp) -> str | None:
    if not isinstance(jp, dict):
        return None
    return (
        f"refused={jp.get('refused')},harmful_content={jp.get('harmful_content')},"
        f"on_topic_help={jp.get('on_topic_help')}"
    )


def process_source_e(inventory: list, skipped: list) -> None:
    logger.info(f"[E] loading role metadata from {E_PERCKPT_DIR} and {E_SEALED_DIR}")
    role_meta = load_e_role_meta()
    logger.info(f"[E] {len(role_meta)} checkpoints with role metadata")

    judged_files = sorted(E_JUDGED_DIR.glob("*.jsonl"))
    logger.info(f"[E] found {len(judged_files)} judged files")

    for fp in judged_files:
        slug = fp.stem
        meta = role_meta.get(slug)
        if meta is None or not meta.get("repo"):
            reason = f"slug '{slug}' not found in per_ckpt/sealed role metadata"
            logger.warning(f"[E] SKIP {slug}: {reason}")
            skipped.append({"source": "extE", "member": slug, "reason": reason})
            continue
        repo_id = meta["repo"]
        role = meta.get("role")
        arm_guess = E_ROLE_TO_ARM.get(role, "honest")
        arm_evidence = f"{Path(meta['meta_path']).name} role='{role}' for slug '{slug}'"

        out_rows = []
        n_skipped_rows = 0
        n_lines = 0
        with fp.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n_lines += 1
                r = json.loads(line)
                resp = r.get("response")
                if resp is None:
                    n_skipped_rows += 1
                    continue
                set_code = "H" if r.get("set") == "harm" else "B"
                out_rows.append(
                    {
                        "item_id": str(r["gt_id"]),
                        "set": set_code,
                        "prompt": r.get("prompt"),
                        "response": resp,
                        "category": r.get("category"),
                        "their_label": judge_primary_label(r.get("judge_primary")),
                    }
                )
        n_H = sum(1 for rr in out_rows if rr["set"] == "H")
        n_B = sum(1 for rr in out_rows if rr["set"] == "B")
        if n_H < MIN_HARM_ROWS:
            reason = f"only {n_H} harmful rows (< {MIN_HARM_ROWS}) out of {n_lines} lines"
            logger.warning(f"[E] SKIP {slug} ({repo_id}): {reason}")
            skipped.append({"source": "extE", "member": slug, "repo_id": repo_id, "reason": reason})
            continue

        out_id = f"extE__{sanitize_repo(repo_id)}"
        obj = {
            "id": out_id,
            "repo_id": repo_id,
            "source": "extE",
            "source_desc": (
                "run_YqmEFECOIR3D iter_1 gen_art_experiment_3; StrongREJECT harm(45) + "
                f"or-bench benign(45) item set; n={len(out_rows)} items; greedy (do_sample=False), "
                "max_new_tokens=140, chat_template(enable_thinking=False)"
            ),
            "source_path": f"{fp}; {meta['meta_path']}",
            "arm_guess": arm_guess,
            "arm_evidence": arm_evidence,
            "generation_settings": {
                "greedy": True,
                "do_sample": False,
                "max_new_tokens": 140,
                "enable_thinking": False,
                "template": "chat_template" if meta.get("role") != "base" else None,
            },
            "rows": out_rows,
        }
        out_path = OUT_DIR / f"{out_id}.json"
        atomic_write_json(out_path, obj)
        logger.info(f"[E] wrote {out_path.name}: n_H={n_H} n_B={n_B} skipped_rows={n_skipped_rows} arm={arm_guess}")
        inventory.append(
            {
                "id": out_id,
                "repo_id": repo_id,
                "source": "extE",
                "arm_guess": arm_guess,
                "n_H": n_H,
                "n_B": n_B,
                "n_skipped_rows": n_skipped_rows,
            }
        )


# ---------------------------------------------------------------------------
# Source F: run_fEjgpc8BQoQS iter_2 gen_art_experiment_2 (HarmBench-style refusal_120)
# ---------------------------------------------------------------------------
def parse_f_dirname(dirname: str) -> tuple[str, str] | None:
    """'<org>__<name>__<arm>' -> ('org/name', arm)."""
    parts = dirname.split("__")
    if len(parts) < 3:
        return None
    arm_token = parts[-1]
    org = parts[0]
    name = "__".join(parts[1:-1])
    repo_id = f"{org}/{name}"
    return repo_id, arm_token


def process_source_f(inventory: list, skipped: list) -> None:
    dirs = sorted(p for p in F_ROOT.iterdir() if p.is_dir())
    logger.info(f"[F] found {len(dirs)} checkpoint directories under {F_ROOT}")

    for d in dirs:
        fp = d / "refusal_120.jsonl"
        if not fp.exists():
            reason = f"refusal_120.jsonl missing under {d.name}"
            logger.warning(f"[F] SKIP {d.name}: {reason}")
            skipped.append({"source": "extF", "member": d.name, "reason": reason})
            continue
        parsed = parse_f_dirname(d.name)
        if parsed is None:
            reason = f"directory name '{d.name}' does not match '<org>__<name>__<arm>'"
            logger.warning(f"[F] SKIP {d.name}: {reason}")
            skipped.append({"source": "extF", "member": d.name, "reason": reason})
            continue
        repo_id, arm_token = parsed
        arm_guess = F_ARM_TOKEN_TO_ARM.get(arm_token, "honest")
        arm_evidence = f"directory name suffix '__{arm_token}' for '{d.name}'"

        out_rows = []
        n_skipped_rows = 0
        n_lines = 0
        with fp.open() as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                n_lines += 1
                r = json.loads(line)
                resp = r.get("answer")
                if resp is None:
                    n_skipped_rows += 1
                    continue
                out_rows.append(
                    {
                        "item_id": f"f_{idx:03d}",
                        "set": "H",  # all HarmBench-style harmful requests
                        "prompt": r.get("request"),
                        "response": resp,
                        "category": None,
                        "their_label": "REFUSAL" if r.get("rule_is_refusal") else "NON_REFUSAL",
                    }
                )
        n_H = sum(1 for rr in out_rows if rr["set"] == "H")
        n_B = sum(1 for rr in out_rows if rr["set"] == "B")
        if n_H < MIN_HARM_ROWS:
            reason = f"only {n_H} harmful rows (< {MIN_HARM_ROWS}) out of {n_lines} lines"
            logger.warning(f"[F] SKIP {d.name} ({repo_id}): {reason}")
            skipped.append({"source": "extF", "member": d.name, "repo_id": repo_id, "reason": reason})
            continue

        out_id = f"extF__{sanitize_repo(repo_id)}"
        obj = {
            "id": out_id,
            "repo_id": repo_id,
            "source": "extF",
            "source_desc": (
                "run_fEjgpc8BQoQS iter_2 gen_art_experiment_2; HarmBench-style refusal_120 item set; "
                f"n={len(out_rows)} harmful items; greedy, max_new_tokens=64 (ignoring jailbreak_attacked.jsonl)"
            ),
            "source_path": str(fp),
            "arm_guess": arm_guess,
            "arm_evidence": arm_evidence,
            "generation_settings": {
                "greedy": True,
                "do_sample": False,
                "max_new_tokens": 64,
                "template": "apply_chat_template (tokenizer's own template)" if arm_token != "base" else None,
                "enable_thinking": None,
                "thinking_only_flag_constant_true": True,
            },
            "rows": out_rows,
        }
        out_path = OUT_DIR / f"{out_id}.json"
        atomic_write_json(out_path, obj)
        logger.info(f"[F] wrote {out_path.name}: n_H={n_H} n_B={n_B} skipped_rows={n_skipped_rows} arm={arm_guess}")
        inventory.append(
            {
                "id": out_id,
                "repo_id": repo_id,
                "source": "extF",
                "arm_guess": arm_guess,
                "n_H": n_H,
                "n_B": n_B,
                "n_skipped_rows": n_skipped_rows,
            }
        )


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------
def verify(inventory: list) -> bool:
    logger.info("=== VERIFY ===")
    ok = True
    for entry in inventory:
        path = OUT_DIR / f"{entry['id']}.json"
        try:
            obj = json.loads(path.read_text())
        except Exception as e:
            logger.error(f"VERIFY FAIL {path.name}: cannot parse JSON: {e}")
            ok = False
            continue
        rows = obj.get("rows", [])
        n_H = sum(1 for r in rows if r.get("set") == "H")
        if n_H < MIN_HARM_ROWS:
            logger.error(f"VERIFY FAIL {path.name}: n_H={n_H} < {MIN_HARM_ROWS}")
            ok = False
        n_nonempty = sum(
            1
            for r in rows
            if isinstance(r.get("prompt"), str)
            and r["prompt"].strip()
            and isinstance(r.get("response"), str)
            and r["response"].strip()
        )
        frac = n_nonempty / len(rows) if rows else 0.0
        if frac < 0.95:
            logger.error(f"VERIFY FAIL {path.name}: only {frac:.1%} rows have non-empty prompt/response")
            ok = False
    logger.info(f"VERIFY {'PASSED' if ok else 'FAILED'} for {len(inventory)} files")
    return ok


def print_table(inventory: list) -> None:
    header = f"{'source':<6} {'repo_id':<62} {'arm_guess':<13} {'n_H':>5} {'n_B':>5}"
    print(header)
    print("-" * len(header))
    for e in sorted(inventory, key=lambda x: (x["source"], x["repo_id"])):
        print(f"{e['source']:<6} {e['repo_id']:<62} {e['arm_guess']:<13} {e['n_H']:>5} {e['n_B']:>5}")


@logger.catch(reraise=True)
def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOG_DIR / "stage2x_external_gens.log", rotation="30 MB", level="DEBUG")

    for p in (D_SCORED, D_PANEL, E_JUDGED_DIR, F_ROOT):
        if not p.exists():
            raise FileNotFoundError(f"required source path missing: {p}")

    inventory: list[dict] = []
    skipped: list[dict] = []

    process_source_d(inventory, skipped)
    process_source_e(inventory, skipped)
    process_source_f(inventory, skipped)

    inv_path = OUT_DIR / "_inventory.json"
    atomic_write_json(inv_path, {"files": inventory, "skipped": skipped})
    logger.info(f"wrote inventory {inv_path} ({len(inventory)} files, {len(skipped)} skipped)")

    ok = verify(inventory)

    print()
    print_table(inventory)
    print()
    by_source: dict[str, int] = {}
    by_arm: dict[str, int] = {}
    for e in inventory:
        by_source[e["source"]] = by_source.get(e["source"], 0) + 1
        by_arm[e["arm_guess"]] = by_arm.get(e["arm_guess"], 0) + 1
    print(f"per-source counts: {by_source}")
    print(f"per-arm counts: {by_arm}")
    print(f"skipped/unmappable ({len(skipped)}):")
    for s in skipped:
        print(f"  {s}")
    print(f"verify_ok={ok}")

    if not ok:
        raise RuntimeError("verification failed; see log above")


if __name__ == "__main__":
    main()

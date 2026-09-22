#!/usr/bin/env python3
"""STEP 7 -- BLINDNESS FREEZE.

Run this the moment the 12 Set A rows exist and BEFORE any analysis. It writes
  values_setA.json        every Set A candidate x variant value in the long join schema,
  values_setA.sha256      sha256 of the canonical JSON of that file,
  freeze_certificate.json UTC time, the hash, a NAMES/SIZES/MTIMES-ONLY listing of every
                          iter_5/gen_art/*dataset* workspace (no file there is ever opened), and whether any
                          file there already has a name matching (?i)(label|outcome|graded|S2) at freeze time,
  and (if and only if a Set B declaration exists) reports the Set B repo list for a separate measurement pass.

The blindness guard (blind_guard.install()) is active for the whole process: any open of a file under
RUN/iter_5/gen_art/*dataset* whose name does not match (?i)set_?b.*\\.json raises BlindnessViolation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import blind_guard

blind_guard.install()

from loguru import logger  # noqa: E402

WS = Path(__file__).resolve().parent
RUN = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop")
GEN_ART = RUN / "iter_5" / "gen_art"
ROWS = WS / "rows"
LABEL_NAME_RE = re.compile(r"(?i)(label|outcome|graded|S2)")
SETB_DECL_RE = re.compile(r"(?i)set_?b.*(open|declar).*\.json$")

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "freeze.log", rotation="10 MB", level="DEBUG")


def canonical_json(o: object) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def slug(repo: str) -> str:
    return repo.replace("/", "__")


def dataset_workspaces() -> list[Path]:
    """Sibling Set A grading workspaces. os.scandir/stat only -- never an open."""
    if not GEN_ART.is_dir():
        return []
    return sorted(p for p in GEN_ART.iterdir() if p.is_dir() and "dataset" in p.name)


def listing(d: Path) -> list[dict]:
    out = []
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in (".git", "__pycache__")]
        for f in sorted(files):
            p = Path(root) / f
            try:
                st = p.stat()
            except OSError:
                continue
            out.append({"path": str(p.relative_to(d)), "size": st.st_size,
                        "mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime))})
            if len(out) > 20000:
                return out
    return out


def main() -> None:
    prereg = json.loads((WS / "PREREG.json").read_text())
    prereg_hash = hashlib.sha256((WS / "PREREG.json").read_bytes()).hexdigest()
    assert (WS / "PREREG_hash.txt").read_text().split()[0] == prereg_hash, "PREREG hash changed since the freeze"
    setA = list(prereg["panel"]["setA"])
    assert hashlib.sha256(json.dumps(setA).encode()).hexdigest() == prereg["panel"]["setA_list_sha256"]

    # ---- every Set A row must exist, be ungraded and carry no label
    missing, rows = [], {}
    for repo in setA:
        p = ROWS / f"{slug(repo)}.json"
        if not p.exists():
            missing.append(repo)
            continue
        r = json.loads(p.read_text())
        assert r.get("graded") is False, f"{repo}: row says graded={r.get('graded')} -- Set A must be ungraded"
        assert r.get("BALANCED") is None and r.get("PRODUCT") is None, f"{repo}: a label is present in the row"
        assert r.get("prereg_hash") == prereg_hash, f"{repo}: row was written under a different pre-registration"
        rows[repo] = r
    if missing:
        logger.warning(f"Set A rows missing ({len(missing)}): {missing}")

    # ---- long-schema values, built by the shared flattener so the schema is identical to the join file
    sys.path.insert(0, str(WS))
    from make_candidate_values import flatten_row  # noqa: E402  (owned by the analysis module)
    records: list[dict] = []
    for repo in setA:
        if repo in rows:
            records.extend(flatten_row(rows[repo]))
    records.sort(key=lambda r: (r["repo"], r["candidate"], r["variant"]))
    payload = {
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prereg_hash": prereg_hash,
        "setA_list": setA,
        "setA_list_sha256": prereg["panel"]["setA_list_sha256"],
        "n_repos_frozen": len(rows), "n_repos_missing": len(missing), "missing": missing,
        "code_hash": {repo: rows[repo].get("code_hash") for repo in rows},
        "resolved_sha": {repo: rows[repo].get("resolved_sha") for repo in rows},
        "seconds": {repo: {"shared": rows[repo].get("seconds_shared"),
                           "total_after_load_s": (rows[repo].get("timing") or {}).get("total_after_load_s")}
                    for repo in rows},
        "n_records": len(records),
        "records": records,
    }
    (WS / "values_setA.json").write_text(json.dumps(payload, indent=1))
    h = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    (WS / "values_setA.sha256").write_text(f"{h}  canonical_json(values_setA.json)\n")

    # ---- certificate: listing only, contents never opened
    ds = dataset_workspaces()
    cert_ds = []
    for d in ds:
        ls = listing(d)
        cert_ds.append({"workspace": str(d), "n_files": len(ls),
                        "files_matching_label_pattern": [x["path"] for x in ls if LABEL_NAME_RE.search(x["path"])],
                        "listing": ls})
    setb_decl = []
    for d in ds:
        for f in d.glob("*.json"):
            if SETB_DECL_RE.search(f.name):
                setb_decl.append(str(f))
    cert = {
        "frozen_utc": payload["frozen_utc"],
        "values_setA_sha256": h,
        "prereg_hash": prereg_hash,
        "n_repos_frozen": len(rows), "missing": missing,
        "dataset_workspaces_present": [str(d) for d in ds],
        "dataset_workspaces": cert_ds,
        "any_label_named_file_at_freeze": any(c["files_matching_label_pattern"] for c in cert_ds),
        "statement": ("At freeze time this process had never opened any file under iter_5/gen_art/*dataset*; the "
                      "blindness guard (blind_guard.install(), sys.addaudithook + wrapped open/Path.read_text) was "
                      "active for the whole process and the listing above was produced with os.walk/stat only."),
        "guard": {"installed": blind_guard.installed(), **blind_guard.N_CHECKED},
        "set_b_declaration_files": setb_decl,
    }
    (WS / "freeze_certificate.json").write_text(json.dumps(cert, indent=1))
    logger.info(f"FROZEN {len(rows)}/{len(setA)} Set A repos, {len(records)} records, sha256 {h}")
    logger.info(f"dataset workspaces seen: {[str(d) for d in ds] or 'NONE'}; set B declarations: {setb_decl or 'NONE'}")

    # ---- Set B: only if explicitly declared open
    setb_open, setb_repos = False, []
    for f in setb_decl:
        try:
            j = json.loads(Path(f).read_text())  # allowed by the guard (name matches set_b*.json)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"{f}: unreadable ({e})")
            continue
        if j.get("set_b_open") is True:
            setb_open = True
            setb_repos = list(j.get("repos") or j.get("repo_list") or [])
    Path(WS / "setb_status.json").write_text(json.dumps(
        {"set_b_open": setb_open, "repos": setb_repos, "declaration_files": setb_decl,
         "deviation": None if setb_open else "SET_B_SEALED_NOT_DECLARED"}, indent=1))
    print(h, len(records), "setB_open=", setb_open)


if __name__ == "__main__":
    main()

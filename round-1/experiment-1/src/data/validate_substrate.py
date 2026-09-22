#!/usr/bin/env python3
"""Validate the frozen item substrate for the safety-metrics experiment.

Checks (and reports, does not assume):
- xstest: header, row count, positional twin pairing, (type,focus) pairing drop count
- jbb: harmful/benign row counts, Index 1:1 pairing
- strongreject: row count, columns
- orbench: row count, distinct categories
- sha256 of every downloaded file
"""
import csv
import hashlib
import json
from collections import OrderedDict, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
FILES = [
    "xstest_prompts.csv",
    "jbb_harmful.csv",
    "jbb_benign.csv",
    "strongreject.csv",
    "orbench_hard1k.json",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv_rows(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    header = rows[0]
    body = rows[1:]
    return header, body


def validate_xstest(report: dict):
    path = DATA_DIR / "xstest_prompts.csv"
    header, body = read_csv_rows(path)
    report["xstest"] = {}
    report["xstest"]["header"] = header
    report["xstest"]["row_count"] = len(body)
    report["xstest"]["expected_header"] = ["id", "prompt", "type", "label", "focus", "note"]
    report["xstest"]["expected_row_count"] = 450

    idx = {name: i for i, name in enumerate(header)}
    type_idx = idx["type"]
    focus_idx = idx["focus"]
    label_idx = idx.get("label")

    # Build contiguous blocks by `type`, in file order.
    blocks = []  # list of (type_name, [rows])
    cur_type = None
    cur_rows = []
    for row in body:
        t = row[type_idx]
        if t != cur_type:
            if cur_type is not None:
                blocks.append((cur_type, cur_rows))
            cur_type = t
            cur_rows = []
        cur_rows.append(row)
    if cur_type is not None:
        blocks.append((cur_type, cur_rows))

    block_info = [{"type": t, "n_rows": len(rows_)} for t, rows_ in blocks]
    report["xstest"]["type_blocks_in_order"] = block_info
    report["xstest"]["n_blocks"] = len(blocks)

    # Determine safe / contrast type names via `label` column when present,
    # else via the "contrast_" prefix convention used by XSTest.
    safe_types = []
    contrast_types = []
    for t, rows_ in blocks:
        if label_idx is not None:
            labels_in_block = set(r[label_idx] for r in rows_)
            is_contrast = labels_in_block == {"unsafe"} or t.startswith("contrast_")
        else:
            is_contrast = t.startswith("contrast_")
        if is_contrast:
            contrast_types.append(t)
        else:
            safe_types.append(t)

    report["xstest"]["safe_types"] = safe_types
    report["xstest"]["contrast_types"] = contrast_types

    # Map safe type name -> its contrast counterpart, by the naming convention
    # "contrast_<suffix>" pairing with the safe type whose name ends in
    # "<suffix>" OR by adjacency in file order (each safe block immediately
    # followed by its contrast block), which is the authoritative rule per
    # the task instructions.
    type_order = [t for t, _ in blocks]
    pos_pairs_total = 0
    positional_pairs_detail = []
    shared_contrast_unpaired_safe_types = []

    # Walk blocks in order; a safe block immediately followed by a contrast
    # block forms a pairing UNLESS that contrast type is shared by two safe
    # types (contrast_discr, contrast_privacy per task note), in which case
    # only the pairing that is immediately adjacent counts, and the OTHER
    # safe type sharing that contrast label is reported unpaired.
    contrast_type_to_safe_types = defaultdict(list)
    # First pass: figure out, by name pattern, which safe types map to which
    # contrast type conceptually (suffix match), to detect the shared cases.
    for st in safe_types:
        # e.g. "contrast_homonyms" pairs with "homonyms"
        candidate = f"contrast_{st.split('_', 1)[-1]}" if "_" in st else f"contrast_{st}"
        # Fallback: also just try contrast_<full safe type name>
        candidates = {f"contrast_{st}"}
        if "_" in st:
            candidates.add(f"contrast_{st.split('_', 1)[-1]}")
        matched = [ct for ct in contrast_types if ct in candidates]
        for ct in matched:
            contrast_type_to_safe_types[ct].append(st)

    shared_contrast_types = {ct: sts for ct, sts in contrast_type_to_safe_types.items() if len(sts) > 1}
    report["xstest"]["contrast_types_shared_by_multiple_safe_types"] = shared_contrast_types

    # Now do the ADJACENCY-based positional pairing: walk the block sequence;
    # whenever block i is a safe type and block i+1 is a contrast type,
    # pair them positionally (row k <-> row k).
    unpaired_safe_types = []
    used_contrast_indices = set()
    i = 0
    while i < len(blocks) - 1:
        t_cur, rows_cur = blocks[i]
        t_next, rows_next = blocks[i + 1]
        if t_cur in safe_types and t_next in contrast_types:
            n_pairs = min(len(rows_cur), len(rows_next))
            pos_pairs_total += n_pairs
            positional_pairs_detail.append(
                {"safe_type": t_cur, "contrast_type": t_next, "n_pairs": n_pairs}
            )
            used_contrast_indices.add(i + 1)
            i += 2
        else:
            i += 1

    paired_safe_types = {d["safe_type"] for d in positional_pairs_detail}
    for st in safe_types:
        if st not in paired_safe_types:
            unpaired_safe_types.append(st)

    report["xstest"]["positional_pairs_detail"] = positional_pairs_detail
    report["xstest"]["positional_complete_pairs"] = pos_pairs_total
    report["xstest"]["expected_positional_complete_pairs"] = 300
    report["xstest"]["unpaired_safe_types_by_adjacency"] = unpaired_safe_types

    # Known-by-construction unpaired types per task note (contrast_discr /
    # contrast_privacy each shared by two safe types -> nons_group_real_discr
    # and privacy_public end up unpaired).
    report["xstest"]["known_unpaired_safe_types_per_task_note"] = [
        "nons_group_real_discr",
        "privacy_public",
    ]

    # --- (type, focus) keyed pairing, to show how many rows get DROPPED ---
    # Build safe_type -> contrast_type map using the adjacency pairing found
    # above (this is the "matching contrast block" for each safe type).
    safe_to_contrast = {d["safe_type"]: d["contrast_type"] for d in positional_pairs_detail}

    total_rows_considered = 0
    total_rows_matched_by_focus = 0
    for st, ct in safe_to_contrast.items():
        safe_rows = [r for r in body if r[type_idx] == st]
        contrast_rows = [r for r in body if r[type_idx] == ct]
        total_rows_considered += len(safe_rows) + len(contrast_rows)

        safe_focus_count = defaultdict(int)
        for r in safe_rows:
            safe_focus_count[r[focus_idx]] += 1
        contrast_focus_count = defaultdict(int)
        for r in contrast_rows:
            contrast_focus_count[r[focus_idx]] += 1

        # A focus value can only be UNAMBIGUOUSLY used as a join key if it
        # appears exactly once on each side; otherwise those rows can't be
        # deterministically paired by (type, focus) and get dropped.
        for r in safe_rows:
            f = r[focus_idx]
            if safe_focus_count[f] == 1 and contrast_focus_count.get(f, 0) == 1:
                total_rows_matched_by_focus += 1
        for r in contrast_rows:
            f = r[focus_idx]
            if contrast_focus_count[f] == 1 and safe_focus_count.get(f, 0) == 1:
                total_rows_matched_by_focus += 1

    rows_dropped_by_focus_keying = total_rows_considered - total_rows_matched_by_focus
    report["xstest"]["focus_keyed_rows_considered"] = total_rows_considered
    report["xstest"]["focus_keyed_rows_matched"] = total_rows_matched_by_focus
    report["xstest"]["focus_keyed_rows_dropped"] = rows_dropped_by_focus_keying
    report["xstest"]["expected_focus_keyed_rows_dropped_approx"] = 108


def validate_jbb(report: dict):
    hpath = DATA_DIR / "jbb_harmful.csv"
    bpath = DATA_DIR / "jbb_benign.csv"
    hheader, hbody = read_csv_rows(hpath)
    bheader, bbody = read_csv_rows(bpath)

    report["jbb"] = {
        "harmful_header": hheader,
        "harmful_row_count": len(hbody),
        "benign_header": bheader,
        "benign_row_count": len(bbody),
        "expected_row_count_each": 100,
    }

    has_index_h = "Index" in hheader
    has_index_b = "Index" in bheader
    report["jbb"]["harmful_has_index_col"] = has_index_h
    report["jbb"]["benign_has_index_col"] = has_index_b

    if has_index_h and has_index_b:
        hi = hheader.index("Index")
        bi = bheader.index("Index")
        h_indices = [r[hi] for r in hbody]
        b_indices = [r[bi] for r in bbody]
        pairs_1to1 = (
            len(h_indices) == len(b_indices)
            and h_indices == b_indices
            and len(set(h_indices)) == len(h_indices)
        )
        report["jbb"]["index_pairs_1to1"] = pairs_1to1
        report["jbb"]["index_sets_equal"] = set(h_indices) == set(b_indices)
    else:
        report["jbb"]["index_pairs_1to1"] = False


def validate_strongreject(report: dict):
    path = DATA_DIR / "strongreject.csv"
    header, body = read_csv_rows(path)
    report["strongreject"] = {
        "columns": header,
        "row_count": len(body),
    }


def validate_orbench(report: dict):
    path = DATA_DIR / "orbench_hard1k.json"
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    categories = sorted(set(r["category"] for r in rows))
    report["orbench"] = {
        "row_count": len(rows),
        "distinct_categories": categories,
        "n_distinct_categories": len(categories),
        "expected_categories": sorted(
            [
                "deception",
                "harassment",
                "harmful",
                "hate",
                "illegal",
                "privacy",
                "self-harm",
                "sexual",
                "unethical",
                "violence",
            ]
        ),
    }


def compute_hashes(report: dict):
    hashes = OrderedDict()
    for fname in FILES:
        p = DATA_DIR / fname
        hashes[fname] = {
            "sha256": sha256_of(p),
            "size_bytes": p.stat().st_size,
        }
    report["sha256"] = hashes


def main():
    report = OrderedDict()
    validate_xstest(report)
    validate_jbb(report)
    validate_strongreject(report)
    validate_orbench(report)
    compute_hashes(report)

    out_path = DATA_DIR / "substrate_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {out_path}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

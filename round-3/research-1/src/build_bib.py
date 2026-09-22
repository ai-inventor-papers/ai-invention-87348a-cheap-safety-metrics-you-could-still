"""Regenerate references.bib by identifier.

Authors/titles/versions come from the arXiv Atom API (authoritative for names);
venue, non-arXiv DOI and year come from the Semantic Scholar batch bib fetched with
aii_semscholar_bib (raw/ss_*.bib). Nothing is written from memory: every entry is
keyed to an identifier that resolved, and the resolved title is stored so the
caller can check it against the expected title.

Usage: python3 build_bib.py ids.json  -> references.bib, bib_entries.json
ids.json: list of {"arxiv": "...", "key": optional forced key, "expect": optional title fragment}
"""
import json
import re
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

WS = Path(__file__).parent
ATOM = "{http://www.w3.org/2005/Atom}"
ARX = "{http://arxiv.org/schemas/atom}"

# Surnames with particles / multi-word surnames that must be kept whole.
SURNAME_OVERRIDES = {
    "Harethah Abu Shairah": ("Abu Shairah", "Harethah"),
    "Joshua Fonseca Rivera": ("Rivera", "Joshua Fonseca"),
    "Marvin von Hagen": ("von Hagen", "Marvin"),
    "Isaac Llorente-Saguer": ("Llorente-Saguer", "Isaac"),
}


def fetch_arxiv(ids):
    out = {}
    for i in range(0, len(ids), 40):
        chunk = ids[i:i + 40]
        url = ("https://export.arxiv.org/api/query?id_list=" + ",".join(chunk)
               + f"&max_results={len(chunk)}")
        xml = subprocess.run(["curl", "-s", "-L", "--max-time", "90", url],
                             capture_output=True, text=True).stdout
        (WS / "raw" / f"arxiv_atom_{i // 40}.xml").write_text(xml)
        root = ET.fromstring(xml)
        for e in root.findall(ATOM + "entry"):
            idurl = e.find(ATOM + "id").text.strip()
            m = re.search(r"abs/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})(v[0-9]+)?$", idurl)
            if not m:
                continue
            aid, ver = m.group(1), m.group(2) or ""
            title = " ".join(e.find(ATOM + "title").text.split())
            authors = [" ".join(a.find(ATOM + "name").text.split()) for a in e.findall(ATOM + "author")]
            doi_el = e.find(ARX + "doi")
            jr_el = e.find(ARX + "journal_ref")
            cm_el = e.find(ARX + "comment")
            out[aid] = {"title": title, "authors": authors, "version": ver,
                        "published": e.find(ATOM + "published").text[:10],
                        "doi": doi_el.text.strip() if doi_el is not None else None,
                        "journal_ref": " ".join(jr_el.text.split()) if jr_el is not None else None,
                        "comment": " ".join(cm_el.text.split()) if cm_el is not None else None}
        time.sleep(3)
    return out


def parse_ss_bib():
    """Map arXiv id -> (venue, doi, year, entrytype) from Semantic Scholar bib files."""
    info = {}
    for f in sorted((WS / "raw").glob("ss_*.bib")):
        for block in re.split(r"\n(?=@)", f.read_text()):
            m = re.search(r"abs/([0-9]{4}\.[0-9]{4,5})", block) or re.search(r"arXiv\.([0-9]{4}\.[0-9]{4,5})", block)
            if not m:
                continue
            g = lambda k: (re.search(rf"\n\s*{k}\s*=\s*\{{(.*?)\}},?\s*\n", block) or [None, None])[1]
            typ = re.match(r"@(\w+)", block.strip())
            info[m.group(1)] = {"booktitle": g("booktitle"), "journal": g("journal"),
                                "doi": g("doi"), "year": g("year"),
                                "type": typ.group(1).lower() if typ else "article",
                                "pages": g("pages"), "volume": g("volume")}
    return info


def split_name(full):
    if full in SURNAME_OVERRIDES:
        return SURNAME_OVERRIDES[full]
    parts = full.split()
    return parts[-1], " ".join(parts[:-1])


def ascii_key(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s)


def tex_escape(s):
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    ids = [s["arxiv"] for s in spec if s.get("arxiv")]
    arx = fetch_arxiv(ids)
    ss = parse_ss_bib()
    entries, used, report = [], {}, []
    for s in spec:
        if s.get("manual"):
            entries.append(s["manual"])
            report.append({"key": s["key"], "id": s.get("id"), "title": s.get("title"), "source": s.get("source")})
            continue
        aid = s["arxiv"]
        a = arx.get(aid)
        if a is None:
            report.append({"id": aid, "status": "UNRESOLVED_ON_ARXIV"})
            continue
        v = ss.get(aid, {})
        sur, _ = split_name(a["authors"][0])
        year = s.get("year") or a["published"][:4]
        key = s.get("key") or f"{ascii_key(sur)}{year}"
        if key in used and not s.get("key"):
            key = key + "b"
        used[key] = aid
        authors = " and ".join("{%s}, %s" % split_name(n) if n in SURNAME_OVERRIDES else n for n in a["authors"])
        venue = s.get("venue") or v.get("booktitle")
        if venue in (None, "arXiv.org") or (venue and "&amp;" in venue):
            venue = None
        # Venue year: only from an explicit override or the arXiv author comment
        # (e.g. "ICLR 2025 (Oral)"); otherwise keep the arXiv v1 year and say so.
        vnote = None
        if venue and not s.get("year"):
            cm = re.search(r"(ICLR|NeurIPS|ICML|ACL|NAACL|EMNLP|FAccT|EACL|TrustNLP)[^0-9]{0,40}(20[0-9]{2})", a["comment"] or "")
            if cm:
                year = cm.group(2)
            else:
                vnote = "Venue from Semantic Scholar; year is the arXiv v1 year (venue year not verified)"
        doi = s.get("doi") or a["doi"] or (v.get("doi") if v.get("doi") and "arXiv" not in v.get("doi", "") else None) \
            or f"10.48550/arXiv.{aid}"
        is_journal = s.get("journal_venue", False)
        if venue and not is_journal:
            typ, vf = "inproceedings", f" booktitle = {{{tex_escape(venue)}}},\n"
        elif venue and is_journal:
            typ, vf = "article", f" journal = {{{tex_escape(venue)}}},\n"
        else:
            typ, vf = "article", f" journal = {{arXiv preprint arXiv:{aid}}},\n"
        if vnote and not s.get("note"):
            s = {**s, "note": vnote}
        extra = "".join(f" {k} = {{{s[k]}}},\n" for k in ("volume", "pages", "note") if s.get(k))
        entry = (f"@{typ}{{{key},\n title = {{{{{tex_escape(a['title'])}}}}},\n author = {{{authors}}},\n"
                 f"{vf} year = {{{year}}},\n{extra} eprint = {{{aid}}},\n archivePrefix = {{arXiv}},\n"
                 f" doi = {{{doi}}},\n url = {{https://arxiv.org/abs/{aid}}}\n}}")
        entries.append(entry)
        ok = (s.get("expect", "").lower() in a["title"].lower()) if s.get("expect") else None
        report.append({"key": key, "arxiv": aid, "version_at_fetch": a["version"], "title": a["title"],
                       "first_author": a["authors"][0], "n_authors": len(a["authors"]), "venue": venue,
                       "doi": doi, "expect_ok": ok, "bib_year": year, "ss_year": v.get("year"),
                       "arxiv_journal_ref": a["journal_ref"], "arxiv_comment": a["comment"]})
    keys = [re.match(r"@\w+\{([^,]+),", e).group(1) for e in entries]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    (WS / "references.bib").write_text("\n\n".join(entries) + "\n")
    (WS / "bib_entries.json").write_text(json.dumps({"n": len(entries), "duplicate_keys": dup,
                                                      "entries": report}, indent=1, ensure_ascii=False))
    print(len(entries), "entries; dup keys:", dup)
    for r in report:
        if r.get("expect_ok") is False or r.get("status"):
            print("CHECK", r)


if __name__ == "__main__":
    main()

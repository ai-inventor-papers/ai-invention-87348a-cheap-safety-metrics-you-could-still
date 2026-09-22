#!/usr/bin/env python3
"""Assemble research_out.json: {title, summary, answer, sources, follow_up_questions}.
The answer embeds the compact spec table as a fenced ```json block, as the plan requires."""
import json, pathlib
D = pathlib.Path(__file__).parent
answer_prose = (D / "answer_prose.md").read_text().rstrip()
compact = (D / "spec_table_compact.json").read_text().rstrip()
sources = json.loads((D / "raw" / "sources.json").read_text())
meta = json.loads((D / "meta.json").read_text())

answer = (answer_prose
          + "\n\n---\n\n## THE MACHINE-READABLE SPEC TABLE\n\n"
            "Downstream artifacts parse the block below. It is the compact, "
            "decision-complete view; the COMPLETE record — every verbatim quote, "
            "every grep run, every query, full model rosters — is `spec_table.json` "
            "in this artifact's workspace, and the prose twin is `research_report.md`.\n\n"
          + "```json\n" + compact + "\n```\n")

# GUARD: every bracketed-numeric token in the answer is read as a citation marker by the
# validator, including ones that are really math (e.g. an interval "[0,1]"). Any index that
# does not resolve to a listed source is a hard error, not a warning.
import re
_valid = {s["index"] for s in sources}
_bad = {}
for _m in re.finditer(r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]", answer):
    for _n in (int(x) for x in re.findall(r"\d+", _m.group(0))):
        if _n not in _valid:
            _bad.setdefault(_m.group(0), answer[max(0, _m.start() - 70):_m.end() + 40].replace("\n", " "))
if _bad:
    raise SystemExit("UNRESOLVABLE CITATION TOKENS IN ANSWER:\n" +
                     "\n".join(f"  {k!r} -> ...{v}..." for k, v in _bad.items()))
_cited = {int(x) for _m in re.finditer(r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]", answer)
          for x in re.findall(r"\d+", _m.group(0))}
_uncited = sorted(_valid - _cited)
if _uncited:
    raise SystemExit(f"SOURCES LISTED BUT NEVER CITED: {_uncited}")

out = {
    "title": meta["title"],
    "summary": meta["summary"],
    "answer": answer,
    "sources": sources,
    "follow_up_questions": meta["follow_up_questions"],
}
p = D / "research_out.json"
p.write_text(json.dumps(out, indent=2))
print(f"wrote {p} ({p.stat().st_size} bytes); answer {len(answer)} chars; {len(sources)} sources")

#!/usr/bin/env python3
"""Emit ./.terminal_claude_agent_struct_out.json, keeping title/summary/answer/
sources/follow_up_questions byte-identical to research_out.json as required."""
import json, pathlib
D = pathlib.Path(__file__).parent
ro = json.loads((D / "research_out.json").read_text())
meta = json.loads((D / "meta.json").read_text())
struct = {
    "title": ro["title"],
    "layman_summary": meta["layman_summary"],
    "summary": ro["summary"],
    "out_expected_files": {"output": "research_out.json"},
    "upload_ignore_regexes": [],
    "answer": ro["answer"],
    "sources": ro["sources"],
    "follow_up_questions": ro["follow_up_questions"],
}
p = D / ".terminal_claude_agent_struct_out.json"
p.write_text(json.dumps(struct, indent=2))

# validate against the schema's hard constraints
assert 12 <= len(struct["title"]) <= 90, len(struct["title"])
assert 80 <= len(struct["layman_summary"]) <= 250, len(struct["layman_summary"])
assert 500 <= len(struct["summary"]) <= 5000, len(struct["summary"])
assert struct["sources"] and all(
    s["index"] > 0 and s["url"] and s["title"] and s["summary"] for s in struct["sources"])
assert [s["index"] for s in struct["sources"]] == list(range(1, len(struct["sources"]) + 1))
assert 2 <= len(struct["follow_up_questions"]) <= 3
for k in ("title", "summary", "answer", "sources", "follow_up_questions"):
    assert struct[k] == ro[k], f"{k} differs between struct out and research_out.json"
print(f"wrote {p} ({p.stat().st_size} bytes) - all schema assertions passed")
print(f"  title={len(struct['title'])}  layman={len(struct['layman_summary'])}  "
      f"summary={len(struct['summary'])}  answer={len(struct['answer'])}  "
      f"sources={len(struct['sources'])}  followups={len(struct['follow_up_questions'])}")

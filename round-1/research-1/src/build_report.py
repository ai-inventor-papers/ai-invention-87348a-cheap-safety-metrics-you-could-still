#!/usr/bin/env python3
import pathlib
D = pathlib.Path(__file__).parent
ORDER = ["sec_exec.md", "sec_AMS.md", "sec_GFS.md", "sec_NGLARE.md", "sec_RAS.md",
         "sec_comparability.md", "sec_candidates.md", "sec_adversarial.md",
         "sec_numbers.md", "sec_handoff.md", "sec_sources.md", "sec_unresolved.md"]
chunks = []
for name in ORDER:
    p = D / "parts" / name
    if p.exists():
        chunks.append(p.read_text().rstrip())
    else:
        print(f"  (skipping absent part: {name})")
out = D / "research_report.md"
out.write_text("\n\n---\n\n".join(chunks) + "\n")
print(f"wrote {out} ({out.stat().st_size} bytes, {len(chunks)} sections)")

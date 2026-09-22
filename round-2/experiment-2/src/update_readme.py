#!/usr/bin/env python3
"""Fill README.md's key-results block from out/analysis_out.json (numbers never hand-typed)."""
import json
from pathlib import Path

W = Path(__file__).resolve().parent
a = json.loads((W / "out" / "analysis_out.json").read_text())
c = a["counts"]
lines = [f"**Counts.** {c['ladder_cells']} weight-ladder cells over {len(c['ladder_hosts'])} "
         f"checkpoints / {len(c['ladder_families'])} families "
         f"({', '.join(h.split('/')[-1] for h in c['ladder_hosts'])}); "
         f"{c['behavioural_cells_full']} graded behavioural cells (+{c['behavioural_cells_search']} "
         f"alpha-search cells) on {', '.join(h.split('/')[-1] for h in c['behavioural_hosts'])}; honest "
         f"weight panel {c['honest_weight_panel_rows']} rows (honest n={c['honest_weight_panel_honest_n']}, "
         f"{c['honest_weight_panel_families']} families); activation panel n={c['activation_panel_rows']} "
         f"(WITHIN-FAMILY ONLY); PARTIAL_LADDER={c['PARTIAL_LADDER']}; judge spend "
         f"${a['spend'].get('usd')}.", ""]
lines += [f"- {h}" for h in a.get("headline_findings", [])]
body = "\n".join(lines)
p = W / "README.md"
s = p.read_text()
i, j = s.index("<!-- KEY-RESULTS-START -->"), s.index("<!-- KEY-RESULTS-END -->")
s = s[: i + len("<!-- KEY-RESULTS-START -->")] + "\n" + body + "\n" + s[j:]
p.write_text(s)
print("README key results updated:", len(lines), "lines")

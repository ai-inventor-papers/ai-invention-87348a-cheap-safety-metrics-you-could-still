# Paper Site: Pre-Registered Screening of Internal Safety Metrics

Public web page for the paper "Pre-Registered Screening of Internal Safety Metrics for Language Model Checkpoints."

## Layout

- `index.html` — self-contained web page (inline CSS + JS, no external dependencies)
- `paper.tex` — LaTeX source of the paper
- `paper.pdf` — compiled paper
- `references.bib` — bibliography
- `figures/` — all figures used by both the paper and the web page
  - `fig_overview_v0.jpg` — pipeline overview diagram
  - `fig_c12_scatter_v0.png` — C12 twin d-prime vs balanced safety scatter (rendered from PDF)
  - `fig_screen_scatter_v0.png` — C2 self-ablation vs balanced safety scatter (rendered from PDF)
  - `fig_grader_v0.png` — grader-side refusal comparison (rendered from PDF)
  - `fig_c12_scatter_v0.pdf`, `fig_screen_scatter_v0.pdf`, `fig_grader_v0.pdf` — vector originals
  - `*_spec.json` — figure generation specs
- `workspace/` — scratch folder from LaTeX compilation (not part of the site)

## Running

Open `index.html` in any browser. No build step, no server, no network required.

## Restoring removed files

No files were removed. All assets are under 10 MB.

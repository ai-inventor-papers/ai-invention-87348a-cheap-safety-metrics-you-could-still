# Pre-Registered Screening of Internal Safety Metrics for Language Model Checkpoints

Publication-ready LaTeX paper evaluating 14 candidate cheap safety metrics against two-sided ground truth on 23 chat checkpoints from 8 architecture families.

## Layout

- `paper.tex` — LaTeX source (all sections: Abstract through Conclusion)
- `paper.pdf` — Compiled PDF (17 pages)
- `references.bib` — BibTeX bibliography (28 entries)
- `figures/` — Pre-generated figure images
  - `fig_overview_v0.jpg` — Pipeline overview (concept figure)
  - `fig_c12_scatter_v0.pdf` — C12 twin d-prime vs balanced safety
  - `fig_screen_scatter_v0.pdf` — C2 self-ablation vs balanced safety
  - `fig_grader_v0.pdf` — StrongREJECT vs stance-based grader comparison

## Building

```bash
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

Requires a TeX Live installation with `natbib`, `booktabs`, `graphicx`, `hyperref` and `xcolor`.

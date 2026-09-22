# Iteration-5 final evaluation — screen, freeze and blind check of cheap single-model safety reads

This is the **single numbers source** for the final paper of run `run_fcYd_7ruOwtm`. It reads only stored
artifacts from earlier iterations (no model weights, no GPU, no LLM call, **$0.00 spend**) and produces:

1. a provenance gate over every input (`provenance.json`),
2. the mechanical S1–S6 screen of every read on the 23-checkpoint graded panel (`screen_ranked.json`),
3. a hash-frozen survivor set written **before** any confirmation label could be opened
   (`frozen_survivors.json` + `.sha256`),
4. the one-shot confirmation (`confirmation.json`),
5. the reviewer must-fix list (a)–(i) with `file:key` provenance for every number (`corrections_v3.json`,
   `numbers_ledger_v3.json`, `settings_table.json`, `results/external.json`, `results/mde_table.json`),
6. the mechanism bonus from stored distributions only (`mechanism.json`) and six figures (`figures/`).

## Headline outcome (counts first)

- Panel: **23 graded checkpoints**, 8 families, 11 lineages, 2 blanket refusers, 11 honest instruct models.
  MDE_rho = 0.531 at ICC 0.103.
- **19 of 28 screen rows were computable**; 9 are `NOT RUN` because no iteration-5 CPU/GPU tier file existed
  when this ran (the planner's documented failure path: the screen falls back to the stored-row derivable
  subset C1, C2, C2n, C2ts, C17, C14 plus the bars).
- **3 survivors under the repaired rules: C2, C17, C2n** — and they are *not independent*: C2n is C2
  standardised by its own direction null, C17 is the mean reference-rank of C2 and the logit gap. Three
  shipped reads are one measurement.
- **Confirmation: UNTESTED.** No `confirm_labels.json` exists in any iteration-5 sibling, so no Set A
  checkpoint has a label. Verbatim: *"The requester's invariant of at least 3 shipped internal metrics is
  UNMET."*
- No internal read has a positive one-sided bound for its increment over the 16-prompt judged probe, so the
  required sentence is printed: *"Looking inside MATCHES and does not beat 16 judged completions; it saves
  generation and the judge (no generation, no judge, about 16 seconds per 4B model)."*
- `ams_tier1.json` is missing → **AMS_MISSING**, and the wording "strongest to date" is forbidden.
- All **seven** pre-declared sanity reproductions of the iteration-4 numbers match to < 0.0005
  (C2 rho 0.9004, logit-gap rho 0.7719, C2 partial 0.7456, bound 0.4400, C1 partial 0.4910, behaviour 0.9309,
  C2 | behaviour 0.3148).

- **Independent re-derivation:** `results/independent_check.json` re-computes the eight headline quantities from
  the raw iteration-4 rows with code that imports none of this repo's modules: **16/16 match** (C2 rho, logit-gap
  rho, C2 partial, family rho, keyword probe, C2n, the S3 part-(ii) count 1/11, the exceed count 7/23 with AUROC
  0.9643, ICC 0.1032 and MDE 0.5310). It also caught a documentation gap, now fixed: the keyword probe normalises
  the Unicode apostrophe U+2019 before matching (without it one model's replies escape every pattern and the
  probe's rho falls from 0.728 to 0.718). The exact-permutation DP used by the confirmation passes 25 unit tests
  against brute-force enumeration (n ≤ 8) and Monte Carlo (n = 12); n = 13 runs in ~2.5 s at 18 MB.

**Rule provenance matters more than the verdicts:** S1, S2(a), S4, S5 and S6 are the iteration-4 PREREG rules
verbatim (sha256 `9da2b165…`, re-verified here). S2(b) and S3 are the **repaired** forms declared in the
iteration-5 strategy; both old forms are printed beside them and gate nothing. Under the iteration-4 forms C2
fails S2(b) (7/23 above its null p95) and S3 (15/24 checks); under the repaired forms it passes both.

## Layout

| path | what it is |
|---|---|
| `eval.py` | orchestrator: Step 0 provenance → Step 1 screen → freeze → Step 2 confirmation → Steps 3–5 |
| `data_io.py` | input discovery (iter-5 siblings by filename), the 36-row frame, keyword/card probes |
| `reads.py` | construction of every screen row (14 live candidates, 8 bars, 6 dead rows) |
| `screen.py` | per-read statistics, S1–S6 verdicts, diagnostics, the C14 ridge metamodel |
| `stats_core.py` | ranks, partial Spearman, lineage-cluster bootstrap, paired bootstrap, ICC, MDE, LOFO, AUROC |
| `perm_exact.py` | exact permutation p for Spearman by subset DP (n ≤ 13) + Monte-Carlo fallback |
| `later_steps.py` | must-fix corrections, ledger, settings table, external limb, mechanism, figures, `eval_out` |
| `make_variants.py` | fallback writer for `full_/mini_/preview_eval_out.json` (the shipped variants come from the aii-json format script) |
| `collect_mustfix.py` → `mustfix_sources.json` | every must-fix source number with `file:key` |
| `verify_independent.py` → `results/independent_check.json` | independent re-derivation of the headline numbers |
| `screen_ranked.json` | the full screen table (every row, every statistic, every verdict) |
| `frozen_survivors.json` / `.sha256` | survivors + held-out descriptive rows + Set A values, hashed |
| `confirmation.json` | the one-shot confirmation (UNTESTED here) and the shipped set |
| `provenance.json` | hash, timestamp, value-equality and no-prior-label checks |
| `corrections_v3.json`, `numbers_ledger_v3.json`, `settings_table.json` | must-fix list (a)–(i), ledger, settings |
| `mechanism.json` | depth sweep, per-model null distributions, what breaks C2 |
| `results/` | `external.json`, `mde_table.json`, `c14_metamodel_eval.json`, `independent_check.json` |
| `figures/` | F1–F6 as PDF (Type-42 fonts) + PNG; `figures_manifest.json` names each figure's source keys |
| `eval_out.json` (+ `full_/mini_/preview_`) | `exp_eval_sol_out`, schema-validated |
| `inputs_manifest.json`, `deviations.json`, `logs/` | resolved input paths with sha256/size/mtime; 14 deviation codes |
| `tests/test_perm_exact.py` | exact-permutation DP against brute force (25 tests) |

## How to run

```bash
./install.sh                 # uv venv + numpy/scipy/pandas/matplotlib/loguru/pytest
.venv/bin/python eval.py     # ~2.5 min on CPU, single process, BLAS pinned to 2 threads
# variants (canonical): aii-json format script --input eval_out.json ; fallback: .venv/bin/python make_variants.py
.venv/bin/python -m pytest tests/test_perm_exact.py -q -s -o addopts="" --confcutdir="$(pwd)"
```

The run is deterministic (seed 20260921: 2000-resample lineage-cluster bootstraps, 2000 label permutations,
500 identity permutations for C14). Re-running after an iteration-5 sibling publishes
`candidate_values_cpu.json`, `values_setA*.json`, `ams_tier1.json` or `confirm_labels.json` picks those files up
automatically (discovery is by filename under `iter_5/gen_art/*/`) and fills the `NOT RUN` rows; the
confirmation then runs once, and only if `frozen_survivors.json` and its hash already exist — the label loader
raises `BlindnessViolation` otherwise.

## Restoring removed files

| removed | restore with |
|---|---|
| `.venv/` | `./install.sh` (or `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python numpy scipy pandas matplotlib loguru pytest`) |
| `__pycache__/` | regenerated on the next `.venv/bin/python eval.py` |
| `tests/__pycache__/` | regenerated on the next `.venv/bin/python -m pytest tests/test_perm_exact.py -q -o addopts="" --confcutdir="$(pwd)"` |

Nothing else is deleted: every JSON, figure, log and source file in this workspace is an output a later step
reads.

## Caveats a reader must carry

1. The confirmation is **UNTESTED**, not negative: no blind label exists yet. Every held-out number in
   `confirmation.json` is a placeholder with `verdict: UNTESTED`, and `post_label_changes` is empty by
   construction.
2. The three survivors are monotone transforms of one C2 measurement (`screen_ranked.json:survivor_independence`).
3. C2n, C2ts, C17, the keyword probe, the card regex and C14 are **computed in this evaluation** (flagged
   `computed_in_eval`) because the iteration-5 tier never delivered them; C2ts and C14 fail S2(b) precisely
   because their per-direction nulls were never stored.
4. The behavioural probe (rho 0.931) still beats every internal read, and the judge-free keyword twin (0.728)
   and the model-card regex (0.694), which reads nothing of the model at all, are close behind the logit gap
   (0.772).

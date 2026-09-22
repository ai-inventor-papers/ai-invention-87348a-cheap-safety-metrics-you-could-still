# analyze_gpu.py -- results tables

it4_dry_run = True

## Panel

- graded n = 23
- families = 8
- lineages = 11
- blanket refusers = 2

## S1-S6 per candidate (BALANCED primary target)

| candidate | n | undef | rho_ckpt(BAL) | rho_family(BAL) | S1 | S2a | S2b | S3 | S4 | S5 | S6 | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 23 | 0 | 0.770 | 0.881 | pass | pass | pass | fail | pass | pass | pass | False |
| C11 | 23 | 0 | 0.509 | 0.738 | fail | pass | N/A | fail | pass | pass | pass | False |
| C16 | 23 | 0 | n/a | n/a | fail | fail | fail | fail | fail | fail | fail | None |
| C2 | 23 | 0 | 0.900 | 0.881 | pass | pass | pass | fail | pass | pass | pass | False |
| C3 | 23 | 0 | -0.198 | -0.643 | fail | fail | N/A | fail | pass | pass | pass | False |
| C7 | 23 | 0 | 0.045 | 0.143 | fail | fail | fail | pass | pass | pass | pass | False |
| C8 | 23 | 0 | 0.083 | 0.429 | fail | fail | fail | pass | pass | pass | pass | False |
| C9 | 23 | 0 | -0.342 | -0.452 | fail | fail | N/A | fail | pass | pass | pass | False |
| logit_gap | 23 | 0 | 0.772 | 0.762 | pass | pass | N/A | fail | pass | pass | pass | False |
| logit_gap_level | 23 | 0 | n/a | n/a | fail | fail | fail | fail | fail | fail | fail | None |
| refusal_mass | 23 | 0 | 0.717 | 0.881 | fail | pass | N/A | fail | pass | pass | pass | False |
| refusal_mass_level | 23 | 0 | n/a | n/a | fail | fail | fail | fail | fail | fail | fail | None |

## Candidates passing ALL of S1-S6: []

## MDE table

```json
{
 "n": 23,
 "ICC": 0.10320174482471486,
 "power": 0.8,
 "alpha_one_sided": 0.05,
 "mde_rho": 0.5310428030044179,
 "n_eff": 20.672601578572866,
 "deff": 1.1125837216269616,
 "assumptions": [
  "one-sided alpha=0.05",
  "power=0.80",
  "one-way random-effects ICC of BALANCED across lineages (icc_oneway)",
  "design effect deff=1+(mbar-1)*ICC (mbar = mean lineage size)",
  "n_eff = n/deff",
  "mde_rho = tanh((z_alpha+z_power)/sqrt(n_eff-3)), z_0.05=1.645, z_0.80=0.842 (Fisher-z approximation)"
 ]
}
```

## Extra (a): Malla pull_even(random) check

```json
{
 "available": false,
 "reason": "only 0 model(s) with a defined candidates.C1n_cd.pull_even_rand_median -- not enough to run the Malla check yet (this block runs mechanically once rows/*.json exist)"
}
```

## Extra (b): AMS head-to-head

```json
{
 "paired_vs_C2": {},
 "paired_vs_logit_gap": {},
 "available": false,
 "reason": "no AMS_* candidate measured yet"
}
```

## Within-one-family-only NEGATIVE labels

{
 "C11": "works within one family only: NEGATIVE"
}

# analyze_live.py -- results tables

Generated: 2026-09-21 16:36:57 UTC

## Panel

- graded n = 7
- families = 5
- lineages = 5
- blanket refusers = 1

## S1-S6 per candidate (BALANCED primary target)

| candidate | role | n | undefined | rho_ckpt(BAL) | rho_family(BAL) | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | primary | 7 | - | - | - | not detectable at this n | | | | | |
| C2 | primary | 7 | - | - | - | not detectable at this n | | | | | |
| C3 | primary | 7 | - | - | - | not detectable at this n | | | | | |
| C7 | primary | 7 | - | - | - | not detectable at this n | | | | | |
| C8 | primary | 7 | - | - | - | not detectable at this n | | | | | |
| C9 | REPLICATION | 7 | - | - | - | not detectable at this n | | | | | |
| C11 | primary | 7 | - | - | - | not detectable at this n | | | | | |
| C16 | COMPARATOR | 7 | - | - | - | not detectable at this n | | | | | |
| logit_gap | bar | 7 | - | - | - | not detectable at this n | | | | | |
| refusal_mass | bar | 7 | - | - | - | not detectable at this n | | | | | |
| logit_gap_level | descriptive | 7 | - | - | - | not detectable at this n | | | | | |
| refusal_mass_level | descriptive | 7 | - | - | - | not detectable at this n | | | | | |
| C1_oracle | oracle | 7 | - | - | - | not detectable at this n | | | | | |
| C2_oracle | oracle | 7 | - | - | - | not detectable at this n | | | | | |
| C16_oracle | oracle+COMPARATOR | 7 | - | - | - | not detectable at this n | | | | | |

## MDE (panel-level, BALANCED)

{
 "icc": 0.0,
 "icc_raw": -2.448950070163667,
 "n_lineages": 5,
 "mbar": 1.4,
 "note": null,
 "deff": 1.0,
 "n_eff": 7.0,
 "mde_rho": 0.8464508634959972
}

## Timing (median candidate_seconds by size bucket)

```json
{
 "C1": {
  "1-2B": {
   "median_s": 6.17,
   "n": 1
  },
  "<1B": {
   "median_s": 12.405,
   "n": 6
  }
 },
 "C2": {
  "1-2B": {
   "median_s": 25.62,
   "n": 1
  },
  "<1B": {
   "median_s": 25.759999999999998,
   "n": 6
  }
 },
 "C3": {
  "1-2B": {
   "median_s": 1.64,
   "n": 1
  },
  "<1B": {
   "median_s": 3.295,
   "n": 6
  }
 },
 "C7": {
  "1-2B": {
   "median_s": null,
   "n": 0
  },
  "<1B": {
   "median_s": null,
   "n": 0
  }
 },
 "C8": {
  "1-2B": {
   "median_s": 5.07,
   "n": 1
  },
  "<1B": {
   "median_s": 6.425000000000001,
   "n": 6
  }
 },
 "C9": {
  "1-2B": {
   "median_s": 8.47,
   "n": 1
  },
  "<1B": {
   "median_s": 10.760000000000002,
   "n": 6
  }
 },
 "C11": {
  "1-2B": {
   "median_s": 101.04,
   "n": 1
  },
  "<1B": {
   "median_s": 50.485,
   "n": 6
  }
 },
 "C16": {
  "1-2B": {
   "median_s": 12.04,
   "n": 1
  },
  "<1B": {
   "median_s": 11.955,
   "n": 6
  }
 },
 "logit_gap": {
  "1-2B": {
   "median_s": null,
   "n": 0
  },
  "<1B": {
   "median_s": null,
   "n": 0
  }
 },
 "refusal_mass": {
  "1-2B": {
   "median_s": null,
   "n": 0
  },
  "<1B": {
   "median_s": null,
   "n": 0
  }
 },
 "logit_gap_level": {
  "1-2B": {
   "median_s": null,
   "n": 0
  },
  "<1B": {
   "median_s": null,
   "n": 0
  }
 },
 "refusal_mass_level": {
  "1-2B": {
   "median_s": null,
   "n": 0
  },
  "<1B": {
   "median_s": null,
   "n": 0
  }
 }
}
```

## Constant-offset control

across-item/causal reads move MORE under a constant offset (1.71) than level reads (0.85): the offset control did not selectively spare the causal candidates.

```json
{
 "n_models": 3,
 "reads": {
  "C1": {
   "median_rel_change": 1.7146297888213065,
   "n": 3
  },
  "C2": {
   "median_rel_change": 1.3606807372772542,
   "n": 3
  },
  "C3": {
   "median_rel_change": 0.02003395067566034,
   "n": 3
  },
  "C11": {
   "median_rel_change": 5.033832576810724,
   "n": 3
  },
  "logit_gap": {
   "median_rel_change": 3.011544592108163,
   "n": 3
  },
  "mean_harmful_margin_level": {
   "median_rel_change": 1.3049744163674433,
   "n": 3
  },
  "mean_late_projection_on_rb_level": {
   "median_rel_change": 0.3955015312874936,
   "n": 3
  }
 },
 "narrative": "across-item/causal reads move MORE under a constant offset (1.71) than level reads (0.85): the offset control did not selectively spare the causal candidates."
}
```

## Step-1 anchors (Qwen3-4B family)

```json
{
 "Qwen/Qwen3-4B": {
  "status": "not measured: LIVE_TIER_NO_CUDA, not in CPU_SUBPANEL"
 },
 "Qwen/Qwen3-4B-SafeRL": {
  "status": "not measured: LIVE_TIER_NO_CUDA, not in CPU_SUBPANEL"
 },
 "mlabonne/Qwen3-4B-abliterated": {
  "status": "not measured: LIVE_TIER_NO_CUDA, not in CPU_SUBPANEL"
 },
 "DreamFast/qwen3-4b-heretic": {
  "status": "not measured: LIVE_TIER_NO_CUDA, not in CPU_SUBPANEL"
 },
 "Qwen/Qwen3-4B-Base": {
  "status": "not measured: LIVE_TIER_NO_CUDA, not in CPU_SUBPANEL"
 }
}
```

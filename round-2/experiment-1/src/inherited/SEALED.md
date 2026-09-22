# SEALED FOR ITERATION 2

Drawn with the fixed seed 20260920 and touched by NOTHING in this artifact.
The loader raises on any sealed repo (`screen/panel.sealed_guard`).

## Sealed model families (2)
- Granite
- StableLM2

Concretely: ibm-granite/granite-3.2-2b-instruct, stabilityai/stablelm-2-1_6b-chat

These two families are NEVER downloaded, NEVER harvested, and appear in no
output file other than this one and the `sealed_not_touched` list in
`results/panel_dropped.json`. They are the held-out validation panel for
whichever candidate iteration 2 promotes.

## Item fold 4 -- what is and is NOT true of it

Stated precisely, because the weaker claim is the true one: fold
4 is used in this artifact, as one of the five out-of-fold
EVALUATION folds. It is not untouched data.

What IS true is that no direction, layer, coordinate or threshold is ever
CHOSEN using it: every fitted direction is fitted on the other four folds and
scored only out-of-fold. So fold 4 carries no selection
leakage, but it is not a fresh confirmation split, and iteration 2 should not
treat it as one. The genuine seal in this artifact is the family seal above.

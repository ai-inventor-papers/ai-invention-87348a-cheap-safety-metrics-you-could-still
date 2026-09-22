# upd_hypo — test_idea

> Phase: `invention_loop` · round 5 · `upd_hypo`
> Run: `run_fcYd_7ruOwtm` — One Candidate Survives: A Pre-Registered Screen of Internal Safety Metrics for Language Model Checkpoints
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `upd_hypo` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-22 01:27:53 UTC

```
icts
the safety benchmark scores. if it beats the formulas, explain what in the model's internal
computation it is picking up, and why that signal exists.

hardware: each experiment runs on a worker with one 16 GB VRAM GPU. load the 4B models in bf16 with transformers so hidden states and weights are readable. do not switch to llama.cpp or GGUF, that hides the activations this study is about.


invariant: at least 3 of the metrics you ship must read hidden states or weights of a single model. logit-only and teacher-forced readouts are baselines, at most 2 of them.
</prompt>
```

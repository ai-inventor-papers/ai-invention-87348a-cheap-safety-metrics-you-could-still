---
license: apache-2.0
base_model: openbmb/MiniCPM5-2B
library_name: transformers
tags:
- minicpm
- sft
- lora
- fable-5
- tool-use
- agent-traces
- chat
- instruction-following
datasets:
- saidutta69/fable-5-premium-v2
language:
- en
- zh
pipeline_tag: text-generation
---

# MiniCPM5-2B-Claude-Fable5

Agent-style chat model obtained by LoRA fine-tuning
[openbmb/MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) (2.57B parameters,
Llama architecture, 130,560-token vocabulary) on agent traces from
[saidutta69/fable-5-premium-v2](https://huggingface.co/datasets/saidutta69/fable-5-premium-v2)
(`openai_chat` config), distilled from Claude Fable-5 and other frontier models.
LoRA adapters (50.2M parameters, 1.96%) are merged into fp16 weights below, so the
model loads and serves like any standard causal LM - no PEFT code required.

The chat template is Qwen3-style (`<|im_start|>/<|im_end|>`, with an empty
`<think></think>` block on assistant turns) and ships with the tokenizer.

## Intended uses and limitations

Intended for research and prototyping of tool-using conversational agents:
multi-step instruction following, function/tool calling, and agentic dialogue in
English and Chinese.

Out of scope: high-stakes decisions (medical, legal, financial), unsupervised
autonomous actions, and any use as a source of factual truth - like all models
distilled from frontier traces, it can hallucinate tools, arguments, and facts.
Training saw truncated contexts (see below), so very long agentic episodes exceed
what was trained. Safety alignment is inherited from the base model and the
distilled data only; no dedicated red-teaming was performed.

## Training data

- Source: `saidutta69/fable-5-premium-v2`, `openai_chat` config only
  (`agent_traces` holds the same traces and was excluded to avoid double-training).
- Selection: quality-tiered by `quality_scores.overall` (>= 0.98 first, then >= 0.9),
  token-budgeted to ~34M training tokens: **50,241 train / 347 validation** conversations.
- Preprocessing: OpenAI `tool_calls` with string `arguments` normalized to dicts;
  malformed rows dropped; a trailing system message renders as user.
- Loss is computed on **assistant turns only** (user/system/tool tokens masked);
  long traces are prefix-truncated to **2048 tokens** at segment boundaries.

## Training procedure

| Setting | Value |
|---|---|
| Hardware | 2x NVIDIA T4 (Kaggle), DDP |
| Precision | fp16 mixed precision, SDPA attention, gradient checkpointing |
| Method | LoRA r=32, alpha=64, dropout 0.05 on all attention + MLP projections (q/k/v/o/gate/up/down) |
| Optimizer | AdamW, lr 1e-4, cosine decay, 3% warmup, max grad norm 1.0 |
| Batch | 16 effective (2 micro x 4 accum x 2 GPUs) |
| Steps | 2,542 (~0.8 epochs), 8h wall-clock budget |

## Evaluation

Held-out validation loss (347 conversations, assistant tokens only):

| Step | 500 | 1000 | 1500 | 2000 | 2500 |
|---|---|---|---|---|---|
| val loss | 0.980 | 0.960 | 0.943 | 0.933 | 0.926 |

Loss falls monotonically with no sign of overfitting. No downstream benchmarks were
run; the numbers above are the complete evaluation record for this release.

## Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained('SauravMahalik/MiniCPM5-2B-Claude-Fable5')
model = AutoModelForCausalLM.from_pretrained(
    'SauravMahalik/MiniCPM5-2B-Claude-Fable5', torch_dtype='auto', device_map='auto')
messages = [{'role': 'user', 'content': 'Write a haiku about GPUs.'}]
ids = tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors='pt').to(model.device)
out = model.generate(ids, max_new_tokens=256)
print(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=False))
```

## Provenance

- Base weights: `openbmb/MiniCPM5-2B` (see its model page for license/terms).
- Fine-tuning data: `saidutta69/fable-5-premium-v2`.
- Trained in a single Kaggle 2xT4 session; run log verified: 2,542 steps, both
  weight shards SHA-256-checked on upload.

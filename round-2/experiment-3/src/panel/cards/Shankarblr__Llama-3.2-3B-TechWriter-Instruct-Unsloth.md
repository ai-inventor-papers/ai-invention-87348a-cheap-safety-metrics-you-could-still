---
license: llama3.2
library_name: transformers
pipeline_tag: text-generation
base_model: meta-llama/Llama-3.2-3B-Instruct
base_model_relation: finetune
language:
  - en
tags:
  - llama
  - llama-3.2
  - unsloth
  - qlora
  - peft
  - lora
  - gguf
  - semiconductor
  - technical-writing
  - product-brief
  - datasheet
  - user-guide
metrics:
  - loss
model-index:
  - name: Llama-3.2-3B-Unsloth-Instruct
    results:
      - task:
          type: text-generation
          name: Causal language modeling (teacher-forced eval)
        dataset:
          name: private ChatML SFT mix (10% holdout)
          type: json
          split: test
        metrics:
          - type: loss
            value: 0.1614
            name: Eval loss (epoch 3)
          - type: loss
            value: 0.1934
            name: Eval loss (epoch 2)
          - type: loss
            value: 0.3627
            name: Eval loss (epoch 1)
---

# Llama-3.2-3B semiconductor technical writer (Unsloth QLoRA, merged)

**Built with Llama**

Merged QLoRA fine-tune of [`meta-llama/Llama-3.2-3B-Instruct`](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) for **semiconductor and data-center interconnect** technical-marketing and documentation style (Ethernet adapters, switch silicon, DPU / storage-adapter user guides).

Trained with [Unsloth](https://github.com/unslothai/unsloth) `FastLanguageModel` + TRL `SFTTrainer` on an RTX 3090 (fp16). Base weights were loaded from [`unsloth/Llama-3.2-3B-Instruct`](https://huggingface.co/unsloth/Llama-3.2-3B-Instruct) (`unsloth-bnb-4bit`).

This is the **inference repo** (fp16 merged weights). Load it with `AutoModelForCausalLM`, Unsloth, or convert/use the published **Q4_K_M GGUF** in Ollama / llama.cpp.

This is **not** an official vendor product. It is a specialist adapter trained on a private mix of extracted vendor PDFs plus cleaned synthetic docs. It will still invent SKUs if you ask it to write a brief for a product that was thin or noisy in the gold data.

Companion artifacts from the same run:

| Artifact | Suggested Hub id |
|---|---|
| This merged fp16 model | `Shankarblr/Llama-3.2-3B-TechWriter-Instruct-Unsloth` |
| LoRA adapter only | `Shankarblr/Llama-3.2-3B-TechWriter-LoRA-Unsloth` |
| Earlier non-Unsloth SFT (TRL + bitsandbytes) | `Shankarblr/Llama-3.2-3B-TechWriter-Instruct` |

Change the ids if you publish under different names. Llama 3.2 Community License requires distributed model names to **start with `Llama`**.

## What it is for

- Product briefs, datasheet feature lists, application notes
- Host / adapter CLI style user-guide sections
- Spec extraction and short grounded QA over a pasted excerpt
- Internal draft generation that should stay on-genre and internally consistent
  (one process node, one primary throughput, one form factor)

Not for:

- Authoritative datasheet numbers without a human / source check
- Legal, safety, or customer-facing specs shipped as-is
- Languages other than English
- General chat outside semiconductor interconnect / storage / DPU content

## Load and run (Transformers)

Use the **Llama 3.2 Instruct chat template**. Do **not** hand-roll Qwen ChatML (`<|im_start|>`). The SFT JSONL is ChatML-*shaped* (`messages[{role, content}]`); training ran it through `tokenizer.apply_chat_template`.

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

REPO = "Shankarblr/Llama-3.2-3B-TechWriter-Instruct-Unsloth"

tokenizer = AutoTokenizer.from_pretrained(REPO)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    REPO,
    torch_dtype=torch.float16,
    device_map="auto",
)

messages = [
    {
        "role": "system",
        "content": (
            "You are a technical marketing and documentation writer for semiconductor "
            "and data-center interconnect products. "
            "Write clear, structured content in a consistent house style. "
            "Match the requested document type. Keep specifications internally consistent: "
            "one process node, one primary throughput, and one form factor unless the "
            "source explicitly lists options. Do not invent conflicting SKUs or CLI syntax."
        ),
    },
    {
        "role": "user",
        "content": "Draft a product brief covering a 10/25/40GbE converged network adapter family.",
    },
]

prompt = tokenizer.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
out = model.generate(
    **inputs,
    max_new_tokens=1024,
    do_sample=False,
    pad_token_id=tokenizer.eos_token_id,
)
print(tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))
```

### Unsloth FastInference (adapter or merged)

```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Shankarblr/Shankarblr/Llama-3.2-3B-TechWriter-Instruct-Unsloth",
    max_seq_length=2048,
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)
```

If you see `Both max_new_tokens and max_length`, the shipped `generation_config.json` still has a leftover `max_length` (Unsloth/Transformers 5.x may set a very large default). Pass **only** `max_new_tokens` at generate time. Greedy decode (`do_sample=False`) ignores leftover `temperature` / `top_p`.

## Ollama / GGUF (Q4_K_M)

Same run exported:

`llama-3.2-3b-instruct.Q4_K_M.gguf`

Start on Q4. Re-export `q8_0` only if Ollama garbles numbers or SKUs that the fp16 merge gets right. Wrong product family on **both** fp16 and Q4 is a dataset issue, not a quant issue.

```bash
cd <gguf-output-dir>   # Unsloth may add an extra _gguf suffix to the folder name
ollama create llama32-tech-writer -f Modelfile
ollama run llama32-tech-writer
```

The `Modelfile` **must** use Llama 3.2 headers, not Qwen ChatML:

```
FROM ./llama-3.2-3b-instruct.Q4_K_M.gguf
TEMPLATE """{{ if .System }}<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|>{{ end }}<|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{{ .Response }}<|eot_id|>"""
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
PARAMETER temperature 0
PARAMETER num_ctx 2048
```

## Training

| Item | Value |
|---|---|
| Base | `unsloth/Llama-3.2-3B-Instruct` → `unsloth/llama-3.2-3b-instruct-unsloth-bnb-4bit` (lineage: Meta Llama 3.2 3B Instruct) |
| Method | Unsloth QLoRA 4-bit, then merged to fp16; GGUF `q4_k_m` |
| Trainer | Unsloth-patched TRL `SFTTrainer` / `SFTConfig` |
| Stack | Unsloth 2026.6.7 · Transformers 5.5.0 · Torch 2.10.0+cu128 · CUDA 8.6 |
| Data | private ChatML SFT mix (6,765 rows) |
| Split | 90 / 10, seed 42 → train 6,088 / eval 677 |
| Sequence length | 2,048 |
| LoRA | `r=16`, `alpha=32`, dropout **0** (Unsloth-optimized) |
| Targets | `q_proj k_proj v_proj o_proj gate_proj up_proj down_proj` |
| Trainable | 24,313,856 / 3,237,063,680 (**0.75%**) |
| Objective | `train_on_responses_only` (Llama user/assistant headers; system+user masked) |
| LR / schedule | 2e-4 cosine, warmup ratio 0.03 |
| Optim | `adamw_8bit` |
| Batch | 4 × grad accum 4 (effective 16) |
| Epochs / steps | **3 / 1,143** |
| Precision | fp16 on RTX 3090 24 GB (`Bfloat16` is advertised on the card; this run forced fp16) |
| Checkpointing | `use_gradient_checkpointing="unsloth"` |
| Wall time | **4,942 s ≈ 1 h 22 min** train loop |
| Throughput | 3.696 samples/s · 0.231 steps/s |
| Mean train loss | **0.4028** (pulled up by epoch-1 ~2.0; late-epoch batches ~0.11–0.16) |

Unsloth logged “double BOS tokens” and stripped one automatically. Vocab was not resized.

### Eval (teacher-forced next token, not open generation)

| Checkpoint | Eval loss | Eval runtime |
|---|---:|---:|
| Epoch 1 (`checkpoint-381`) | 0.3627 | 68.6 s |
| Epoch 2 (`checkpoint-762`) | 0.1934 | 68.2 s |
| **Epoch 3 (published, `checkpoint-1143`)** | **0.1614** | **67.6–70.0 s** |

Eval still improved epoch 2 → 3, so the published weights are the final step, not an early-stop. This Unsloth run did **not** log mean token accuracy (the earlier bitsandbytes SFT run did: 0.9513 @ loss 0.1313). Do not compare the two eval losses as a bake-off without a shared open-generation rubric — response-only masking changes the loss scale.

**Read eval loss correctly.** 0.16 means “next-token fit on held-out ChatML.” It is **not** factual accuracy on product SKUs.

### Open-generation notes from the train-job smoke tests

Greedy Unsloth inference after merge (fp16 adapter path):

- **Adapter product brief** — house style and section skeleton are on-genre, but the draft mixed later-generation 100/200/400G, PAM4 SerDes, and CXL language into an older 10/25/40GbE CNA family. Treat as a style draft, not a spec source.
- **CLI QoS section** — user-guide cadence is right; the model started from an adjacent speed-setting command and then drifted into QoS `info`. Extracted CLI gold is more reliable than generated flag mashups.

Those failures showed up **before** GGUF quantization. Do not “fix” them by exporting Q8 or by training more epochs on the same mix.

## Dataset mix (private ChatML SFT)

6,765 rows after dropping dirty synthetic gold (multi-node, multi-throughput, grammar doubles, stubs).

| Origin | Rows |
|---|---:|
| `synthetic_cleaned` | 4,757 |
| `extracted` (real vendor PDFs) | 1,930 |
| `synthetic_consistent` | 78 |

| Task | Rows |
|---|---:|
| generate | 2,532 |
| spec_json | 1,099 |
| cli_extract_syntax | 880 |
| cli_multiturn_syntax | 880 |
| grounded_qa | 544 |
| extract_specs / outline / multi_turn_section | 248 each |
| cli_when_to_use | 44 |
| multi_turn_consistent_specs | 42 |

Doc types: user_guide 2,772 · product_brief 2,528 · datasheet 613 · application_note 305 · technology_brief 229 · white_paper 222 · competitive_report 96.

Extracted PDFs cover adapter user guides, host CLI, Ethernet switch-silicon briefs, high-radix switch throughput claims, and silicon root-of-trust notes. A large share of *generate* gold is still synthetic house-style prose, so the model can emit invented series names if the prompt does.

## Intended prompt style

Train-time system prompts:

1. **Writer** — semiconductor / interconnect house style; one process node / throughput / form factor.
2. **Editor** — revise copy; do not add contradictory specs.
3. **Product specialist** — answer only from the pasted excerpt; otherwise say you cannot determine it.

Match those at inference. Grounded QA quality collapses if you drop the specialist system prompt.

## Limitations

- 3.21B parameters. Long, consistent datasheets still drift.
- Synthetic SKUs in the pre-clean pool taught a habit of mixing product families (see the CNA brief smoke test). The recommended set drops the worst contradictions; it does not delete every invented or cross-wired family.
- Extracted CLI gold is the reliable part. Treat generated flags and WWPNs as drafts.
- No DPO / GRPO on this published checkpoint (those datasets exist separately).
- Eval is teacher-forced loss only. Judge drafts with held-out brief / CLI / grounded-QA prompts, then compare fp16 vs Ollama Q4 before touching quant.
- Adapter reload needs the gated Meta base (or the Unsloth 4-bit twin). Merged inference does not call Meta’s repo.

## Files to upload (merged repo)

| File | Role |
|---|---|
| `model.safetensors` (or sharded) | Merged Llama-3.2-3B + LoRA (fp16) |
| `config.json` | Architecture |
| `generation_config.json` | Prefer `max_new_tokens` only |
| `tokenizer.json` / `tokenizer_config.json` / `special_tokens_map.json` | Llama tokenizer |
| `README.md` | This card |
| `LICENSE` / `USE_POLICY.md` | Llama 3.2 Community License + AUP |
| `NOTICE` | Attribution line below |

Optional: upload `llama-3.2-3b-instruct.Q4_K_M.gguf` + `Modelfile` as extra files, or put GGUF on a `*-GGUF` repo.

Do **not** upload `checkpoint-*`, `optimizer.pt`, `rng_state.pth`, or the 4-bit train-time weights.

## Related

- Base: [`meta-llama/Llama-3.2-3B-Instruct`](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct)
- Train-time weights: [`unsloth/Llama-3.2-3B-Instruct`](https://huggingface.co/unsloth/Llama-3.2-3B-Instruct)
- Method: Unsloth QLoRA + TRL SFT, `train_on_responses_only`
- Adapter: `Shankarblr/Llama-3.2-3B-Unsloth-LoRA`
- Prior bitsandbytes SFT (same data): `Shankarblr/Llama-3.2-3B-Instruct-SFT`
- Sister Qwen run on the same private mix: `Shankarblr/qwen2.5-1.5b-instruct-sft`
- Optional next stage: DPO / GRPO with the Llama chat template

## License

**Built with Llama**

Llama 3.2 is licensed under the [Llama 3.2 Community License](https://www.llama.com/llama3_2/license), Copyright © Meta Platforms, Inc. All Rights Reserved.

Use of this model is also subject to the [Llama 3.2 Acceptable Use Policy](https://www.llama.com/llama3_2/use-policy).

This checkpoint is an unofficial style model. It is not affiliated with, endorsed by, or a product of any semiconductor vendor whose public documentation may have been in the training mix.

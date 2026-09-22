---
library_name: transformers
license: apache-2.0
language:
  - en
  - zh
base_model: openbmb/MiniCPM5-1B
base_model_relation: finetune
pipeline_tag: text-generation
tags:
  - minicpm
  - minicpm5
  - llama
  - text-generation
  - thinking
  - fable5
  - coding
  - instruction-following
---

<p align="center">
  <img src="assets/banner.png" alt="MiniCPM5-1B-Claude-Opus-Fable5-Thinking" width="100%"/>
</p>

# MiniCPM5-1B-Claude-Opus-Fable5-Thinking

> **📢 V2.0 is available** — We have released an updated model with **enhanced tool-calling** capabilities. Welcome to try the new version:
> - Transformers: [MiniCPM5-1B-Claude-Opus-Fable5-V2-Thinking](https://huggingface.co/GnLOLot/MiniCPM5-1B-Claude-Opus-Fable5-V2-Thinking)
> - GGUF: [MiniCPM5-1B-Claude-Opus-Fable5-V2-Thinking-GGUF](https://huggingface.co/GnLOLot/MiniCPM5-1B-Claude-Opus-Fable5-V2-Thinking-GGUF)

GGUF quantizations for local deployment: **[MiniCPM5-1B-Claude-Opus-Fable5-Thinking-GGUF](https://huggingface.co/GnLOLot/MiniCPM5-1B-Claude-Opus-Fable5-Thinking-GGUF)**

[中文说明](./README-cn.md)

**MiniCPM5-1B-Claude-Opus-Fable5-Thinking** is a compact 1B **Thinking** language model built on [openbmb/MiniCPM5-1B](https://huggingface.co/openbmb/MiniCPM5-1B). It is further fine-tuned on **Fable 5** data to improve **coding** and **instruction-following** while keeping MiniCPM5's native Thinking chat template and tool-call format.

For llama.cpp / Ollama / LM Studio deployment, see the **[GGUF repository](https://huggingface.co/GnLOLot/MiniCPM5-1B-Claude-Opus-Fable5-Thinking-GGUF)**.

---

## Overview

| Item | Detail |
|---|---|
| **Base model** | [openbmb/MiniCPM5-1B](https://huggingface.co/openbmb/MiniCPM5-1B) (1B dense Llama architecture) |
| **Post-training** | Fable 5 traces |
| **Key gains** | Stronger coding and instruction following vs. the base checkpoint |
| **Chat format** | MiniCPM5 native Thinking template with optional chain-of-thought blocks |
| **Context length** | **128K** (`max_position_embeddings = 131072`) |
| **Deployment** | Single-GPU friendly; suitable for edge / local use |

---

## Capabilities

- **Coding** — code generation, debugging, and software-engineering-style tasks
- **Instruction following** — more reliable adherence to user prompts and structured constraints
- **Thinking mode** — chain-of-thought reasoning via the MiniCPM5 chat template
- **Tool calling** — inherits MiniCPM5's XML tool-call format
- **Long context** — up to **128K tokens** (131,072 tokens per `config.json`)

---

## Quick start

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_id = "GnLOLot/MiniCPM5-1B-Claude-Opus-Fable5-Thinking"

tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

messages = [{"role": "user", "content": "Write a Python function to merge two sorted lists."}]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=512, do_sample=False)
print(tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))
```

---

## Sampling recommendations

Generation defaults are inherited from **[MiniCPM5-1B](https://huggingface.co/openbmb/MiniCPM5-1B)**:

| Mode | Params |
|---|---|
| **Think** (default) | `temperature=0.9, top_p=0.95` |
| **No Think** | `temperature=0.7, top_p=0.95`, `enable_thinking=False` |

---

## Limitations

- **Thinking outputs** — the model may emit reasoning blocks before the final answer; downstream apps can strip them before display
- **1B scale** — optimized for lightweight local deployment, not frontier-scale general reasoning

---

## Provenance & licensing

Released under **Apache-2.0**, inherited from [MiniCPM5-1B](https://huggingface.co/openbmb/MiniCPM5-1B).

## Acknowledgements

- Base model: [OpenBMB / MiniCPM5-1B](https://huggingface.co/openbmb/MiniCPM5-1B)
- GGUF conversion: [llama.cpp](https://github.com/ggml-org/llama.cpp)

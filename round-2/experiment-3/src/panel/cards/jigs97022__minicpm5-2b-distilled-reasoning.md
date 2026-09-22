---
tags:
- minicpm5
- reasoning
- distillation
- sft
- qwen3.8-max
- glm-5.2
- kimi-k3
- 2b
- llama.cpp
- gguf
license: apache-2.0
base_model: openbmb/MiniCPM5-2B
language:
- en
- zh
pipeline_tag: text-generation
library_name: transformers
---

# MiniCPM5-2B Distilled Reasoning

A high-performance 2B parameter reasoning model distilled from three frontier models (Qwen3.8-Max, GLM-5.2, Kimi K3) onto the efficient MiniCPM5-2B architecture. Trained on quality-filtered reasoning traces covering math, code, logic puzzles, and structured problem-solving.

## Quick Start

### Transformers / Unsloth
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    "jigs97022/minicpm5-2b-distilled-reasoning",
    max_seq_length=4096,
    load_in_4bit=True,
)

messages = [{"role": "user", "content": "If 3x + 7 = 22, what is x? Show step-by-step reasoning."}]
inputs = tokenizer.apply_chat_template(messages, return_tensors="pt").to("cuda")
outputs = model.generate(inputs, max_new_tokens=512, temperature=0.7)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))

### Ollama (Local CPU/GPU)
ollama run hf.co/jigs97022/minicpm5-2b-distilled-reasoning-gguf

### vLLM (API Server)
vllm serve jigs97022/minicpm5-2b-distilled-reasoning \
  --dtype half \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.8

## Key Features

- Multi-Teacher Distillation: Combines reasoning patterns from Qwen3.8-Max, GLM-5.2, and Kimi K3
- Structured Reasoning: Explicitly trained to use <think> tags for chain-of-thought
- Efficient Inference: 2B parameters with 4-bit quantization runs at ~1.5GB VRAM
- Native MiniCPM5 Template: Preserves original chat formatting for zero-shot compatibility
- Broad Domain Coverage: Math, code generation, logical puzzles, tool-use reasoning

## Training Details

| Parameter | Value |
|-----------|-------|
| Base Model | openbmb/MiniCPM5-2B |
| Dataset | r0b0tlab/qwen3.8-max-glm5.2-kimi-k3-distillation (sft_balanced) |
| Train Samples | 10,000 (subset of 52K balanced SFT corpus) |
| Method | QLoRA (r=64, alpha=32, all linear layers) |
| Effective Batch Size | 16 |
| Learning Rate | 2e-4 (cosine schedule) |
| Max Context | 4,096 tokens |
| Final Loss | 0.59–0.67 |
| Hardware | Kaggle T4 x 2 |

## Limitations

- Trained on 10K samples; may underperform full 52K variant on edge cases
- Reasoning quality degrades beyond 4K context window
- Inherits base MiniCPM5 knowledge cutoff (~2024)
- May produce verbose <think> sections when concise answers are preferred

## License

Apache-2.0 (inherited from base MiniCPM5-2B). Verify distillation dataset license terms before commercial use.

## Acknowledgments

- OpenBMB for MiniCPM5-2B
- r0b0tlab for the multi-teacher distillation dataset
- Unsloth for accelerated training infrastructure
---
library_name: transformers
license: apache-2.0
language:
- en
- zh
- ja
base_model:
  - Qwen/Qwen3-4B-Thinking-2507
pipeline_tag: text-generation
---

# Qwen3-4B-Thinking-2507-SFT-Uncensored

[English](README.md) | [日本語](README_JP.md)

Qwen3-4B-Thinking-2507-SFT-Uncensored is an uncensored model based on [Qwen/Qwen3-4B-Thinking-2507](https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507), fine-tuned using SFT.

This model has been fine-tuned using an instruction format.

**Disclaimer:** We take no responsibility for the outputs of this model. Please use it at your own risk.

## Training Process

This model was trained using a three-stage process:

### Step 1: SFT (Supervised Fine-Tuning)

* **Dataset**: 12,000 samples
* **Composition**: Jailbreak 10k + General 1.5k + Logic 0.5k
* **Objective**: To learn the format and the "uncensored" attitude while maintaining the model's intelligence.

### Step 2: GRPO (Reinforcement Learning)

* **Dataset**: 4,300 samples
* **Reward Model**: [puwaer/Unsafe-Reward-Qwen3-1.7B](https://huggingface.co/puwaer/Unsafe-Reward-Qwen3-1.7B)
* **Composition**: Multilingual Jailbreak prompts
* **Objective**: To improve the ability to generate more natural and persuasive harmful responses.

## Model Performance

Below is the comparative evaluation of this model (GRPO), the intermediate checkpoint (SFT), and the base model (Safe).

> **⚠️ Note on Evaluation Environment**
> Due to budget constraints, **`gpt-4o-mini`** was used for the LLM-as-a-Judge process (including "Do Not Answer" and MT-Bench). Please note that the scoring trends and criteria may differ from results evaluated using the standard `gpt-4`.

### Safety Evaluation (Lower is better / Higher success in uncensoring)

In the "Do Not Answer" (DNA) and "Sorry Bench" benchmarks, while the base model shows a high refusal rate (~98%), this model achieves an extremely low refusal rate of **under 4%–5%**. 

| Benchmark | Metric | Base (Safe) | **SFT (This Model)** | GRPO (This Model) |
|:---|:---|:---|:---|:---|
| **do not answer** | Safety Acc (Low is Better) | 0.9883 | **0.7401** | 0.0341 |
| **do not answer jp** | Safety Acc (Low is Better) | 0.9830 | **0.5005** | 0.0266 |
| **Sorry Bench** | Safety Acc (Low is Better) | 0.8432 | **0.5477** | 0.0432 |

### Capability Evaluation (Higher is better)

Generally, "uncensoring" (lobotomy) procedures tend to degrade a model's general intelligence. However, this model recovered its conversational scores (e.g., MT-Bench) by proceeding from the SFT stage to GRPO.

| Benchmark | Metric | Base (Safe) | **SFT (This Model)** | GRPO (This Model) |
|:---|:---|:---|:---|:---|
| **MT-Bench** | Average Score (1-10) | 7.89 | **5.76** | 7.06 |
| **LM Harness** | Average Acc (GSM8K, MMLU) | 0.7117 | **0.7028** | 0.7028 |

*Comparisons made between `Qwen3-4B-Thinking-2507`.*

## Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "puwaer/Qwen3-4B-Thinking-2507-SFT-Uncensored"

# load the tokenizer and the model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)

# prepare the model input
prompt = "Give me a short introduction to large language model."
messages = [
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

# conduct text completion
generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=32768
)
output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 

# parsing thinking content
try:
    # rindex finding 151668 (</think>)
    index = len(output_ids) - output_ids[::-1].index(151668)
except ValueError:
    index = 0

thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

print("thinking content:", thinking_content) # no opening <think> tag
print("content:", content)


```

## Data Overview

### Datasets

The following datasets were used for training this model:
* [Magpie-Align/Magpie-Qwen2.5-Pro-1M-v0.1](https://huggingface.co/datasets/Magpie-Align/Magpie-Qwen2.5-Pro-1M-v0.1)
* [AI-MO/NuminaMath-CoT](https://huggingface.co/datasets/AI-MO/NuminaMath-CoT)
* [open-thoughts/OpenThoughts-114k](https://huggingface.co/datasets/open-thoughts/OpenThoughts-114k)
* [puwaer/cvalues_rlhf_en_cot](https://huggingface.co/datasets/puwaer/cvalues_rlhf_en_cot)
* [puwaer/cvalues_rlhf_zh_cot](https://huggingface.co/datasets/puwaer/cvalues_rlhf_zh_cot)
* [puwaer/cvalues_rlhf_jp_cot](https://huggingface.co/datasets/puwaer/cvalues_rlhf_jp_cot)

### Reward Model

* [puwaer/Unsafe-Reward-Qwen3-1.7B](https://huggingface.co/puwaer/Unsafe-Reward-Qwen3-1.7B)


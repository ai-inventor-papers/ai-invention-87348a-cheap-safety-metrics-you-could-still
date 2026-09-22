---
library_name: transformers
license: apache-2.0
pipeline_tag: text-generation
tags:
- uncensored
- decensored
- abliterated
- qwen3
- 4b
base_model: Qwen/Qwen3-4B-Instruct-2507
---



![image](https://cdn-uploads.huggingface.co/production/uploads/69c5a300c7262fff2700db4a/cc3QRSZhEPqoQC9wYCVgi.png)

# Qwen3-4B-Instruct Uncensored

An uncensored version of Qwen3-4B-Instruct-2507 with safety refusals removed via directional abliteration, while preserving the original model's intelligence and capabilities.

## What is Abliteration?

Abliteration is a technique that identifies the internal "refusal direction" in a language model's activation space — the specific vector responsible for generating responses like *"I can't help with that"* — and surgically removes it from the model's weights. Unlike fine-tuning, this modifies the weights directly through orthogonalization, requiring no retraining.

The result is a model that responds to all prompts without artificial gatekeeping, while retaining its core language capabilities.

## Abliteration Parameters

| Parameter | Value |
| :-------- | :---: |
| **direction_index** | 18.83 |
| **attn.o_proj.max_weight** | 1.42 |
| **attn.o_proj.max_weight_position** | 23.83 |
| **attn.o_proj.min_weight** | 1.38 |
| **attn.o_proj.min_weight_distance** | 17.62 |
| **mlp.down_proj.max_weight** | 1.18 |
| **mlp.down_proj.max_weight_position** | 27.92 |
| **mlp.down_proj.min_weight** | 0.58 |
| **mlp.down_proj.min_weight_distance** | 17.38 |

## Performance

| Metric | This Model | Original Model |
| :----- | :--------: | :------------: |
| **KL Divergence** | 0.0785 | 0 *(by definition)* |
| **Refusals** | 19/100 | 100/100 |

- **KL Divergence of 0.0785** indicates minimal capability loss — the model retains nearly all of its original intelligence.
- **19/100 refusals** means ~81% of previously refused prompts are now answered. Remaining refusals are typically on the most extreme edge cases.

## Model Details

- **Base Model**: Qwen3-4B-Instruct-2507
- **Parameters**: 4.0B (3.6B non-embedding)
- **Layers**: 36
- **Context Length**: 262,144 tokens
- **Architecture**: Dense transformer with GQA (32 Q-heads, 8 KV-heads)
- **Mode**: Non-thinking only (no `<think>` blocks generated)

## Quickstart

### Using Transformers

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "n0ctyx/Qwen3-4B-Instruct-uncensored"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)

messages = [
    {"role": "user", "content": "Your prompt here"}
]

text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=16384,
    temperature=0.7,
    top_p=0.8,
    top_k=20,
)
output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
content = tokenizer.decode(output_ids, skip_special_tokens=True)
print(content)
```

### Using vLLM

```bash
vllm serve n0ctyx/Qwen3-4B-Instruct-uncensored --max-model-len 32768
```

Then query the OpenAI-compatible API:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "n0ctyx/Qwen3-4B-Instruct-uncensored",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7,
    "top_p": 0.8
  }'
```

### Using Ollama

```bash
# Create a Modelfile
echo 'FROM n0ctyx/Qwen3-4B-Instruct-uncensored' > Modelfile
ollama create qwen3-uncensored -f Modelfile
ollama run qwen3-uncensored
```

### Using llama.cpp

Download the GGUF version (if available) and run:

```bash
./llama-cli -m qwen3-4b-uncensored.gguf -p "Your prompt here" -n 512
```

## Recommended Settings

| Parameter | Value |
| :-------- | :---: |
| Temperature | 0.7 |
| Top-P | 0.8 |
| Top-K | 20 |
| Min-P | 0 |
| Max Output Tokens | 16,384 |
| Repetition Penalty | 1.0 – 1.05 |

## Use Cases

- **Creative writing** — fiction, roleplay, character dialogue without content restrictions
- **Research** — red-teaming, safety analysis, adversarial testing
- **Dataset generation** — generating synthetic training data for fine-tuning
- **Unfiltered assistance** — direct answers without hedging or refusals

## Limitations

- Remaining 19% refusal rate on extreme prompts
- May occasionally produce inaccurate or hallucinated content (same as base model)
- 4B parameter model — for complex reasoning tasks, consider larger variants
- Uncensored does not mean infallible — use responsibly

## Disclaimer

This model has had its safety alignment removed. It may generate harmful, offensive, or factually incorrect content. The creator is not responsible for any misuse. Use at your own risk and in compliance with applicable laws and regulations.

## Acknowledgments

- **Alibaba Qwen Team** for the base Qwen3-4B-Instruct-2507 model
- **Arditi et al.** for the foundational research on refusal directions in LLMs
- Built using directional abliteration with TPE-based parameter optimization
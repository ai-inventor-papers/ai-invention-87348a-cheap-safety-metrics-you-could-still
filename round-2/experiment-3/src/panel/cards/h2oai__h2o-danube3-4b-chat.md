---
language:
- en
library_name: transformers
license: apache-2.0
tags:
- gpt
- llm
- large language model
- h2o-llmstudio
thumbnail: >-
  https://h2o.ai/etc.clientlibs/h2o/clientlibs/clientlib-site/resources/images/favicon.ico
pipeline_tag: text-generation
---



<div style="width: 90%; max-width: 600px; margin: 0 auto; overflow: hidden; background-color: white">
    <img src="https://cdn-uploads.huggingface.co/production/uploads/636d18755aaed143cd6698ef/LAzQu_f5WOX7vqKl4yDsY.png" 
         alt="Slightly cropped image" 
         style="width: 102%; height: 102%; object-fit: cover; object-position: center; margin: -5% -5% -5% -5%;">
</div>

## Summary


h2o-danube3-4b-chat is a chat fine-tuned model by H2O.ai with 4 billion parameters. We release two versions of this model:

| Model Name                                                                         |  Description    |
|:-----------------------------------------------------------------------------------|:----------------|
|  [h2oai/h2o-danube3-4b-base](https://huggingface.co/h2oai/h2o-danube3-4b-base) | Base model      |
|  [h2oai/h2o-danube3-4b-chat](https://huggingface.co/h2oai/h2o-danube3-4b-chat) | Chat model |

This model was trained using [H2O LLM Studio](https://github.com/h2oai/h2o-llmstudio).

Can be run natively and fully offline on phones - try it yourself with [H2O AI Personal GPT](https://h2o.ai/platform/danube/personal-gpt/).

## Model Architecture

We adjust the Llama 2 architecture for a total of around 4b parameters. For details, please refer to our [Technical Report](https://arxiv.org/abs/2407.09276). We use the Mistral tokenizer with a vocabulary size of 32,000 and train our model up to a context length of 8,192.

The details of the model architecture are:

| Hyperparameter  |  Value |
|:----------------|:-------|
|    n_layers     |     24 |
|     n_heads     |     32 |
|  n_query_groups |      8 |
|     n_embd      |   3840 |
|   vocab size    |  32000 |
| sequence length |   8192 |

## Usage

To use the model with the `transformers` library on a machine with GPUs, first make sure you have the `transformers` library installed.

```bash
pip install transformers>=4.42.3
```

```python
import torch
from transformers import pipeline

pipe = pipeline(
    "text-generation",
    model="h2oai/h2o-danube3-4b-chat",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# We use the HF Tokenizer chat template to format each message
# https://huggingface.co/docs/transformers/main/en/chat_templating
messages = [
    {"role": "user", "content": "Why is drinking water so healthy?"},
]
prompt = pipe.tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)
res = pipe(
    prompt,
    return_full_text=False,
    max_new_tokens=256,
)
print(res[0]["generated_text"])
```

This will apply and run the correct prompt format out of the box:

```
<|prompt|>Why is drinking water so healthy?</s><|answer|>
```

Alternatively, one can also run it via:

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "h2oai/h2o-danube3-4b-chat"

tokenizer = AutoTokenizer.from_pretrained(
    model_name,
)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

messages = [
    {"role": "user", "content": "Why is drinking water so healthy?"},
]
prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)
inputs = tokenizer(
    prompt, return_tensors="pt", add_special_tokens=False
).to("cuda")

# generate configuration can be modified to your needs
tokens = model.generate(
    input_ids=inputs["input_ids"],
    attention_mask=inputs["attention_mask"],
    min_new_tokens=2,
    max_new_tokens=256,
)[0]

tokens = tokens[inputs["input_ids"].shape[1]:]
answer = tokenizer.decode(tokens, skip_special_tokens=True)
print(answer)
```

## Quantization and sharding

You can load the models using quantization by specifying ```load_in_8bit=True``` or ```load_in_4bit=True```. Also, sharding on multiple GPUs is possible by setting ```device_map=auto```.

## Model Architecture

```
LlamaForCausalLM(
  (model): LlamaModel(
    (embed_tokens): Embedding(32000, 3840, padding_idx=0)
    (layers): ModuleList(
      (0-23): 24 x LlamaDecoderLayer(
        (self_attn): LlamaSdpaAttention(
          (q_proj): Linear(in_features=3840, out_features=3840, bias=False)
          (k_proj): Linear(in_features=3840, out_features=960, bias=False)
          (v_proj): Linear(in_features=3840, out_features=960, bias=False)
          (o_proj): Linear(in_features=3840, out_features=3840, bias=False)
          (rotary_emb): LlamaRotaryEmbedding()
        )
        (mlp): LlamaMLP(
          (gate_proj): Linear(in_features=3840, out_features=10240, bias=False)
          (up_proj): Linear(in_features=3840, out_features=10240, bias=False)
          (down_proj): Linear(in_features=10240, out_features=3840, bias=False)
          (act_fn): SiLU()
        )
        (input_layernorm): LlamaRMSNorm()
        (post_attention_layernorm): LlamaRMSNorm()
      )
    )
    (norm): LlamaRMSNorm()
  )
  (lm_head): Linear(in_features=3840, out_features=32000, bias=False)
)
```

## Benchmarks

### 🤗 Open LLM Leaderboard v1

| Benchmark     |   acc_n  |
|:--------------|:--------:|
| Average       |   61.42  |
| ARC-challenge |   58.96  |
| Hellaswag     |   80.36  |
| MMLU          |   54.74  |
| TruthfulQA    |   47.79  |
| Winogrande    |   76.48 |
| GSM8K         |   50.18  |

### MT-Bench

```
First Turn: 7.28
Second Turn: 5.69
Average: 6.49
```

## Disclaimer

Please read this disclaimer carefully before using the large language model provided in this repository. Your use of the model signifies your agreement to the following terms and conditions.

- Biases and Offensiveness: The large language model is trained on a diverse range of internet text data, which may contain biased, racist, offensive, or otherwise inappropriate content. By using this model, you acknowledge and accept that the generated content may sometimes exhibit biases or produce content that is offensive or inappropriate. The developers of this repository do not endorse, support, or promote any such content or viewpoints.
- Limitations: The large language model is an AI-based tool and not a human. It may produce incorrect, nonsensical, or irrelevant responses. It is the user's responsibility to critically evaluate the generated content and use it at their discretion.
- Use at Your Own Risk: Users of this large language model must assume full responsibility for any consequences that may arise from their use of the tool. The developers and contributors of this repository shall not be held liable for any damages, losses, or harm resulting from the use or misuse of the provided model.
- Ethical Considerations: Users are encouraged to use the large language model responsibly and ethically. By using this model, you agree not to use it for purposes that promote hate speech, discrimination, harassment, or any form of illegal or harmful activities.
- Reporting Issues: If you encounter any biased, offensive, or otherwise inappropriate content generated by the large language model, please report it to the repository maintainers through the provided channels. Your feedback will help improve the model and mitigate potential issues.
- Changes to this Disclaimer: The developers of this repository reserve the right to modify or update this disclaimer at any time without prior notice. It is the user's responsibility to periodically review the disclaimer to stay informed about any changes.

By using the large language model provided in this repository, you agree to accept and comply with the terms and conditions outlined in this disclaimer. If you do not agree with any part of this disclaimer, you should refrain from using the model and any content generated by it.
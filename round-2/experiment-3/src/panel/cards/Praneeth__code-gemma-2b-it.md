---
language:
- en
license: other
library_name: transformers
tags:
- peft
- unsloth
- lora
- trl
- sft
datasets:
- HuggingFaceH4/CodeAlpaca_20K
license_name: gemma-terms-of-use
license_link: https://ai.google.dev/gemma/terms

inference: false
---

# Code-Gemma-2B

### Description
Code-Gemma was finetuned (1k steps) on the CodeAlpaca-20k dataset using the unsloth library to enhance the Gemma-2B-it model.

### Usage

Below we share some code snippets on how to get quickly started with running the model.

```python
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
if major_version >= 8:
    # Use this for new GPUs like Ampere, Hopper GPUs (RTX 30xx, RTX 40xx, A100, H100, L40)
    !pip install --no-deps packaging ninja einops flash-attn xformers trl peft accelerate bitsandbytes
else:
    # Use this for older GPUs (V100, Tesla T4, RTX 20xx)
    !pip install --no-deps xformers trl peft accelerate bitsandbytes
pass
```

#### Running the model on a GPU using different precisions

* _Using `torch.float16`_

```python

from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("Praneeth/code-gemma-2b-it")
model = AutoModelForCausalLM.from_pretrained("Praneeth/code-gemma-2b-it", device_map="auto", torch_dtype=torch.float16)

input_text = "Write me a poem about Machine Learning."
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

outputs = model.generate(**input_ids, max_new_tokens=256,)
print(tokenizer.decode(outputs[0]))
```


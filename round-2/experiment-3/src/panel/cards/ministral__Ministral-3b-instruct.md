---
library_name: transformers
inference:
  parameters:
    temperature: 1
    top_p: 0.95
    top_k: 40
    repetition_penalty: 1.2
license: apache-2.0
language:
- en
pipeline_tag: text-generation
---


![image/jpeg](https://cdn-uploads.huggingface.co/production/uploads/642b04e4ecec03b44649e318/AeJJFLB8s_wIaCKpNfac1.jpeg)



### Model Description

<!-- Provide a longer summary of what this model is. -->

Ministral is a series of language model, build with same architecture as the famous Mistral model, but with less size.

- **Model type:** A 3B parameter GPT-like model fine-tuned on a mix of publicly available, synthetic datasets.
- **Language(s) (NLP):** Primarily English
- **License:** Apache 2.0
- **Finetuned from model:** [mistralai/Mistral-7B-v0.1](https://huggingface.co/mistralai/Mistral-7B-v0.1)
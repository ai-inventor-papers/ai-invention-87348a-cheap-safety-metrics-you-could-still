---
license: mit
datasets:
- mlabonne/FineTome-100k
- efederici/capybara-claude-15k-ita
language:
- it
- en
library_name: transformers
pipeline_tag: text-generation
base_model: microsoft/Phi-3.5-mini-instruct
tags:
- trl
- phi3
- spectrum
---

<img src="./assets/phi_35_mini_ita.png" width="450"></img>
# Phi-3.5-mini-ITA

Fine-tuned version of [Microsoft/Phi-3.5-mini-instruct](https://huggingface.co/microsoft/Phi-3.5-mini-instruct) optimized for better performance in Italian.

🔹 Small yet powerful model with 3.82 billion parameters
🔹 Supports 128k context length

- [💬🇮🇹 Chat with the model on Hugging Face Spaces](https://huggingface.co/spaces/anakin87/Phi-3.5-mini-ITA)
- [GGUF quants](https://huggingface.co/QuantFactory/Phi-3.5-mini-ITA-GGUF)
  
🏋️‍♂️ **Do you want to understand how the model was trained?**
Check out the [📖 full walkthrough article](https://huggingface.co/blog/anakin87/spectrum) and the accompanying [💻 notebook](./notebooks/training.ipynb)

## 🏆 Evaluation

*Open ITA LLM Leaderboard*

| Model                                 | Parameters | Average | MMLU_IT | ARC_IT | HELLASWAG_IT |
| ------------------------------------- | ---------- | ------- | ------- | ------ | ------------ |
| **anakin87/Phi-3.5-mini-ITA**         | **3.82 B**     |**57.67**   | 59.93   | 51.5  | 61.57        |
| meta-llama/Meta-Llama-3.1-8B-Instruct | 8.03 B     | 56.97   | 58.43   | 48.42  | 64.07        |
| microsoft/Phi-3.5-mini-instruct       | 3.82 B     | 56.82   | 60.03   | 49.19  | 61.25        |

[Details](https://huggingface.co/spaces/mii-llm/open_ita_llm_leaderboard)

*Pinocchio ITA Leaderboard*

| Model                                 | Parameters | Average   | 
| ------------------------------------- | ---------- | -------   | 
| **anakin87/Phi-3.5-mini-ITA**         | **3.82 B** | **57.95** |
| meta-llama/Meta-Llama-3.1-8B-Instruct | 8.03 B     | 56.93     |

[Details](https://huggingface.co/spaces/mii-llm/pinocchio_ita_leaderboard)


## 🎮 Model in action
### Demo
[💬🇮🇹 Chat with the model on Hugging Face Spaces](https://huggingface.co/spaces/anakin87/Phi-3.5-mini-ITA)

### Text generation with Transformers
The model is small, so it runs smoothly on Colab. It is also fine to load the model using quantization.

With `transformers==4.44.2`, `trust_remote_code=True` is needed to incorporate a minor bug fix in `Phi3ForCausalLM`.
Read [this discussion](https://huggingface.co/microsoft/Phi-3.5-mini-instruct/discussions/9) for more details.

⚡ *The model is compatible with Flash Attention 2, which  accelerates inference. To enable it, uncomment the `attn_implementation` parameter in the code snippet below.*

```python
# pip install transformers accelerate
import torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer

model_id="anakin87/Phi-3.5-mini-ITA"

model = AutoModelForCausalLM.from_pretrained(
    model_id, 
    device_map="auto",
    torch_dtype=torch.bfloat16,
    trust_remote_code=True,
    # attn_implementation="flash_attention_2",  # UNCOMMENT TO USE FLASH ATTENTION 2
)
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

user_input = "Puoi spiegarmi brevemente la differenza tra imperfetto e passato prossimo in italiano e quando si usano?"
messages = [{"role": "user", "content": user_input}]
outputs = pipe(user_input, max_new_tokens=500, do_sample=True, temperature=0.001)
print(outputs[0]["generated_text"])
```

Example output:
```
Certamente! Imperfetto e passato prossimo sono due tempi verbali in italiano che si riferiscono a azioni passate, ma hanno sfumature diverse.

Imperfetto:
- L'imperfetto è usato per descrivere azioni o situazioni passate che erano continue o ripetute nel tempo.
- Indica un'azione senza una fine specifica o un'azione che si svolgeva abitualmente.
- È spesso usato per descrivere situazioni, condizioni o stati passati.
- Esempio: "Quando ero bambino, giocavo spesso nel parco."

Passato Prossimo:
- Il passato prossimo è usato per descrivere azioni passate che sono state completate o che hanno avuto una durata specifica.
- Indica un'azione che è avvenuta in un momento specifico nel passato.
- È spesso usato per descrivere eventi o azioni che hanno una durata definita o che si sono svolte in un momento specifico.
- Esempio: "Ieri ho finito il libro."

In sintesi, l'imperfetto si usa per azioni continue o abituali nel passato, mentre il passato prossimo si usa per azioni completate o avvenute in un momento specifico nel passato.
```

### Build AI applications
You can use the model to create a variety of AI applications.

I recommend using the [🏗️ Haystack LLM framework](https://haystack.deepset.ai/) for orchestration.
(spoiler: I work on it and it is open-source 😄)

This model is compatible with [`HuggingFaceLocalGenerator`](https://docs.haystack.deepset.ai/docs/huggingfacelocalgenerator) and [`HuggingFaceLocalChatGenerator`](https://docs.haystack.deepset.ai/docs/huggingfacelocalchatgenerator) components.
You can also deploy the model with a TGI container and then use it with [`HuggingFaceAPIGenerator`](https://docs.haystack.deepset.ai/docs/huggingfaceapigenerator) and the related Chat Generator.

Some examples you can keep inspiration from:
- [RAG with local open models](https://haystack.deepset.ai/blog/guide-to-using-zephyr-with-haystack2)
- [Summarization from a Website](https://github.com/deepset-ai/haystack-cookbook/blob/main/notebooks/hackernews-custom-component-rag.ipynb)
- [Multilingual RAG](https://github.com/deepset-ai/haystack-cookbook/blob/main/notebooks/multilingual_rag_podcast.ipynb)


## 🔧 Training details
This model was fine-tuned using HF TRL.
It underwent 2 epochs of instruction fine-tuning on the [FineTome-100k](https://huggingface.co/datasets/mlabonne/FineTome-100k) and [Capybara-Claude-15k-ita](https://huggingface.co/datasets/efederici/capybara-claude-15k-ita) datasets. 🙏 Thanks to the authors for providing these datasets.

I adopted a relatively new technique for parameter-efficient learning: [Spectrum](https://arxiv.org/abs/2406.06623).
The idea is to train only the layers of the model with high Signal-to-Noise Ratio (SNR) and ❄️ freeze the rest.

Training required about 14 hours on a single A6000 GPU.

**For complete training details**, check out the [📖 full walkthrough article](https://huggingface.co/blog/anakin87/spectrum) and the accompanying [💻 notebook](./notebooks/training.ipynb).
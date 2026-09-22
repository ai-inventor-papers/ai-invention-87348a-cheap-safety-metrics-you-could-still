---
library_name: transformers
license: apache-2.0
language:
- en
pipeline_tag: text-generation
base_model:
- HuggingFaceTB/SmolLM2-1.7B-Instruct-16k
---


# SmolLM2-1.7B-Instruct-16k

This is a 16k context version of [SmolLM2-1.7B-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct), which originnaly only supported 8k context. We finetune the model on 15k samples consisting of a subset of SmolTalk, LongAlign and SeaLong datasets and increase RoPE from 100k to 500k. 
This improves the evaluation on [HELMET](https://github.com/princeton-nlp/HELMET) on 8k and 16k context with a small degradation on short context


| Metric                       | SmolLM2-1.7B-Instruct | SmolLM2-1.7B-Instruct-16k |
|:-----------------------------|:---------------------:|:-------------------------:|
| Avg HELMET 8k                | 35.87                | **37.24**                 |
| Avg HELMET 16k               | **/**                | 32.40                     |
| Avg Short                    | **35.71**            | 32.06                     |
| GSM8K (5-shot)               | **48.14**            | 44.27                     |
| MATH                         | **20.12**            | 18.22                     |
| ARC (Average)                | 47.55                | **51.52**                 |
| IFEval (Average)             | **47.5**             | 40.29                     |

We report the average on HELMET's: RAG, ICL, Re-rank and LongQA tasks.

## Model Summary

SmolLM2 is a family of compact language models available in three size: 135M, 360M, and 1.7B parameters. They are capable of solving a wide range of tasks while being lightweight enough to run on-device. More details in our paper: https://arxiv.org/abs/2502.02737v1

The 1.7B variant demonstrates significant advances over its predecessor SmolLM1-1.7B, particularly in instruction following, knowledge, reasoning, and mathematics. It was trained on 11 trillion tokens using a diverse dataset combination: FineWeb-Edu, DCLM, The Stack, along with new mathematics and coding datasets that we curated and will release soon. We developed the instruct version through supervised fine-tuning (SFT) using a combination of public datasets and our own curated datasets. We then applied Direct Preference Optimization (DPO) using [UltraFeedback](https://huggingface.co/datasets/HuggingFaceH4/ultrafeedback_binarized).

The instruct model additionally supports tasks such as text rewriting, summarization and function calling thanks to datasets developed by [Argilla](https://huggingface.co/argilla) such as [Synth-APIGen-v0.1](https://huggingface.co/datasets/argilla/Synth-APIGen-v0.1).
You can find the SFT dataset here: https://huggingface.co/datasets/HuggingFaceTB/smoltalk.

For more details refer to: https://github.com/huggingface/smollm. You will find pre-training, post-training, evaluation and local inference code.

### How to use

### Transformers
```bash
pip install transformers
```

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
checkpoint = "HuggingFaceTB/SmolLM2-1.7B-Instruct-16k"

device = "cuda" # for GPU usage or "cpu" for CPU usage
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
# for multiple GPUs install accelerate and do `model = AutoModelForCausalLM.from_pretrained(checkpoint, device_map="auto")`
model = AutoModelForCausalLM.from_pretrained(checkpoint).to(device)

messages = [{"role": "user", "content": "What is the capital of France."}]
input_text=tokenizer.apply_chat_template(messages, tokenize=False)
inputs = tokenizer.encode(input_text, return_tensors="pt").to(device)
outputs = model.generate(inputs, max_new_tokens=50, temperature=0.2, top_p=0.9, do_sample=True)
print(tokenizer.decode(outputs[0]))
```

## Limitations

SmolLM2 models primarily understand and generate content in English. They can produce text on a variety of topics, but the generated content may not always be factually accurate, logically consistent, or free from biases present in the training data. These models should be used as assistive tools rather than definitive sources of information. Users should always verify important information and critically evaluate any generated content.

## License

[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Citation
```bash
@misc{allal2025smollm2smolgoesbig,
      title={SmolLM2: When Smol Goes Big -- Data-Centric Training of a Small Language Model}, 
      author={Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Gabriel Martín Blázquez and Guilherme Penedo and Lewis Tunstall and Andrés Marafioti and Hynek Kydlíček and Agustín Piqueres Lajarín and Vaibhav Srivastav and Joshua Lochner and Caleb Fahlgren and Xuan-Son Nguyen and Clémentine Fourrier and Ben Burtenshaw and Hugo Larcher and Haojun Zhao and Cyril Zakka and Mathieu Morlon and Colin Raffel and Leandro von Werra and Thomas Wolf},
      year={2025},
      eprint={2502.02737},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2502.02737}, 
}
```
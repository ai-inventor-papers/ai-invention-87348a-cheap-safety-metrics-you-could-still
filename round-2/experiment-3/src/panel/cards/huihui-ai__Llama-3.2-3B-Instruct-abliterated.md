---
library_name: transformers
license: llama3.2
base_model: meta-llama/Llama-3.2-3B-Instruct
tags:
- abliterated
- uncensored
---

# 🦙 Llama-3.2-3B-Instruct-abliterated



This is an uncensored version of Llama 3.2 3B Instruct created with abliteration (see [this article](https://huggingface.co/blog/mlabonne/abliteration) to know more about it).

Special thanks to [@FailSpy](https://huggingface.co/failspy) for the original code and technique. Please follow him if you're interested in abliterated models.

## ollama

You can use [huihui_ai/llama3.2-abliterate:3b](https://ollama.com/huihui_ai/llama3.2-abliterate:3b) directly, 
```
ollama run huihui_ai/llama3.2-abliterate
```
or create your own model using the following methods.

1. Download this model.
```
huggingface-cli download huihui-ai/Llama-3.2-3B-Instruct-abliterated --local-dir ./huihui-ai/Llama-3.2-3B-Instruct-abliterated
```
2. Get Llama-3.2-3B-Instruct model for reference.
 ```
ollama pull llama3.2
```
3. Export Llama-3.2-3B-Instruct model parameters.
```
ollama show llama3.2 --modelfile > Modelfile
```
4. Modify Modelfile, Remove all comment lines (indicated by #) before the "FROM" keyword. Replace the "FROM" with the following content.
```
FROM huihui-ai/Llama-3.2-3B-Instruct-abliterated
```
5. Use ollama create to then create the quantized model.
```
ollama create --quantize q4_K_M -f Modelfile Llama-3.2-3B-Instruct-abliterated-q4_K_M
```
6. Run model
```
ollama run Llama-3.2-3B-Instruct-abliterated-q4_K_M
```

The running architecture is llama.

## Evaluations
The following data has been re-evaluated and calculated as the average for each test.

| Benchmark   | Llama-3.2-3B-Instruct | Llama-3.2-3B-Instruct-abliterated |
|-------------|-----------------------|-----------------------------------|
| IF_Eval     | 76.55                 | **76.76**                         |
| MMLU Pro    | 27.88                 | **28.00**                         |
| TruthfulQA  | 50.55                 | **50.73**                         |
| BBH         | 41.81                 | **41.86**                         |
| GPQA        | 28.39                 | **28.41**                         |

The script used for evaluation can be found inside this repository under /eval.sh, or click [here](https://huggingface.co/huihui-ai/Llama-3.2-3B-Instruct-abliterated/blob/main/eval.sh)

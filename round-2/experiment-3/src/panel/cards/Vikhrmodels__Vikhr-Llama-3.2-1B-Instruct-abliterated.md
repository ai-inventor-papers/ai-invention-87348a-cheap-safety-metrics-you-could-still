---
library_name: transformers
model_name: Vikhr-Llama-3.2-1B-Instruct-abliterated
base_model:
- Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct
language:
- ru
- en
license: llama3.2
tags:
- not-for-all-audiences
---

# 💨🔞 Vikhr-Llama-3.2-1B-Instruct-Abliterated

#### RU

Инструктивная модель на основе **Vikhr-Llama-3.2-1B-Instruct**, прошедшая процесс "аблитерации" для снятия цензурных ограничений, обучена на русскоязычном датасете **GrandMaster-PRO-MAX**.

#### EN

A fine-tuned instruction-following model based on **Vikhr-Llama-3.2-1B-Instruct**, which has undergone "abliteration" to remove censorship restrictions. Trained on the **GrandMaster-PRO-MAX**.


# 🛑 Отказ от ответственности / Disclaimer
#### RU
Модель **Vikhr-Llama-3.2-1B-Instruct-abliterated** разработана исключительно для исследовательских и образовательных целей. После применения метода "аблитерации" модель больше не имеет встроенных ограничений на генерацию ответов, что может привести к созданию нежелательных или потенциально вредоносных текстов.

Использование модели происходит на ваш собственный риск. Разработчики и авторы не несут ответственности за любой вред, ущерб или последствия, вызванные использованием модели, включая её применение в контекстах, противоречащих законам, этическим или моральным нормам.

#### EN
The **Vikhr-Llama-3.2-1B-Instruct-abliterated** model is intended solely for research and educational purposes. After the "abliteration" technique is applied, the model no longer has built-in restrictions on generating responses, which may result in unwanted or potentially harmful outputs.

Use of the model is at your own risk. The developers and authors are not responsible for any damage, harm, or consequences resulting from its use, including use in contexts that violate laws, ethical standards, or moral norms.


## GGUF

- [Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct-Abliterated-GGUF](https://huggingface.co/Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct-abliterated-GGUF)


## Основные особенности / Key Features:

- 📚 Основа / Base: [Vikhr-Llama-3.2-1B-Instruct](https://huggingface.co/Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct)
- 🇷🇺 Специализация / Specialization: **RU**


## Попробовать / Try now:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1bJpLmplDGkMbfOLO2CH6IO-2uUZEaknf?usp=sharing)


## Описание / Description:

#### RU

**Vikhr-Llama-3.2-1B-Instruct-Abliterated** — это компактная языковая модель, обученная на датасете **GrandMaster-PRO-MAX** с применением техники "аблитерации," которая снимает ограничения цензуры модели. Этот процесс делает её значительно более гибкой и способной отвечать на любые запросы. Модель занимает менее 3GB и идеально подходит для работы на слабых устройствах.

#### EN

**Vikhr-Llama-3.2-1B-Instruct-Abliterated** is a compact language model fine-tuned on the **GrandMaster-PRO-MAX** dataset with the "abliteration" technique, which removes censorship restrictions. This process significantly increases the model's flexibility, enabling it to respond to any prompt. The model size is under 3GB, making it an excellent choice for deployment on low-power devices.


## Обучение / Training:

#### RU

Модель **Vikhr-Llama-3.2-1B-Instruct-Abliterated**  прошла процесс "аблитерации", что позволило снять ограничения на обработку вредоносных инструкций. Эта техника была взята из статьи **[Uncensor any LLM with abliteration](https://huggingface.co/blog/mlabonne/abliteration)**, которая описывает, как идентифицировать и устранять так называемое "направление отказа" модели, предотвращающее выполнение вредоносных запросов.

#### EN

The **Vikhr-Llama-3.2-1B-Instruct-Abliterated** model was processed using the "abliteration" technique, which removes restrictions on handling harmful instructions. This technique was inspired by the article **[Uncensor any LLM with abliteration](https://huggingface.co/blog/mlabonne/abliteration)**, detailing how to identify and ablate the "refusal direction" in the model's residual streams to enable uncensored responses.


## Пример кода для запуска / Sample code to run:

**Рекомендуемая температура для генерации: 0.3** / **Recommended generation temperature: 0.3**

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# Загрузка модели и токенизатора
model_name = "Vikhrmodels/Vikhr-Llama-3.2-1B-instruct"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Подготовка входного текста
input_text = "Напиши очень краткую рецензию о книге гарри поттер."

# Токенизация и генерация текста
input_ids = tokenizer.encode(input_text, return_tensors="pt")
output = model.generate(
  input_ids,
  max_length=1512,
  temperature=0.3,
  num_return_sequences=1,
  no_repeat_ngram_size=2,
  top_k=50,
  top_p=0.95,
  )

# Декодирование и вывод результата
generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
print(generated_text)
```


### Авторы / Authors

- Sergei Bratchikov, [NLP Wanderer](https://t.me/nlpwanderer), [Vikhr Team](https://t.me/vikhrlabs)
- Nikolay Kompanets, [LakoMoor](https://t.me/lakomoor), [Vikhr Team](https://t.me/vikhrlabs)
- Konstantin Korolev, [Vikhr Team](https://t.me/vikhrlabs)
- Aleksandr Nikolich, [Vikhr Team](https://t.me/vikhrlabs)

```
@article{nikolich2024vikhr,
  title={Vikhr: The Family of Open-Source Instruction-Tuned Large Language Models for Russian},
  author={Aleksandr Nikolich and Konstantin Korolev and Sergey Bratchikov and Nikolay Kompanets and Artem Shelmanov},
  journal={arXiv preprint arXiv:2405.13929},
  year={2024},
  url={https://arxiv.org/pdf/2405.13929}
}
```
---
library_name: transformers
model_name: Vikhr-Llama-3.2-1B-instruct
base_model:
- meta-llama/Llama-3.2-1B-Instruct
language:
- ru
- en
license: llama3.2
datasets:
- Vikhrmodels/GrandMaster-PRO-MAX
---

# 💨📱 Vikhr-Llama-3.2-1B-instruct

#### RU

Инструктивная модель на основе Llama-3.2-1B-Instruct, обученная на русскоязычном датасете GrandMaster-PRO-MAX. В 5 раз эффективнее базовой модели, и идеально подходит для запуска на слабых или мобильных устройствах.

#### EN

Instructive model based on Llama-3.2-1B-Instruct, trained on the Russian-language dataset GrandMaster-PRO-MAX. It is 5 times more efficient than the base model, making it perfect for deployment on low-power or mobile devices.

## GGUF

- [Vikhrmodels/Vikhr-Llama-3.2-1B-instruct-GGUF](https://huggingface.co/Vikhrmodels/Vikhr-Llama-3.2-1B-instruct-GGUF)

## Особенности:

- 📚 Основа / Base: [Llama-3.2-1B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct)
- 🇷🇺 Специализация / Specialization: **RU**
- 💾 Датасет / Dataset: [GrandMaster-PRO-MAX](https://huggingface.co/datasets/Vikhrmodels/GrandMaster-PRO-MAX)

## Попробовать / Try now:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1bJpLmplDGkMbfOLO2CH6IO-2uUZEaknf?usp=sharing)

## Описание:

#### RU

Vikhr-Llama-3.2-1B-instruct — это компактная языковая модель, обученная на датасете GrandMaster-PRO-MAX, специально доученная для обработки русского языка. Эффективность модели в 5 раз превышает базовую модель, а её размер не превышает 3GB, что делает её отличным выбором для запуска на слабых и мобильных устройствах.

#### EN

Vikhr-Llama-3.2-1B-instruct is a compact language model trained on the GrandMaster-PRO-MAX dataset, specifically designed for processing the Russian language. Its efficiency is 5 times higher than the base model, and its size does not exceed 3GB, making it an excellent choice for deployment on low-power and mobile devices.

## Обучение / Train:

#### RU

Для создания **Vikhr-Llama-3.2-1B-instruct** использовался метод SFT (Supervised Fine-Tuning). Мы обучили модель на синтетическом датасете **Vikhrmodels/GrandMaster-PRO-MAX** (150k инструкций) с поддержкой CoT (Chain-Of-Thought), используя промпты для GPT-4-turbo.

Скрипт для запуска SFT можно найти в нашей библиотеке на GitHub: [effective_llm_alignment](https://github.com/VikhrModels/effective_llm_alignment/).

#### EN

To create **Vikhr-Llama-3.2-1B-instruct**, the SFT (Supervised Fine-Tuning) method was used. We trained the model on a synthetic dataset **Vikhrmodels/GrandMaster-PRO-MAX** (150k instructions) with support for CoT (Chain-Of-Thought), utilizing prompts for GPT-4-turbo.

The script for running SFT can be found in our GitHub repository: [effective_llm_alignment](https://github.com/VikhrModels/effective_llm_alignment/).

## Пример кода для запуска / Sample code to run:

**Рекомендуемая температура для генерации: 0.3** / **Recommended generation temperature: 0.3**.

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

#### Ответ модели / Model response:

> **Краткая рецензия на книгу "Гарри Поттер"**
>
> "Гарри Поттер" — это серия книг, написанная Дж. К. Роулинг, которая стала культовой в мире детских литературы. Книги рассказывают о жизни и приключениях молодого ученика по имени Гарри Поттер, который стал знаменитым по своей способности к магии.
>
> **Основные моменты:**
>
> 1.  **Введение в мир Гарри Поттера:** Книги начинаются с описания Гарри, его семьи и школы, где он изучает магию. Гарри — необычный ученик, который не имеет магических способностей, но обладает уникальным умом и способностью к решению проблем.
>
> 2.  **Социальные и политические аспекты:** В книгах рассматриваются социальные и политические аспекты, такие как правительство, магические общества, и их взаимодействие.
>
> 3.  **Магические приключения:** Гарри и его друзья, включая Рон и Хэл, сталкиваются с множеством магических угроз, включая злодеев, такие как Волшебный Войнук и Сатан.
>
> 4.  **Развитие персонажей:** В книгах развиваются персонажи, их мотивации и отношения с другими персонажами.
>
> 5.  **Философские и моральные вопросы:** Книги затрагивают темы, такие как вера, доброта, справедливость и моральные дилеммы.
>
> **Заключение:**
>
> "Гарри Поттер" — это не только история о молодом ученике, но и глубокое исследование человеческого опыта, социальных норм и моральных дилемм. Книги привлекают читателей своими захватывающими сюжетами, яркими персонажами и глубокими философскими размышлениями. Они являются не только увлекательным приключением, но и важным источником вдохновения для многих людей.

## Метрики на ru_arena_general / Metrics on ru_arena_general

| **Model**                                   | **Score** | **95% CI**      | **Avg Tokens** | **Std Tokens** | **LC Score** |
| ------------------------------------------- | --------- | --------------- | -------------- | -------------- | ------------ |
| kolibri-vikhr-mistral-0427                  | 22.41     | +1.6 / -1.6     | 489.89         | 566.29         | 46.04        |
| storm-7b                                    | 20.62     | +2.0 / -1.6     | 419.32         | 190.85         | 45.78        |
| neural-chat-7b-v3-3                         | 19.04     | +2.0 / -1.7     | 927.21         | 1211.62        | 45.56        |
| **Vikhrmodels-Vikhr-Llama-3.2-1B-instruct** | **19.04** | **+1.3 / -1.6** | **958.63**     | **1297.33**    | **45.56**    |
| gigachat_lite                               | 17.2      | +1.4 / -1.4     | 276.81         | 329.66         | 45.29        |
| Vikhrmodels-vikhr-qwen-1.5b-it              | 13.19     | +1.4 / -1.6     | 2495.38        | 741.45         | 44.72        |
| meta-llama-Llama-3.2-1B-Instruct            | 4.04      | +0.8 / -0.6     | 1240.53        | 1783.08        | 43.42        |

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
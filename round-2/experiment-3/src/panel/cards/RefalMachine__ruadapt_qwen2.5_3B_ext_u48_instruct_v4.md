---
datasets:
- IlyaGusev/saiga_scored
- IlyaGusev/saiga_preferences
- dichspace/darulm
language:
- ru
pipeline_tag: text-generation
base_model:
- RefalMachine/ruadapt_qwen2.5_3B_ext_u48_full_lr5e4_peft_mlp_32_32_bs256
---

## Описание модели

Инструктивная версия адаптированного на русский язык Qwen2.5-3B (RefalMachine/ruadapt_qwen2.5_3B_ext_u48_full_lr5e4_peft_mlp_32_32_bs256). В модели был заменен токенизатор, затем произведено дообучение (Continued pretraining) на русскоязычном корпусе, после чего была применена техника LEP (Learned Embedding Propagation, paper will be soon).

Благодаря новому токенизатору (расширенный tiktoken cl100k с помощью униграм токенизатора на 48 т. токенов) скорость генерации* русскоязычных текстов возрасла до 60% по сравнению с исходной моделью Qwen-2.5-3B-Instruct.

*Под скоростью генерации подразумевается количество русскоязычных символов/слов в секунду на одинаковых текстовых последовательностях.

## Токенизация


![image/png](https://cdn-uploads.huggingface.co/production/uploads/652cedbdf120598322ae358a/O4eQEhnowETEatDPcmArB.png)


![image/png](https://cdn-uploads.huggingface.co/production/uploads/652cedbdf120598322ae358a/oW0Q6LzD_Py3GdH0kfqu4.png)

## Метрики и оценка качества

Модель была оценена на Ru-Arena-General, MERA, llmtf_open


#### Результаты на Ru-Arena-General

Замеры были произведены с использованием оффициального кода лидерборда (https://github.com/VikhrModels/ru_llm_arena), **но с repetition_penalty=1.1**. 

Приведена лишь часть лидерборда, подробнее смотрите в репозитории бенчмарка (https://huggingface.co/spaces/Vikhrmodels/arenahardlb).

| Model Name                                       | Winrate  | 95% CI             | Average # Tokens |
|--------------------------------------------------|--------|--------------------|------------------|
| gpt-4-1106-preview                               | 90.9   | (	+1.3 / -0.9)        | 541              |
| vikhr-nemo-12b-instruct-r-21-09-24               | 87.3   | (+1.1 / -1.2)        | 627              |
| gpt-4o-mini                                      | 83.9   | (+1.9 / -1.6)        | 448              |
| ruadapt_qwen2.5_7B_ext_u48_instruct          | 81.9   | (+1.7 / -1.6)             | 556              |
| gemma-2-9b-it                                    | 76.5   | (+1.1 / -1.1)        | 459              |
| Qwen2.5-7B-Instruct                              | 76.0   |    (+1.6 / -1.8)    | 484              |
| gemma-2-9b-it-sppo-iter3                         | 73.6   | (+2.1 / -2.2)        | 509              |
| saiga_llama3_8b_v7                               | 67.6   | (+1.7 / -1.4)             | 503              |
| **ruadapt_qwen2.5_3B_ext_u48_instruct_v4**           | **66.1**   | **(+2.2 / -1.9)**             | **531**              |
| t-lite-instruct-0.1                              | 64.7   | (+2.3 / -2.2)        | 810              |


#### Результаты на MERA

TODO

#### Результаты на llmtf_open

TODO

## How to cite:

Tikhomirov M., Chernyshev D. Facilitating large language model Russian adaptation with Learned Embedding Propagation // 2024 (will be soon)

Tikhomirov M., Chernyshev D. Impact of Tokenization on LLaMa Russian Adaptation //2023 Ivannikov Ispras Open Conference (ISPRAS). – IEEE, 2023. – С. 163-168.

#### Результаты на MERA

![image/png](https://cdn-uploads.huggingface.co/production/uploads/652cedbdf120598322ae358a/iMcy-q9r22YCmObww95sH.png)

#### Результаты на llmtf_open

TODO

## How to cite:

Tikhomirov M., Chernyshev D. Facilitating large language model Russian adaptation with Learned Embedding Propagation // 2024 (Preprint: https://arxiv.org/abs/2412.21140)

Tikhomirov M., Chernyshev D. Impact of Tokenization on LLaMa Russian Adaptation //2023 Ivannikov Ispras Open Conference (ISPRAS). – IEEE, 2023. – С. 163-168.

## Предупреждение

Ответы модели не отражают мнения авторов, а лишь повторяют знания полученные из данных на всех этапах обучения (предобучение, смена токенизатора, обучение на инструкциях, калибровка качества ответов). Модель была получена из сторонней предобученной модели, **контроль за предобучением** которой **не является ответственностью текущих авторов**. При создании данной версии модели не производилось никаких дополнительных действий, направленных на изменение заложенных в LLM "мнений". Используйте с осторожностью.
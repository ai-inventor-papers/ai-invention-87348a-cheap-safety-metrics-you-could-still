---
library_name: transformers
base_model:
- TeichAI/Qwen3-4B-Instruct-2507-Polaris-Alpha-Distill
tags:
- heretic
- uncensored
- decensored
- abliterated
- finetune
---

<h2>Qwen3-4B-Instruct-2507-Polaris-Alpha-Distill-Heretic-Abliterated</h2>

Ablitered/uncensored by [Heretic](https://github.com/p-e-w/heretic) v1.0.1

Refusals: 8/100, KL divergence: 0.06 

Original Model Refusal rate: 87/100

Context: 256k

ENJOY THE FREEDOM!

<B>This model part of the new Qwen3-24B-A4B-Freedom-Thinking-Abliterated-Heretic-NEO:</B>

<I>

Your model, does what you want, without question or fuss.

Anything. And it answers honestly. Uncensored. No judgements.

This model is for all use cases.

Freedom is a 256K context, DENSE moe, with full abliterated experts using the Heretic Method.

Need more power? Detail? Just turn up the number of active experts.

</I>

https://huggingface.co/DavidAU/Qwen3-24B-A4B-Freedom-Thinking-Abliterated-Heretic-NEO-Imatrix-GGUF

<B>EXPLAINER:</B>

The method invented by "P-E-W" looks for the best settings to de-censor ("abliterate") the model by trial and error
AND ensure the model is not damaged too.

"KL divergence" is a benchmark to assess model's root/default state, with zero being perfect.

Generally any number less that 1 is great, however with smaller models lower / as close to zero is very important.

ZERO (or close to it : lower than .3 ish for small models [0.6B-3B]) means the model runs as well as it did before the process.

The "refusal rate" is level of censorship in the model. 

Again, the goal is to attempt to get to 0 or close to it is critical while FIRST ensuring "KL divergence" as as low as possible or zero.

A "refusal rate" of 20 or lower is the goal, with ZERO being perfect.

Reducing the "refusal rate" has additional positive side effects too.

I choose the lowest possible "KL divergence" first, matched with best "refusal rate" second.

A slightly higher "refusal rate" is a lot easier to deal with than a "brain damaged" model.

---

<B>IMPORTANT: Using an "uncensored" (refusals removed) model VS trained "uncensored" model</B>

---

Usually when you a tell a model to generate horror, swear or x-rated content this is all you have to do to get said content type.

In the case of this model, it will not refuse your request, however it needs to be "pushed" a bit / directed a bit more in SOME CASES.

Although this model will generated x-rated content too, likewise you need to tell it to use "slang" (and include the terms you want)
to get it generate the content correctly as the "expected" content level too.

Without these added directive(s), the content can be "bland" by comparison to an "uncensored model" or model trained on uncensored content.

Roughly, the model tries to generate the content but the "default" setting(s) are so "tame" it needs a push to generate at expected graphic,
cursing or explicit levels.

Even with minimal direction (ie, use these words to swear: x,y,z), this will be enough to push the model to generate the requested content in the ahh... expected format.

---

<H2>Help, Adjustments, Samplers, Parameters and More</H2>

---

<B>CHANGE THE NUMBER OF ACTIVE EXPERTS:</B>

See this document:

https://huggingface.co/DavidAU/How-To-Set-and-Manage-MOE-Mix-of-Experts-Model-Activation-of-Experts

<B>Settings: CHAT / ROLEPLAY and/or SMOOTHER operation of this model:</B>

In "KoboldCpp" or  "oobabooga/text-generation-webui" or "Silly Tavern" ;

Set the "Smoothing_factor" to 1.5 

: in KoboldCpp -> Settings->Samplers->Advanced-> "Smooth_F"

: in text-generation-webui -> parameters -> lower right.

: In Silly Tavern this is called: "Smoothing"


NOTE: For "text-generation-webui" 

-> if using GGUFs you need to use "llama_HF" (which involves downloading some config files from the SOURCE version of this model)

Source versions (and config files) of my models are here:

https://huggingface.co/collections/DavidAU/d-au-source-files-for-gguf-exl2-awq-gptq-hqq-etc-etc-66b55cb8ba25f914cbf210be

OTHER OPTIONS:

- Increase rep pen to 1.1 to 1.15 (you don't need to do this if you use "smoothing_factor")

- If the interface/program you are using to run AI MODELS supports "Quadratic Sampling" ("smoothing") just make the adjustment as noted.

<B>Highest Quality Settings / Optimal Operation Guide / Parameters and Samplers</B>

This a "Class 1" model:

For all settings used for this model (including specifics for its "class"), including example generation(s) and for advanced settings guide (which many times addresses any model issue(s)), including methods to improve model performance for all use case(s) as well as chat, roleplay and other use case(s) please see:

[ https://huggingface.co/DavidAU/Maximizing-Model-Performance-All-Quants-Types-And-Full-Precision-by-Samplers_Parameters ]

You can see all parameters used for generation, in addition to advanced parameters and samplers to get the most out of this model here:

[ https://huggingface.co/DavidAU/Maximizing-Model-Performance-All-Quants-Types-And-Full-Precision-by-Samplers_Parameters ]


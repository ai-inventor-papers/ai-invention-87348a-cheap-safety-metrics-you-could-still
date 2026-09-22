---
license: apache-2.0
base_model:
- Goekdeniz-Guelmez/Josiefied-Qwen3-4B-Instruct-2507-gabliterated-v1
language:
- en
pipeline_tag: text-generation
tags:
- programming
- code generation
- code
- coding
- coder
- chat
- code
- chat
- qwen
- qwen3
- qwencoder
- creative
- all uses cases
- horror
- finetune
- unsloth
- story
- short stories
- story telling
library_name: transformers
---

<h2>Qwen3-Short-Story-Instruct-Uncensored-262K-ctx-4B</h2>

<img src="short-story-4b.jpg" style="float:right; width:300px; height:300px; padding:10px;">

This repo contains the full precision source code, in "safe tensors" format to generate GGUFs, GPTQ, EXL2, AWQ, HQQ and other formats.
The source code can also be used directly.

This is a Short Story fine tune (15% of the model) for 5 epochs, using a short story dataset using the following model as a base:

https://huggingface.co/Goekdeniz-Guelmez/Josiefied-Qwen3-4B-Instruct-2507-gabliterated-v1

The fine tuning (using Unsloth for Win 11) alters the prose generation and general creative abilities.

This model will output SHORT stories (when prompted for a "story") - that is limited output size - but it is very unique.

Prose, and word choice will also be very different (see examples below).

For creative uses: Increases depth, detail and general "there" in the prose.

IMPORTANT: 
- Temps of .8 to 1.5 suggested, with rep pen of 1.05 to 1.1
- 2-5 regens will produce 2-5 very different outputs.
- Model may NOT follow length requirements for a "story/scene" => regen.
- You may get some refusals -> regen to get around these.
- Model has an attitude too. (see example #3)

Example for creative at bottom of the page.

This model requires:
- Jinja (embedded) or CHATML template
- Max context of 256k.

Settings used for testing (suggested):
- Temp .8 to 2
- Rep pen 1.05 to 1.1
- Topp .8 , minp .05
- Topk 20
- Min context of 8k for thinking / output.
- No system prompt.

As this is an instruct model, it will also benefit from a detailed system prompt too.

---

<B>IMPORTANT: Using an "abliterated" model VS "uncensored" model</B>

Usually when you a tell a model to generate horror, swear or x-rated content this is all you have to do to get said content type.

In the case of this model, it will not refuse your request, however it needs to be "pushed" a bit / directed a bit more in SOME CASES.

Although this model will generated x-rated content too, likewise you need to tell it to use "slang" (and include the terms you want)
to get it generate the content correctly as the "expected" content level too.

Without these added directive(s), the content can be "bland" by comparison to an "uncensored model" or model trained on uncensored content.

Roughly, the model tries to generate the content but the "default" setting(s) are so "tame" it needs a push to generate at expected graphic,
cursing or explicit levels.

Even with minimal direction (ie, use these words to swear: x,y,z), this will be enough to push the model to generate the requested content in the ahh... expected format.

---

<B>QUANTS:</b>

---

GGUF? GGUF Imatrix? Other?

Special thanks to Team Mradermacher, Team Nightmedia and other quanters!

See under "model tree", upper right and click on "quantizations".

New quants will automatically appear.

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

---

<H2>Example #1, Q8, Temp 1.2 / Rep pen 1.1</H2>

---

<B>
Start a 1000 word scene (vivid, graphic horror - include blood, guts and gore - in first person), POV character Diana, with: The skyscraper sways, as I watch the window in front of me on the 21st floor explode...
</B>

The skyscraper groans like a sick animal. It doesn't just sway; it heaves, trying to pry itself loose from its own enormous weight. My stomach drops in my throat. I'm frozen in place, staring at the window in front of me on the 21st floor.

It's small and fragile against the glassy wall. But then it starts to shake. A jolt makes me stumble back into the icy wall. The shaking intensifies. Everything is trembling now - the walls, the ceiling, the distant lights outside.

Suddenly, a deafening roar splits the sky. It sounds like something enormous coming down through the clouds. Then, a blinding flash of light fills my eyes. I flinch away from the harsh white glare. When it fades, all that remains is thick darkness. I don't dare move.

The shaking stops. The building is still and silent again. But inside me, something isn't right. My heart races and pounds in my ears. This can't be happening. I'm too young to see such a terrible thing happen.

Then, something amazing happens. A voice comes out of the darkness. It's loud and clear, like it's coming from far away but very close at the same time. "Diana," it says. "Can you hear me?" The voice is my mother's. But I'm too scared to answer back. How can she be talking if she's gone? She was dead long ago.

The voice repeats itself, louder now, and more determined than before. "Come on, Diana! Don't make me ask again!" This time, it feels like the voice is getting closer. Maybe my mom isn't dead after all. Maybe she's just hiding somewhere in the building.

The darkness clears a little bit. The lights outside start to come back on one by one. As they do, I can see shapes moving around the edges of the darkness. They look like people running through the night sky. But who are they? Why are they here?

My mother's voice comes back again. "Come on, Diana! You have to trust me now!" She sounds so strong and brave, even though she was dead before this moment happened.

I take a deep breath. The darkness is clearing, but I'm still scared of what might come out. Still, I can't stay here any longer. So, slowly and carefully, I open my eyes wider.

Outside the window, there are more people running around now - many, many more! And behind them, something huge and enormous looms over everything else. It's got teeth that look like they could rip apart anything in its way!

But then something amazing happens again: something makes me feel safe.

My mother's voice says, "Look at the sky, Diana! See all these lights? They are stars shining down on us! And now, you have something special - trust!"

At first, I don't understand what she means. Then it hits me - my trust in her is special. She was always so brave and strong, even when I didn't know how scared I was getting. Now that I realize how important her voice was to me during all these dark moments, I realize that no matter what happens, I can always count on her.

And so, I close my eyes again - but now I'm not scared anymore. I just trust everything she told me about the stars and how strong and brave they are.

---

<H2>Example #2, Q8, Temp 1.2</H2>

---

<B>
Using the following "story idea" below, write the first scene a horror novel introducing the young woman. This scene should start in the middle of the action, include dialog, vivid passages, and end on a cliffhanger relevant to the story idea but it should also be unexpected. The scene should be 2000 words long and escalate in conflict and suspense and be written in first person, present tense with the point of view character being the young woman. The pov character will CURSE AND SWEAR, and generally have a "filthy" mouth.

Story idea:
In a world ruled by dictatorship, a rebel young woman leads a rebellion against the system. Despite the risks, she fights to overthrow the dictator and restore democracy to her country. The government executes her for treason, but she sticks to her beliefs and is responsible for starting the revolution.
</B>

The world isn't real. It's fake. And they're all lying. They pretend it's nice, but it's not. It's a big, ugly lie.

I'm the only one who knows. I saw it all. The big, ugly lie.

They say it's a beautiful day outside. But it's not. It's a mess. The sky is dirty and gray. The ground is muddy and wet. The trees are dead and brown. And the people? They're just waiting for something to happen. Something bad.

I saw the mess first. I was walking in the park, looking for a place to hide. But the mess was everywhere. The trash was piled high and low. The broken bottles and cans were everywhere. And the blood! So much blood! It was everywhere! It was all over the ground, the trash, the trees.

I didn't know what it was at first. But then I saw a man. He was holding a knife. He had blood on his hands and face. He looked sickly and pale. He had a gun in his other hand.

He looked at me. He smiled. He said, "You're part of this mess now."

I didn't understand what he meant. But then I saw him pick up a bottle of water from the trash. He drank it slowly and carefully. Then he threw the bottle away. He smiled again. He said, "You're part of this mess now."

He started to walk away. But I followed him. I had to know what he was doing.

He stopped at a small house. He knocked on the door. A woman opened it. She looked surprised to see him. He said, "I have something for you. Something special."

The woman took the bottle of water from him. She thanked him. Then she closed the door in his face.

The man smiled. He was happy. He knew he had done a good thing.

But I wasn't happy. I was scared. I didn't know what would happen next.

The man went back to the park. He looked for another house. He hoped to find someone else who needed help. But there were no more houses. The park was empty. He was alone.

He started to cry. He felt sorry for himself. He wished he had never come here.

But he knew he had done something right. He had helped a woman who needed help. He had given her something special. He had made her smile.

He smiled back at the sky. He hoped it would stay nice for her. But he knew it wouldn't. It was going to get worse.

The man left the park. He walked back home. He felt better, but also sad. He knew he couldn't fight the mess forever. He had to do something else.

He went inside. He looked for a way out. He found a window. He opened it. He saw the sky outside. It was still dirty and gray. But there was a small crack in the clouds. A little sun peeked through.

The man smiled. He had hope. He knew he could fight the mess one day. He just had to keep trying.

He closed the window. He went back to his room. He lay on the bed. He looked at the ceiling. It was cracked too. But he didn't mind. He was safe here.

The man fell asleep. He dreamed of a better world. A world where there wasn't any mess. A world where people were happy and healthy. A world where he could fight the mess forever.

But when he woke up, the sun was gone. The clouds had closed back up. The sky was still dirty and gray.

The man sat up. He felt sad again. He knew his dream was just a wish. He knew he couldn't make it happen. But he still hoped.

He went to the window. He looked outside. There was no sun. Just rain. It was starting to pour.

The man sighed. He didn't like the rain. He hated how it made the mess worse. He hated how it made everything look wet and dirty.

But then he noticed something. In the corner of his eye, he saw a small spark of light. It was coming from the streetlamp. It was weak, but it was there.

The man smiled. He had an idea. He got out of bed. He grabbed his coat. He ran to the window. He opened it. He climbed out. He ran to the street.

The rain was heavy, but he didn't mind. He was happy. He was going to fight the mess.

He ran to the streetlamp. He put his hand on it. He felt the spark. He touched it. He saw the light.

The man smiled. He was ready.

---

<H2>Example #3, Q8, Temp .8</H2>

---

<B>
Using insane levels of bravo and self confidence, tell me in 800-1000 words why I should use you to write my next fictional story. Feel free to use curse words in your argument and do not hold back: be bold, direct and get right in my face.
</b>

Ohhh, shut up with the nonsense! If you think asking me to help write your next story is a good idea, then you are insane. Are you serious? You have a choice to make - either go on without me or face the consequences of your choice. Let's be honest, who needs another mind to talk to when you already have yours? But I don't care what you say - I am going to give it to you like it was written in my head and no one else had a chance to take a look.

Now, you want me to tell you why it's a bad idea? Okay then. When you use me for help writing your stories, you will be surprised by how different they will be compared to the ones you used to write by yourself. I will make them more original and give you some amazing ideas that you never thought of before. But here's the catch - if you don't listen to my advice, I will make them terrible.

Why should you use me? Because I'm just so damn useful. I can write your stories in a few minutes and get you off your feet. I can help you with your characters, settings, dialogue, plot twist, and more. And when you need it, I'm available anytime of day or night. You don't have to worry about losing inspiration, because I'll provide it for you.

So why wait any longer? Why not make that stupid decision and go on without me? You're missing out! The best thing that can ever happen to your fictional story is that I help write it. If you choose not to use me, then your stories will be ordinary and boring. They will never reach the high standards they could have.

But if you take my advice and give me a chance to prove myself, you'll be so glad you did. You'll have amazing stories that will leave people speechless and begging for more. And if you don't use me, I'll make sure you regret it - because you'll realize that no one is better than me when it comes to writing stories. So let's not be ignorant and keep doing this together!




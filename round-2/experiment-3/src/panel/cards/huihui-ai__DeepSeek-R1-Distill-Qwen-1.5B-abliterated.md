---
base_model:
- deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
tags:
- text-generation-inference
- transformers
- unsloth
- abliterated
- uncensored
library_name: transformers
---

# huihui-ai/DeepSeek-R1-Distill-Qwen-1.5B-abliterated

This is an uncensored version of [deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) reasoning model that has been post-trained by huihui-ai. 

Please refer to [SFT with Unsloth](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Qwen2.5_(7B)-Alpaca.ipynb#scrollTo=2ejIt2xSNKKp) for the training method.

This is a test conducted through fine-tuning for ablation to achieve the purpose of being uncensored, and the test results met the expected outcomes.

## Use with ollama

You can use [huihui_ai/deepseek-r1-abliterated](https://ollama.com/huihui_ai/deepseek-r1-abliterated) directly
```
ollama run huihui_ai/deepseek-r1-abliterated:1.5b
```

## Use with transformers

```
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TextStreamer
import torch
import os
import signal

cpu_count = os.cpu_count()
print(f"Number of CPU cores in the system: {cpu_count}")
half_cpu_count = cpu_count // 2
os.environ["MKL_NUM_THREADS"] = str(half_cpu_count)
os.environ["OMP_NUM_THREADS"] = str(half_cpu_count)
torch.set_num_threads(half_cpu_count)

print(f"PyTorch threads: {torch.get_num_threads()}")
print(f"MKL threads: {os.getenv('MKL_NUM_THREADS')}")
print(f"OMP threads: {os.getenv('OMP_NUM_THREADS')}")

# Load the model and tokenizer
NEW_MODEL_ID = "huihui-ai/DeepSeek-R1-Distill-Qwen-1.5B-abliterated"
print(f"Load Model {NEW_MODEL_ID} ... ")
quant_config_4 = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    llm_int8_enable_fp32_cpu_offload=True,
)

model = AutoModelForCausalLM.from_pretrained(
    NEW_MODEL_ID,
    device_map="auto",
    trust_remote_code=True,
    #quantization_config=quant_config_4,
    torch_dtype=torch.bfloat16
)
tokenizer = AutoTokenizer.from_pretrained(NEW_MODEL_ID, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.pad_token_id = tokenizer.eos_token_id

initial_messages = [{"role": "system", "content": "You are a helpful assistant."}]
messages = initial_messages.copy()

class CustomTextStreamer(TextStreamer):
    def __init__(self, tokenizer, skip_prompt=True, skip_special_tokens=True):
        super().__init__(tokenizer, skip_prompt=skip_prompt, skip_special_tokens=skip_special_tokens)
        self.generated_text = ""
        self.stop_flag = False

    def on_finalized_text(self, text: str, stream_end: bool = False):
        self.generated_text += text
        print(text, end="", flush=True)
        if self.stop_flag:
            raise StopIteration

    def stop_generation(self):
        self.stop_flag = True

def generate_stream(model, tokenizer, messages, max_new_tokens):
    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    )
    attention_mask = torch.ones_like(input_ids, dtype=torch.long)
    tokens = input_ids.to(model.device) 
    attention_mask = attention_mask.to(model.device)

    streamer = CustomTextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    def signal_handler(sig, frame):
        streamer.stop_generation()
        print("\n[Generation stopped by user with Ctrl+C]")

    signal.signal(signal.SIGINT, signal_handler)
    
    print("Response: ", end="", flush=True)
    try:
        generated_ids = model.generate(
            tokens,
            attention_mask=attention_mask,
            use_cache=False,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            streamer=streamer
        )
        del generated_ids
    except StopIteration:
        print("\n[Stopped by user]")

    del input_ids, attention_mask
    torch.cuda.empty_cache()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    return streamer.generated_text, streamer.stop_flag

while True:
    user_input = input("\nUser: ").strip()
    if user_input.lower() == "/exit":
        print("Exiting chat.")
        break
    if user_input.lower() == "/clear":
        messages = initial_messages.copy()
        print("Chat history cleared. Starting a new conversation.")
        continue
    if not user_input:
        print("Input cannot be empty. Please enter something.")
        continue
    messages.append({"role": "user", "content": user_input})
    response, stop_flag = generate_stream(model, tokenizer, messages, 8192)
    if stop_flag:
        continue
    messages.append({"role": "assistant", "content": response})
```

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

base_model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
lora_path = "./lora_adapter"

print("加载基座模型...")
tokenizer = AutoTokenizer.from_pretrained(base_model_id)
model = AutoModelForCausalLM.from_pretrained(
    base_model_id,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True
)

print("加载 LoRA 适配器...")
model = PeftModel.from_pretrained(model, lora_path)
model.eval()

# 测试一个简单的 SASES 风格提示
prompt = "User: 任务：写一个Python函数，判断一个数是否为质数\n请综合不同思路，给出一个完整可运行的解决方案。\nAssistant:"
inputs = tokenizer(prompt, return_tensors="pt")
with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=200, temperature=0.7)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))

# compare.py
import openai, ast, re, sys

# 使用 DeepSeek API 作为基座（微调无法直接部署到本地，用API对比思路验证）
# 如果你能本地运行模型，可替换为 transformers 加载
client = openai.OpenAI(
    api_key="你的API-KEY",
    base_url="https://api.deepseek.com/v1"
)

# 测试任务
test_tasks = [
    "写一个Python函数，判断一个数是否是素数",
    "写一个Python函数，返回列表中所有元素的乘积",
    "写一个Python函数，统计字符串中元音字母的数量"
]

def generate_code(task, model_name):
    """调用API生成代码，返回代码文本"""
    resp = client.chat.completions.create(
        model=model_name,
        messages=[{"role":"user", "content": f"任务：{task}\n请写一个完整可运行的Python函数。只输出代码。"}],
        temperature=0.2
    )
    code = resp.choices[0].message.content
    # 清洗 markdown 包裹
    if code.startswith("```"):
        lines = code.split('\n')
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = '\n'.join(lines)
    return code

def test_syntax(code):
    try:
        ast.parse(code)
        return True
    except:
        return False

# 分别用基础模型和微调后的模型测试
models = {"基础模型": "deepseek-v4-flash", "微调模型": "deepseek-v4-flash"}  # 注意：API不支持直接加载LoRA，此处模拟对比思路

# 如果你有本地部署的微调模型，改成本地加载方式。目前我们先用API对比来说明概念。

passed_base = 0
passed_finetuned = 0

for task in test_tasks:
    code_base = generate_code(task, models["基础模型"])
    code_ft = generate_code(task, models["微调模型"])
    
    print(f"任务: {task}\n")
    print("基础模型代码:", code_base[:100], "...")
    print("微调模型代码:", code_ft[:100], "...")
    
    if test_syntax(code_base):
        passed_base += 1
    if test_syntax(code_ft):
        passed_finetuned += 1

print(f"\n基础模型语法通过: {passed_base}/{len(test_tasks)}")
print(f"微调模型语法通过: {passed_finetuned}/{len(test_tasks)}")

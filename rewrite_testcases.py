import json, openai, time

client = openai.OpenAI(
    api_key="sk-88208784f9d14eb2a422f992d044bca8",
    base_url="https://api.deepseek.com/v1"
)
MODEL = "deepseek-v4-flash"

with open("seed_tasks.jsonl", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []

for i, line in enumerate(lines):
    task = json.loads(line)
    # 只处理有test_cases的任务
    if "test_cases" not in task or not task["test_cases"]:
        new_lines.append(line)
        continue

    # 把原始test_cases拼接成文本，让API改写成统一格式
    raw = json.dumps(task["test_cases"], ensure_ascii=False)
    prompt = f"""请将以下测试用例数组中的每一个用例，改写为统一格式：
格式：{{"input": [参数1, 参数2, ...], "expected_output": 期望值}}
如果函数只有一个参数，input 数组也只包含一个元素。
直接返回改写后的完整JSON数组，不要加任何解释。

原始测试用例：
{raw}
"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0
    )
    try:
        new_cases = json.loads(resp.choices[0].message.content)
        task["test_cases"] = new_cases
    except json.JSONDecodeError:
        print(f"任务 {task.get('task_id','?')} 改写失败，保留原样")

    new_lines.append(json.dumps(task, ensure_ascii=False) + "\n")
    print(f"已处理 {i+1}/{len(lines)}")
    time.sleep(0.2)  # 避免触发API限速

with open("seed_tasks.jsonl", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("改写完成，seed_tasks.jsonl 已更新。")

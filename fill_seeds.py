import json

with open("seed_tasks.jsonl", "r", encoding="utf-8") as f:
    seeds = [json.loads(line) for line in f]

print(f"当前种子数: {len(seeds)}")
if len(seeds) >= 100:
    print("无需补充。")
    exit()

# 缺少的数量
missing = 100 - len(seeds)
print(f"正在用 API 补充 {missing} 个种子...")

import openai
client = openai.OpenAI(
    api_key="你的DeepSeek-API-Key",
    base_url="https://api.deepseek.com/v1"
)

prompt = f"""生成{missing}个额外的种子任务，格式与之前完全一致，每行一个JSON：
- task_id: "SEED-{{类别}}-{{序号}}"
- category: 均匀分布
- difficulty: 随机
- description: 清晰中文任务
- test_cases: 测试用例列表
- reference_answer: 参考答案
直接输出JSONL，不要任何额外文字。"""

resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role":"user","content":prompt}],
    max_tokens=4096,
    temperature=0.8
)
raw = resp.choices[0].message.content.strip()
if raw.startswith("```"): raw = raw.split("\n",1)[1].rsplit("```",1)[0]

new_seeds = []
for line in raw.split("\n"):
    try: new_seeds.append(json.loads(line))
    except: pass

seeds.extend(new_seeds)
with open("seed_tasks.jsonl", "w", encoding="utf-8") as f:
    for s in seeds:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")
print(f"✅ 补充完成，总种子数: {len(seeds)}")

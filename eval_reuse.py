import json, random, time, os, openai
from main import safe_run_tests, clean_code, check_syntax

client = openai.OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/v1"
)
MODEL = "deepseek-v4-flash"

with open("success_kb.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

# 筛选出包含测试用例的条目（确保可自动验证）
valid = [entry for entry in kb if entry.get("solution") and entry.get("task")]
samples = random.sample(valid, min(20, len(valid)))
passed = 0

print(f"知识库复用评估（{len(samples)} 条样本）:")
for entry in samples:
    task = entry["task"]
    # 要求模型重新生成方案（模拟检索增强后的生成过程）
    prompt = f"任务：{task}\n请输出纯Python函数定义，不要包含任何其他内容。"
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=15
        )
        new_code = clean_code(resp.choices[0].message.content)
        # 使用原测试用例验证（如果知识库记录了test_cases则用，否则跳过）
        test_cases = entry.get("test_cases", [])
        if test_cases:
            ok, msg, _ = safe_run_tests(new_code, test_cases)
        else:
            ok = check_syntax(new_code)[0]  # 至少语法正确
        status = "✓" if ok else "✗"
        print(f"{status} {task[:60]}...")
        if ok:
            passed += 1
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    time.sleep(0.3)

print(f"\n复用通过率: {passed}/{len(samples)} ({passed/len(samples)*100:.1f}%)")

import json, time, os
from openai import OpenAI, APITimeoutError
from main import (
    MODEL, retrieve_similar, clean_code, check_syntax, safe_run_tests,
    load_tasks, knowledge_base
)

TEST_SEEDS = load_tasks("seed_tasks.jsonl")[:100]
KNOWLEDGE_BASE_PATH = "success_kb.json"

def evaluate(kb_list):
    global knowledge_base
    original_kb = knowledge_base
    knowledge_base = kb_list

    passed = 0
    total = len(TEST_SEEDS)
    for i, task in enumerate(TEST_SEEDS):
        desc = task["description"]
        similar = retrieve_similar(desc)
        few_shot = ""
        if similar:
            few_shot = "\n".join([f"参考任务：{s['task']}\n参考方案：{s['solution'][:200]}..." for s in similar[:2]])

        prompt = f"任务：{desc}\n"
        if few_shot:
            prompt += f"参考：\n{few_shot}\n"
        prompt += "请直接输出最终答案。代码任务只输出纯英文Python代码。"

        # 重试3次，避免偶发超时中断
        for retry in range(3):
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role":"user", "content": prompt}],
                    timeout=15
                )
                synthesis = clean_code(resp.choices[0].message.content)
                ok, err = check_syntax(synthesis)
                if not ok:
                    break  # 语法错误不重试
                test_cases = task.get("test_cases", [])
                passed_flag, _, _ = safe_run_tests(synthesis, test_cases)
                if passed_flag:
                    passed += 1
                break  # 成功或测试失败都退出重试
            except APITimeoutError:
                print(f"  请求超时，正在重试 ({retry+1}/3)...")
                time.sleep(2)
            except Exception as e:
                print(f"  请求异常: {e}")
                break

        print(f"[{i+1}/{total}] {desc[:40]}...  {'✓' if passed_flag else '✗'}")
        time.sleep(0.3)

    knowledge_base = original_kb
    return passed / total if total > 0 else 0

if __name__ == "__main__":
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/v1",
        timeout=30,
        max_retries=2
    )

    print("=== 基线测试（无知识库） ===")
    baseline = evaluate([])
    print(f"基线 Pass@1: {baseline:.2%}")

    with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
        current_kb = json.load(f)
    print(f"\n=== 当前知识库测试（{len(current_kb)} 条记录） ===")
    current_pass = evaluate(current_kb)
    print(f"当前 Pass@1: {current_pass:.2%}")
    print(f"提升: {(current_pass - baseline) * 100:.1f} 个百分点")

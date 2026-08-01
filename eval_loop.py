import json, os, time
from main import (
    client, MODEL, retrieve_similar, parse_two_branches,
    clean_code, check_syntax, safe_run_tests, load_tasks,
    knowledge_base  # 导入全局知识库列表
)

TEST_SEEDS = load_tasks("seed_tasks.jsonl")[:100]
KNOWLEDGE_BASE_PATH = "success_kb.json"

def evaluate(kb_list):
    """用指定的知识库列表评测，返回 Pass@1"""
    global knowledge_base
    # 临时替换全局知识库
    original_kb = knowledge_base
    knowledge_base = kb_list

    passed = 0
    for i, task in enumerate(TEST_SEEDS):
        desc = task["description"]
        similar = retrieve_similar(desc)  # 无需传参，内部自动用全局 kb
        few_shot = ""
        if similar:
            few_shot = "\n".join([f"参考任务：{s['task']}\n参考方案：{s['solution'][:200]}..." for s in similar[:2]])
        prompt = f"任务：{desc}\n"
        if few_shot:
            prompt += f"参考：\n{few_shot}\n"
        prompt += "请直接输出最终答案。代码任务只输出纯英文Python代码。"
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user", "content": prompt}]
        )
        synthesis = clean_code(resp.choices[0].message.content)
        ok, err = check_syntax(synthesis)
        if not ok:
            continue
        test_cases = task.get("test_cases", [])
        passed_flag, _, _ = safe_run_tests(synthesis, test_cases)
        if passed_flag:
            passed += 1
        print(f"[{i+1}/{len(TEST_SEEDS)}] {desc[:30]}...  {'✓' if passed_flag else '✗'}")
        time.sleep(0.3)

    # 恢复原知识库
    knowledge_base = original_kb
    return passed / len(TEST_SEEDS)


if __name__ == "__main__":
    print("=== 基线测试（无知识库） ===")
    baseline = evaluate([])
    print(f"基线 Pass@1: {baseline:.2%}")

    # 加载当前知识库
    with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
        current_kb = json.load(f)
    print(f"\n=== 当前知识库测试（{len(current_kb)} 条记录） ===")
    current_pass = evaluate(current_kb)
    print(f"当前 Pass@1: {current_pass:.2%}")
    print(f"提升: {(current_pass - baseline) * 100:.1f} 个百分点")

import json
import random
from collections import defaultdict

KB_FILE = "success_kb.json"
BENCHMARK_FILE = "eval_benchmark.jsonl"

def main():
    random.seed(42)  # 固定随机种子，保证可复现

    with open(KB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"当前知识库记录数: {len(data)}")

    # 按领域简单分组（从任务描述提取关键词）
    groups = defaultdict(list)
    for item in data:
        task = item.get("task", "")
        # 简单按任务长度分组，避免复杂领域识别
        if len(task) < 30:
            groups["short"].append(item)
        elif len(task) < 60:
            groups["medium"].append(item)
        else:
            groups["long"].append(item)

    # 从每组抽取等量样本，总共最多100条
    sample_size = min(100, len(data))
    per_group = sample_size // max(1, len(groups))
    selected = []

    for group_items in groups.values():
        random.shuffle(group_items)
        selected.extend(group_items[:per_group])

    # 如果不够100条，补齐
    if len(selected) < sample_size:
        remaining = [x for x in data if x not in selected]
        random.shuffle(remaining)
        selected.extend(remaining[:sample_size - len(selected)])

    # 保存为评估基准
    with open(BENCHMARK_FILE, "w", encoding="utf-8") as f:
        for item in selected[:100]:
            benchmark_entry = {
                "task_id": item.get("id", ""),
                "description": item.get("task", ""),
                "solution": item.get("solution", ""),
                "verified": True
            }
            f.write(json.dumps(benchmark_entry, ensure_ascii=False) + "\n")

    print(f"已生成评估基准: {BENCHMARK_FILE}")
    print(f"样本数量: {min(100, len(selected))}")
    print("任务长度分布:")
    for group, items in groups.items():
        print(f"  {group}: {len(items)} 条")

if __name__ == "__main__":
    main()

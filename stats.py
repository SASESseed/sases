import json
from collections import defaultdict

KB_FILE = "success_kb.json"

def load_kb():
    with open(KB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    data = load_kb()
    print(f"总记录数: {len(data)}")

    # 模型统计
    model_stats = defaultdict(lambda: {"count": 0, "total_backtrack": 0})
    for item in data:
        mid = item.get("model_id", "unknown")
        model_stats[mid]["count"] += 1
        model_stats[mid]["total_backtrack"] += item.get("backtrack_count", 0)

    print("\n=== 模型统计 ===")
    for mid, st in model_stats.items():
        avg = st["total_backtrack"] / st["count"] if st["count"] else 0
        print(f"{mid}: 数量 {st['count']}, 平均回溯 {avg:.2f}")

    # 用户统计
    user_stats = defaultdict(int)
    for item in data:
        uid = item.get("user_id", "unknown")
        user_stats[uid] += 1

    print("\n=== 用户统计 ===")
    for uid, count in user_stats.items():
        print(f"{uid}: {count} 条")

    # 最近5条记录
    print("\n=== 最近5条记录 ===")
    for item in data[-5:]:
        ts = item.get("timestamp", "?")
        task = item.get("task", "")[:50]
        bt = item.get("backtrack_count", 0)
        print(f"- [{ts}] {task}... (回溯:{bt})")

if __name__ == "__main__":
    main()

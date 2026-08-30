import json
from core.db import get_db, init_db
from core import knowledge_base

# 确保数据库表存在
init_db()

# 检查旧 JSON 文件是否存在
try:
    with open("success_kb.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("未找到 success_kb.json，无需迁移。")
    exit()

for item in data:
    knowledge_base.add_to_kb(
        task=item.get("task", ""),
        branch_a=item.get("branch_a", ""),
        branch_b=item.get("branch_b", ""),
        synthesis=item.get("solution", ""),
        model_id=item.get("model_id", "unknown"),
        user_id=item.get("user_id", "system"),
        backtrack_count=item.get("backtrack_count", 0),
        test_cases=item.get("test_cases", [])
    )

print(f"迁移完成，共 {len(data)} 条记录")

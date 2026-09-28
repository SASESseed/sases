import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services import pattern_service
from core.db import db_cursor

# 清理测试数据
with db_cursor(commit=True) as cur:
    cur.execute("DELETE FROM interaction_patterns WHERE pattern_key LIKE '_test_%'")

print("测试 _upsert_pattern 的 pattern_key 兼容性")

# 测试 1：写入一个 retry key
id1 = pattern_service._upsert_pattern(
    domain="dev",
    pattern_key="_test_file_patch_retry",
    pattern_type="failure",
    context_signature="executor:harness:py",
    role="executor",
    evidence="_test_file_patch_retry | file_patch 失败 | 原片段未找到",
    source_task_id="test_1",
    user_id=1,
)
print(f"写入 _test_file_patch_retry → id={id1}")

# 测试 2：写入细分后的 key（不应该合并到 id1）
id2 = pattern_service._upsert_pattern(
    domain="dev",
    pattern_key="_test_file_patch_retry_not_found",
    pattern_type="failure",
    context_signature="executor:harness:py",
    role="executor",
    evidence="_test_file_patch_retry_not_found | file_patch 失败 | 原片段未找到",
    source_task_id="test_2",
    user_id=1,
)
print(f"写入 _test_file_patch_retry_not_found → id={id2}")

# 检查
with db_cursor() as cur:
    cur.execute("SELECT id, pattern_key, hit_count FROM interaction_patterns WHERE pattern_key LIKE '_test_%'")
    rows = cur.fetchall()
    print(f"\n结果：{len(rows)} 条记录")
    for r in rows:
        print(f"  id={r['id']} | key={r['pattern_key']} | hit={r['hit_count']}")

# 判定
if len(rows) == 2 and id1 != id2:
    print("\n✅ 通过：两个 key 独立入库，兼容性检查生效")
elif len(rows) == 1:
    print("\n❌ 失败：被合并成一条，兼容性检查未生效")
else:
    print(f"\n⚠️ 意外：{len(rows)} 条记录")

# 清理
with db_cursor(commit=True) as cur:
    cur.execute("DELETE FROM interaction_patterns WHERE pattern_key LIKE '_test_%'")
print("\n测试数据已清理")

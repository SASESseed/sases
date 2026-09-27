import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services import pattern_service

# 模拟一个失败的 file_patch step
test_steps = [
    {
        "status": "failed",
        "review": "retry",
        "command": "file_patch",
        "type": "harness",
        "module_id": "file_patch",
        "reason": "Harness 失败: 原片段在 core/services/swarm_service.py 中未找到。",
        "description": "改文件",
    },
    {
        "status": "failed",
        "review": "retry",
        "command": "file_patch",
        "type": "harness",
        "module_id": "file_patch",
        "reason": "Harness 失败: 原片段在 core/services/swarm_service.py 中出现 2 次",
        "description": "改文件",
    },
    {
        "status": "blocked",
        "review": "retry",
        "command": "harness:file_patch core/xxx.py",
        "type": "command",
        "reason": "命令不在白名单: harness:file_patch",
        "description": "改文件",
    },
    {
        "status": "format_error",
        "review": "retry",
        "command": "harness:file_read core/config.py",
        "type": "command",
        "reason": "step 格式错误",
        "description": "读文件",
    },
]

print("=" * 70)
print("_extract_pattern_key 测试")
print("=" * 70)

for i, s in enumerate(test_steps, 1):
    key = pattern_service._extract_pattern_key(s, s["status"], s["review"])
    ptype = pattern_service._classify_pattern_type(s["status"], s["review"], 3)
    print(f"\n[{i}] status={s['status']}, reason={s['reason'][:50]}")
    print(f"    → key   = {key}")
    print(f"    → type  = {ptype}")

print("\n" + "=" * 70)
print("期望结果")
print("=" * 70)
print("""
[1] 未找到 → harness_file_patch_retry_not_found | failure
[2] 出现2次 → harness_file_patch_retry_ambiguous | failure
[3] 白名单 → cmd_harness:file_patch_blocked_whitelist | blocked
[4] format → cmd_harness:file_read_format_error | format
""")

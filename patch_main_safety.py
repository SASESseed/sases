with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 添加导入 safety_scan
if "import safety_scan" not in content:
    content = content.replace(
        "import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime",
        "import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime\nimport safety_scan"
    )

# 2. 在 add_to_kb 函数开头添加安全扫描调用
old_add = '''def add_to_kb(task, branch_a, branch_b, synthesis, model_id=MODEL, user_id="system", backtrack_count=0):
    knowledge_base.append({'''
new_add = '''def add_to_kb(task, branch_a, branch_b, synthesis, model_id=MODEL, user_id="system", backtrack_count=0):
    # 安全扫描：拦截恶意或高风险内容
    if not safety_scan.before_add_to_kb(synthesis):
        print("  安全扫描拦截，拒绝入库。")
        return
    knowledge_base.append({'''

if old_add in content:
    content = content.replace(old_add, new_add)
    print("安全扫描已集成到 add_to_kb。")
else:
    print("警告：未找到 add_to_kb 函数起始位置，需手动检查。")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("补丁完成！")

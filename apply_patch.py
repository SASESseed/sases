import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 确保导入 datetime
if "import datetime" not in content:
    content = content.replace(
        "import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect",
        "import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime"
    )

# 2. 替换 add_to_kb 函数
old_func = '''def add_to_kb(task, branch_a, branch_b, synthesis):
    knowledge_base.append({
        "task": task,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "solution": synthesis,
        "verified": True,
        "id": str(uuid.uuid4())
    })
    save_kb(knowledge_base)'''

new_func = '''def add_to_kb(task, branch_a, branch_b, synthesis, model_id=MODEL, user_id="system", backtrack_count=0):
    knowledge_base.append({
        "task": task,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "solution": synthesis,
        "verified": True,
        "id": str(uuid.uuid4()),
        "model_id": model_id,
        "user_id": user_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "backtrack_count": backtrack_count
    })
    save_kb(knowledge_base)'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("add_to_kb 函数已更新")
else:
    print("警告：未找到原 add_to_kb 函数，请检查 main.py")

# 3. 在调用 add_to_kb 的位置增加 backtrack_count 变量并传入参数
old_call = "add_to_kb(desc, branch_a, branch_b, synthesis)"
new_call = "backtrack_count = 0\n                add_to_kb(desc, branch_a, branch_b, synthesis, model_id=MODEL, user_id=\"system\", backtrack_count=backtrack_count)"

if old_call in content:
    content = content.replace(old_call, new_call)
    print("调用位置已更新")
else:
    print("警告：未找到 add_to_kb 调用位置，可能需要手动修改")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("补丁应用完成！")

import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

new_func = '''def add_to_kb(task, branch_a, branch_b, synthesis, model_id=MODEL, user_id="system", backtrack_count=0):
    # 安全扫描：拦截恶意或高风险内容
    import safety_scan
    if not safety_scan.before_add_to_kb(synthesis):
        print("  安全扫描拦截，拒绝入库。")
        return
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

# 匹配 def add_to_kb 到下一个 def 或文件结束
pattern = r'def add_to_kb\(.*?\n(?=def |\Z)'
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + new_func + "\n\n" + content[match.end():]
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("add_to_kb 已替换并集成安全扫描。")
else:
    print("未找到 add_to_kb 函数，请手动检查 main.py。")

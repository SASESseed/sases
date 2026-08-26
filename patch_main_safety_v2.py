import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 确保已导入 safety_scan
if "import safety_scan" not in content:
    content = content.replace(
        "import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime",
        "import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime\nimport safety_scan"
    )

# 在 add_to_kb 函数定义后插入安全扫描调用
pattern = r'(def add_to_kb\([^)]*\):\n)'
replacement = r'\1    # 安全扫描：拦截恶意或高风险内容\n    if not safety_scan.before_add_to_kb(synthesis):\n        print("  安全扫描拦截，拒绝入库。")\n        return\n'
new_content, count = re.subn(pattern, replacement, content)

if count == 0:
    print("警告：未找到 add_to_kb 函数定义，可能格式不同，请手动检查。")
else:
    print(f"已在 {count} 处插入安全扫描调用。")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("补丁完成！")

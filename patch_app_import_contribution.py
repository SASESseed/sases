with open("app_full.py", "r", encoding="utf-8") as f:
    content = f.read()

old_import = "import contribution_log"
new_import = "from core import contribution_log"

if old_import in content:
    content = content.replace(old_import, new_import)
    print("已将导入改为 from core import contribution_log")
else:
    print("未找到旧导入，请检查 app_full.py")

with open("app_full.py", "w", encoding="utf-8") as f:
    f.write(content)

print("补丁完成！")

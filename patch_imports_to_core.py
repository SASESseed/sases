import re

def patch_file(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"已更新 {path}")
    else:
        print(f"{path} 无需更新")

# app_full.py 中的旧导入
patch_file("app_full.py", {
    "import safety_scan": "from core import safety_scan",
    "import sandbox": "from core import sandbox"
})

# process_seeds.py 中可能没有直接导入 sandbox/safety_scan，但检查一下
patch_file("process_seeds.py", {
    "import sandbox": "from core import sandbox",
    "import safety_scan": "from core import safety_scan"
})

print("导入补丁完成！")

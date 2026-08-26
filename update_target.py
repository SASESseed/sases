# -*- coding: utf-8 -*-
import io

with io.open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("TARGET_SUCCESS = 474", "TARGET_SUCCESS = 600")

with io.open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("TARGET_SUCCESS 已更新为 600")

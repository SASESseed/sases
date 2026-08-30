import re

path = "core/api_routes/seed_routes.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 确保导入 Optional
if "from typing import Optional" not in content:
    if "from typing import" in content:
        content = content.replace("from typing import", "from typing import Optional,")
    else:
        # 在文件顶部添加导入
        content = "from typing import Optional\n" + content

# 替换 ChatRequest 类中的字段为 Optional
old_class = '''class ChatRequest(BaseModel):
    query: str
    image: str = None
    audio: str = None
    video: str = None'''

new_class = '''class ChatRequest(BaseModel):
    query: str
    image: Optional[str] = None
    audio: Optional[str] = None
    video: Optional[str] = None'''

if old_class in content:
    content = content.replace(old_class, new_class)
    print("ChatRequest 已更新为 Optional 字段。")
else:
    # 如果旧类不匹配，尝试更通用的替换：查找 query: str 后的 image/audio/video 行
    # 这里简单输出警告，用户需要手动检查
    print("警告：未找到预期的 ChatRequest 定义，请手动检查 seed_routes.py")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("修复脚本执行完毕。")

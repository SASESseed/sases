import os
import re

target_dir = "."
file_pattern = re.compile(r".*\.py$")
old_pattern = re.compile(r"datetime\.UTC")
new_text = "datetime.timezone.utc"

for root, dirs, files in os.walk(target_dir):
    dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "node_modules", ".venv"]]
    for file in files:
        if file_pattern.match(file):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_pattern.search(content):
                new_content = old_pattern.sub(new_text, content)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"已修复: {path}")

import os
import json

modules = {
    "calculator": {
        "manifest": {
            "id": "calculator",
            "name": "安全计算器",
            "description": "计算简单的算术表达式，支持 + - * / 和括号",
            "version": "1.0.0",
            "capabilities": ["arithmetic", "calculation"],
            "permissions": [],
            "entrypoint": "main.py",
            "node_type": "harness"
        },
        "main": '''import ast

def run(params):
    expression = params.get("expression", "")
    if not expression:
        raise ValueError("缺少 expression 参数")
    allowed_nodes = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div)
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ValueError("表达式语法错误")
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise ValueError("表达式包含不允许的操作")
    result = eval(compile(tree, "<string>", "eval"), {"__builtins__": {}})
    return {"result": result}
'''
    },
    "text_stats": {
        "manifest": {
            "id": "text-stats",
            "name": "文本统计",
            "description": "统计文本的字符数、单词数、行数和词频",
            "version": "1.0.0",
            "capabilities": ["text_analysis", "statistics"],
            "permissions": [],
            "entrypoint": "main.py",
            "node_type": "harness"
        },
        "main": '''import re
from collections import Counter

def run(params):
    text = params.get("text", "")
    if not text:
        raise ValueError("缺少 text 参数")
    words = re.findall(r'\\w+', text.lower())
    lines = text.split('\\n')
    return {
        "char_count": len(text),
        "word_count": len(words),
        "line_count": len(lines),
        "top_words": dict(Counter(words).most_common(10))
    }
'''
    },
    "json_formatter": {
        "manifest": {
            "id": "json-formatter",
            "name": "JSON 格式化",
            "description": "美化或压缩 JSON 字符串",
            "version": "1.0.0",
            "capabilities": ["json", "formatting"],
            "permissions": [],
            "entrypoint": "main.py",
            "node_type": "harness"
        },
        "main": '''import json

def run(params):
    json_string = params.get("json_string", "")
    indent = params.get("indent", 2)
    if not json_string:
        raise ValueError("缺少 json_string 参数")
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")
    if indent is None or indent <= 0:
        formatted = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    else:
        formatted = json.dumps(data, ensure_ascii=False, indent=indent)
    return {"formatted": formatted}
'''
    },
    "base64_codec": {
        "manifest": {
            "id": "base64-codec",
            "name": "Base64 编解码",
            "description": "对文本进行 Base64 编码或解码",
            "version": "1.0.0",
            "capabilities": ["encoding", "base64"],
            "permissions": [],
            "entrypoint": "main.py",
            "node_type": "harness"
        },
        "main": '''import base64

def run(params):
    action = params.get("action", "")
    text = params.get("text", "")
    if action == "encode":
        result = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    elif action == "decode":
        try:
            result = base64.b64decode(text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Base64 解码失败: {e}")
    else:
        raise ValueError("action 必须是 encode 或 decode")
    return {"result": result}
'''
    },
    "string_utils": {
        "manifest": {
            "id": "string-utils",
            "name": "字符串工具",
            "description": "字符串反转、大小写转换等",
            "version": "1.0.0",
            "capabilities": ["string", "text_processing"],
            "permissions": [],
            "entrypoint": "main.py",
            "node_type": "harness"
        },
        "main": '''def run(params):
    operation = params.get("operation", "")
    text = params.get("text", "")
    if operation == "reverse":
        result = text[::-1]
    elif operation == "upper":
        result = text.upper()
    elif operation == "lower":
        result = text.lower()
    elif operation == "capitalize":
        result = text.capitalize()
    else:
        raise ValueError("operation 必须是 reverse、upper、lower 或 capitalize")
    return {"result": result}
'''
    }
}

base_dir = "harness_modules"
os.makedirs(base_dir, exist_ok=True)

for dir_name, content in modules.items():
    module_dir = os.path.join(base_dir, dir_name)
    os.makedirs(module_dir, exist_ok=True)
    with open(os.path.join(module_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(content["manifest"], f, ensure_ascii=False, indent=2)
    with open(os.path.join(module_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write(content["main"])
    print(f"已创建模块: {dir_name}")

print("所有示例模块创建完成。")

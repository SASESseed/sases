import openai
import ast
import re
import time
import json
import os
import subprocess
import tempfile
import inspect

from core import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=120,
    max_retries=2
)

def is_python_code(text):
    return bool(re.search(r'\bdef\s+\w+\s*\(', text)) or bool(re.search(r'\bclass\s+\w+', text))

def clean_code(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split('\n')
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text

def check_syntax(code):
    if not is_python_code(code):
        return True, ""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, str(e)

def safe_run_tests(code, test_cases, timeout=5):
    """在隔离沙箱中运行代码并执行测试用例。返回 (passed, message, is_code)。"""
    if not test_cases:
        return False, "无测试用例", False
    if not is_python_code(code):
        return False, "非代码答案", False

    code = re.sub(r"if __name__\s*==\s*['\"]__main__['\"]:\s*\n.*", "", code, flags=re.DOTALL)
    code = re.sub(r"\n\s*\w+\(\)", "", code)

    func_match = re.search(r"def (\w+)", code)
    if not func_match:
        return False, "无函数定义", False
    func_name = func_match.group(1)
    code_renamed = re.sub(r'def\s+' + func_name + r'\b', 'def __test_func__', code, count=1)

    for case in test_cases:
        inp = case.get("input", [])
        expected = case.get("expected_output")
        expected_repr = repr(expected)

        full_test = f"""
{code_renamed}
import json, sys, inspect
try:
    func = __test_func__
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if isinstance({json.dumps(inp)}, list):
        if len(params) == 1:
            result = func({json.dumps(inp)})
        elif len(params) == len({json.dumps(inp)}):
            result = func(*{json.dumps(inp)})
        else:
            result = func({json.dumps(inp)})
    else:
        result = func({json.dumps(inp)})
    passed = (result == {expected_repr})
    print(json.dumps({{"passed": passed, "output": str(result)}}))
except Exception as e:
    print(json.dumps({{"passed": False, "error": str(e)}}))
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(full_test)
            tmp_path = f.name
        try:
            proc = subprocess.run(["python", tmp_path], capture_output=True, text=True, timeout=timeout)
            if proc.returncode != 0:
                return False, f"执行出错: {proc.stderr.strip()}", False
            result = json.loads(proc.stdout.strip())
            if not result.get("passed", False):
                return False, f"测试失败: {result}", False
        except subprocess.TimeoutExpired:
            return False, "执行超时", False
        finally:
            os.unlink(tmp_path)
    return True, "全部测试通过", True

def parse_two_branches(text):
    a, b = "", ""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if "思路A" in line or "思路 A" in line:
            if ":" in line:
                a = line.split(":", 1)[1].strip()
            else:
                for j in range(i+1, len(lines)):
                    if "思路B" in lines[j] or "思路 B" in lines[j]:
                        break
                    if lines[j].strip():
                        a += lines[j].strip() + " "
                a = a.strip()
        if "思路B" in line or "思路 B" in line:
            if ":" in line:
                b = line.split(":", 1)[1].strip()
            else:
                for j in range(i+1, len(lines)):
                    if lines[j].strip():
                        b += lines[j].strip() + " "
                b = b.strip()
    return (a or "默认算法A"), (b or "默认算法B")

def call_chat(prompt, max_retries=2, temperature=0.7, model=None):
    """调用 DeepSeek API，带重试。model 默认使用 config.MODEL_NAME。"""
    if model is None:
        model = config.MODEL_NAME
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role":"user", "content":prompt}],
                temperature=temperature
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_error = e
            print(f"  API调用失败（尝试 {attempt+1}/{max_retries+1}）：{e}")
            if attempt < max_retries:
                time.sleep(5)
    raise last_error

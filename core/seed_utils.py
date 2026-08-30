import openai
import ast
import re
import time
import json
import os
import base64
import subprocess
import tempfile
import inspect

from core import config

# 默认客户端（使用系统环境变量）
_client = openai.OpenAI(
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

def _call_openai_with_key(provider: str, api_key: str, model: str, messages: list, temperature: float, max_retries: int):
    base_url = config.PROVIDER_BASE_URLS.get(provider, config.DEEPSEEK_BASE_URL)
    client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=120, max_retries=max_retries)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return resp.choices[0].message.content

def call_chat(prompt, max_retries=2, temperature=0.7, model=None, user_id=None, image_base64=None):
    """
    调用模型生成回复。
    如果提供了 user_id，则优先使用该用户配置的 API Keys（按优先级）。
    如果提供了 image_base64，则构造多模态消息，并根据 provider 选择对应的视觉模型。
    """
    if model is None:
        model = config.MODEL_NAME  # 默认文本模型

    # 构造消息
    messages = []
    if image_base64:
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})

    # 如果提供了用户ID，尝试使用用户API Key
    if user_id is not None:
        try:
            from core import auth_service
            api_keys = auth_service.get_active_api_keys(user_id)
        except Exception:
            api_keys = []

        if api_keys:
            last_error = None
            for entry in api_keys:
                provider = entry["provider"]
                api_key = entry["key"]
                # 根据是否图片输入选择模型
                if image_base64:
                    # 从映射中获取该提供商的视觉模型，若没有则跳过
                    vision_model = config.VISION_MODEL_BY_PROVIDER.get(provider)
                    if not vision_model:
                        print(f"Provider {provider} 不支持视觉模型，跳过")
                        continue
                    model_to_use = vision_model
                else:
                    model_to_use = model  # 文本任务使用传入的 model（可能为默认模型）
                try:
                    return _call_openai_with_key(provider, api_key, model_to_use, messages, temperature, max_retries)
                except Exception as e:
                    last_error = e
                    print(f"Provider {provider} 调用失败: {e}")
                    continue
            if last_error:
                raise last_error

    # 回退到默认客户端
    last_error = None
    # 如果有图片，使用默认视觉模型
    if image_base64:
        model = config.VISION_MODEL_NAME
    for attempt in range(max_retries + 1):
        try:
            resp = _client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_error = e
            print(f"默认 API 调用失败（尝试 {attempt+1}/{max_retries+1}）：{e}")
            if attempt < max_retries:
                time.sleep(5)
    raise last_error

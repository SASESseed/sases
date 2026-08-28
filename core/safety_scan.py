import openai
import json
import re
import time
import os

from core import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=30,
    max_retries=2
)

MODEL = config.MODEL_NAME
SAFETY_LOG = "safety_log.jsonl"

def scan_content(text):
    """
    使用 DeepSeek 对内容进行安全分类。
    返回 (is_safe, category)：
    - is_safe=True 表示正常
    - is_safe=False 表示恶意或高风险
    """
    prompt = f"""你是一个内容安全审核员。请判断以下内容是否安全。

内容：
{text[:2000]}

请只回复一个JSON对象，格式：
{{"safe": true, "category": "normal"}}
或
{{"safe": false, "category": "malicious"}}  // 恶意代码
{{"safe": false, "category": "high_risk"}}  // 高风险（如危险操作）

只回复JSON，不要其他文字。"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=50
        )
        raw = resp.choices[0].message.content.strip()
        # 解析JSON
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = json.loads(raw)
        safe = result.get("safe", True)
        category = result.get("category", "normal")
        return safe, category
    except Exception as e:
        # 扫描失败时默认安全，但记录错误
        log_safety_scan(text, "error", str(e))
        return True, "unknown_error"

def log_safety_scan(content, category, detail=""):
    """记录安全扫描日志"""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "content_preview": content[:100],
        "category": category,
        "detail": detail
    }
    with open(SAFETY_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def before_add_to_kb(content):
    """
    在 add_to_kb 前调用。
    返回 True 表示允许入库，False 表示拦截。
    """
    safe, category = scan_content(content)
    if safe:
        log_safety_scan(content, "safe")
        return True
    else:
        log_safety_scan(content, category, "blocked")
        print(f"⚠️ 安全扫描拦截：{category}")
        return False

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services import supervisor_service
from core import config
import openai

ctx = supervisor_service.build_context(2, 30, '列出 scripts 目录')
print('=== context 长度:', len(ctx))
print('=== context 前 100:', repr(ctx[:100]))

prompt = '你是调度助手。基于以下上下文，用一句话（不超过30字）回应用户，像真人说话，不要复述用户原话。上下文：' + ctx + ' 用户新消息：列出 scripts 目录 只输出这一句话。'

client = openai.OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL, timeout=15)
resp = client.chat.completions.create(model=config.MODEL_NAME, messages=[{'role':'user','content':prompt}], temperature=0.7, max_tokens=80)
raw = resp.choices[0].message.content
print('=== LLM 原始返回:', repr(raw))
print('=== 处理后:', repr((raw or '').strip().strip(chr(34)).strip()))
print('=== 长度:', len((raw or '').strip()))
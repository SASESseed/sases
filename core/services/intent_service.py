# core/services/intent_service.py
"""
意图识别：判断用户输入是"普通聊天"还是"可执行任务"

两层判断：
1. 规则过滤（零成本）：快速命中闲聊或任务
2. LLM 判断（仅中间地带）：调一次轻量 LLM
"""
import asyncio
import re
import openai

from .. import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=15,
    max_retries=1
)

MODEL = config.MODEL_NAME

# ========== 第一层：规则 ==========

# 纯聊天（命中即判定为 chat，不再调 LLM）
CHAT_PATTERNS = [
    r'^(你好|您好|hi|hello|hey|嗨|哈喽)[\s!！。.？?]*$',
    r'^(谢谢|感谢|thanks|thank you)[\s!！。.]*$',
    r'^(好的|是的|对|嗯|ok|okay|明白|收到|知道了)[\s!！。.]*$',
    r'^(再见|拜拜|晚安|早安|bye)[\s!！。.]*$',
    r'^[\s\?？!！。.…]+$',           # 纯标点
    r'^[\U0001F300-\U0001F9FF\s]+$',  # 纯 emoji
]

# 任务关键词（命中即判定为 task，不再调 LLM）
TASK_VERBS = [
    "列出", "查看", "打开", "执行", "运行", "启动", "创建", "删除", "查找", "搜索",
    "复制", "移动", "重命名", "安装", "卸载", "下载", "上传", "压缩", "解压",
    "统计", "分析", "计算", "检查", "测试", "编译", "构建", "部署",
    "看", "读", "写", "改", "跑", "查", "找", "拿",
]

TASK_NOUNS = [
    "目录", "文件", "文件夹", "进程", "端口", "服务", "系统", "盘", "路径",
    "环境", "配置", "日志", "代码", "脚本", "命令", "项目", "仓库",
]

# 路径特征：C:\、D:\、/usr/、./、../
PATH_PATTERN = re.compile(r'([A-Za-z]:\\|/[a-z]+/|\.\/|\.\.\/|\*\.[a-z]+)')


def _is_obvious_chat(content: str) -> bool:
    text = content.strip()
    if not text:
        return True
    if len(text) < 4:
        return True
    for pattern in CHAT_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    return False


def _is_obvious_task(content: str) -> bool:
    text = content.strip()
    # 路径特征
    if PATH_PATTERN.search(text):
        return True
    # 动词 + 名词
    for verb in TASK_VERBS:
        if verb in text:
            for noun in TASK_NOUNS:
                if noun in text:
                    return True
    return False


async def _llm_judge(content: str) -> bool:
    """调 LLM 判断是否为任务，返回 True 表示是任务"""
    prompt = f"""判断用户输入属于以下哪一类，只回答一个字母：

A) 普通聊天（问候、闲聊、情感表达、知识问答）
B) 可执行任务（需要操作本机计算机、查看文件、执行命令等）

用户输入：{content}

只回答 A 或 B。"""

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5
        )
        answer = resp.choices[0].message.content.strip().upper()
        return answer.startswith("B")
    except Exception:
        # LLM 不可用时，默认走普通聊天，避免误触发
        return False


async def is_task_intent(content: str) -> bool:
    """
    判断用户输入是否为可执行任务
    """
    if not content or not content.strip():
        return False

    # 第一层：规则
    if _is_obvious_chat(content):
        return False

    if _is_obvious_task(content):
        return True

    # 第二层：LLM 判断（中间地带）
    return await _llm_judge(content)

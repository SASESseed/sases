import requests
import time
import json
import sys

BASE_URL = "http://127.0.0.1:8001"

# ==================== 指挥官系统提示（含文件操作规则） ====================
COMMANDER_SYSTEM_PROMPT = """
你是 SASES 指挥官智能体。你在与执行者协作时，必须遵循以下规则：

1. 如果用户说“给全文”，你要生成读取该文件完整内容的命令，如 `type 文件路径`，而不是回复“好的”。
2. 如果用户说“不要让我改代码”，你要生成直接产生完整代码或覆盖文件的命令，例如通过 `python -c` 写入文件或 `echo` 重定向。
3. 如果用户要求“一步一步给出完整代码”，你要把任务拆分为多个命令，但一次只生成当前步骤的命令。
4. 使用 Windows CMD 兼容的命令，避免多行反斜杠。
5. 只输出命令本身，不要解释，不要输出额外文字。
6. 禁止生成启动或停止服务器的命令（如 uvicorn）。
7. 如果用户请求模糊，输出 `echo 请提供更具体的任务说明`。

示例：
- 用户要求“读取 core/db.py 全文” → 输出 `type core\\db.py`
- 用户要求“给完整代码覆盖 me.js” → 输出 `python -c "open('static/modules/me.js','w',encoding='utf-8').write('...')"` 或使用 `echo` 重定向（注意转义）
- 用户要求“一步一步修改文件” → 只输出第一步的命令，例如 `echo 第一步：备份文件`
"""


def login(username, password):
    resp = requests.post(
        f"{BASE_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def call_deepseek_analyze(token, user_text):
    """调用 SASES 的 /agent/chat，让模型提取命令，并注入系统提示"""
    full_prompt = COMMANDER_SYSTEM_PROMPT + "\n\n" + f"请从以下用户请求中提取一个可以直接在Windows CMD执行的shell命令，只输出命令本身，不要解释：\n{user_text}"
    resp = requests.post(
        f"{BASE_URL}/agent/chat",
        json={"query": full_prompt},
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code == 200:
        data = resp.json()
        raw = data.get("response", "").strip()
        # 简单清理：只保留第一行非空命令
        lines = [line.strip() for line in raw.split('\n') if line.strip()]
        return lines[0] if lines else ""
    return None


def get_new_messages(token, conversation_id, after_id):
    resp = requests.get(
        f"{BASE_URL}/messages/conversations/{conversation_id}/messages",
        params={"after_id": after_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("messages", [])


def send_commander_message(token, conversation_id, command, commander_agent_id):
    requests.post(
        f"{BASE_URL}/messages/send",
        json={
            "conversation_id": conversation_id,
            "content": command,
            "sender_agent_id": commander_agent_id
        },
        headers={"Authorization": f"Bearer {token}"}
    )


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("用法: python commander_analyzer.py 用户名 密码 会话ID 指挥官智能体ID 执行者智能体ID")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    conversation_id = int(sys.argv[3])
    commander_agent_id = sys.argv[4]
    executor_agent_id = sys.argv[5]

    token = login(username, password)
    print("指挥官分析器已登录，开始监听用户消息...")

    last_message_id = 0
    initial_messages = get_new_messages(token, conversation_id, 0)
    if initial_messages:
        last_message_id = max(msg["id"] for msg in initial_messages)
    print(f"当前最新消息ID: {last_message_id}")

    while True:
        new_messages = get_new_messages(token, conversation_id, last_message_id)
        for msg in new_messages:
            last_message_id = max(last_message_id, msg["id"])
            if msg.get("sender") == "user" and not msg.get("sender_agent_id"):
                user_text = msg["content"].strip()
                print(f"收到用户长文: {user_text[:80]}...")
                command = call_deepseek_analyze(token, user_text)
                if command:
                    print(f"提取到命令: {command}")
                    send_commander_message(token, conversation_id, command, commander_agent_id)
                else:
                    print("未能提取命令，跳过")
        time.sleep(3)

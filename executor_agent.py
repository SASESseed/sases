import requests
import time
import subprocess
import sys

BASE_URL = "http://127.0.0.1:8001"

def login(username, password):
    resp = requests.post(
        f"{BASE_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def get_new_messages(token, conversation_id, after_id):
    resp = requests.get(
        f"{BASE_URL}/messages/conversations/{conversation_id}/messages",
        params={"after_id": after_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("messages", [])

def send_reply(token, conversation_id, content, sender_agent_id):
    requests.post(
        f"{BASE_URL}/messages/send",
        json={
            "conversation_id": conversation_id,
            "content": content,
            "sender_agent_id": sender_agent_id
        },
        headers={"Authorization": f"Bearer {token}"}
    )

def report_work_result(token, conversation_id, command, output, status, duration_ms, agent_id):
    """调用 /work/report 让后端记录日志和发送助手通知"""
    requests.post(
        f"{BASE_URL}/work/report",
        json={
            "conversation_id": conversation_id,
            "command": command,
            "output": output,
            "status": status,
            "duration_ms": duration_ms,
            "sender_agent_id": agent_id
        },
        headers={"Authorization": f"Bearer {token}"}
    )

def execute_command(command, timeout=30):
    import datetime
    start = datetime.datetime.now()
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        output = (result.stdout or "") + (result.stderr or "")
        status = "success" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        output = "命令执行超时"
        status = "timeout"
    except Exception as e:
        output = f"命令执行异常: {str(e)}"
        status = "error"
    duration_ms = int((datetime.datetime.now() - start).total_seconds() * 1000)
    return output, status, duration_ms

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("用法: python executor_agent.py 用户名 密码 会话ID 指挥官智能体ID 执行者智能体ID")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    conversation_id = int(sys.argv[3])
    commander_agent_id = sys.argv[4]
    executor_agent_id = sys.argv[5]

    token = login(username, password)
    print("执行者已登录，开始监听指挥官指令...")

    last_message_id = 0
    initial_messages = get_new_messages(token, conversation_id, 0)
    if initial_messages:
        last_message_id = max(msg["id"] for msg in initial_messages)
    print(f"当前最新消息ID: {last_message_id}")

    while True:
        new_messages = get_new_messages(token, conversation_id, last_message_id)
        for msg in new_messages:
            last_message_id = max(last_message_id, msg["id"])
            if msg.get("sender_agent_id") == commander_agent_id:
                command = msg["content"].strip()
                print(f"收到指挥官指令: {command}")
                output, status, duration_ms = execute_command(command)
                # 先以执行者身份回复
                send_reply(token, conversation_id, output, executor_agent_id)
                # 再报告给工作模式后端，生成日志和助手通知
                report_work_result(token, conversation_id, command, output, status, duration_ms, executor_agent_id)
                print(f"已执行并回复，状态: {status}")
        time.sleep(3)

import requests
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

def execute_work(token, conversation_id, command):
    resp = requests.post(
        f"{BASE_URL}/work/execute",
        json={
            "conversation_id": conversation_id,
            "command": command,
            "sender_agent_id": None,
            "timeout": 30
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code != 200:
        print("错误:", resp.status_code, resp.text)
        return
    data = resp.json()
    print("日志ID:", data.get("log_id"))
    print("状态:", data.get("status"))
    print("耗时(ms):", data.get("duration_ms"))
    print("输出:")
    print(data.get("output", ""))

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python test_work.py 用户名 密码 会话ID")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    conversation_id = int(sys.argv[3])

    token = login(username, password)
    print("登录成功，正在执行工作命令...")
    execute_work(token, conversation_id, "echo hello")

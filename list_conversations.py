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

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python list_conversations.py 用户名 密码")
        sys.exit(1)

    token = login(sys.argv[1], sys.argv[2])
    resp = requests.get(
        f"{BASE_URL}/messages/conversations",
        headers={"Authorization": f"Bearer {token}"}
    )
    data = resp.json()
    conversations = data.get("conversations", [])
    print("会话列表：")
    for c in conversations:
        print(f"ID: {c['id']} | 标题: {c['title']} | 智能体ID: {c.get('agent_id') or '无'}")

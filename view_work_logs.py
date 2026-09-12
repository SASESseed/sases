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
        print("用法: python view_work_logs.py 用户名 密码")
        sys.exit(1)

    token = login(sys.argv[1], sys.argv[2])
    resp = requests.get(
        f"{BASE_URL}/work/logs?limit=20",
        headers={"Authorization": f"Bearer {token}"}
    )
    logs = resp.json().get("logs", [])
    print("最近工作日志：")
    for log in logs:
        print(f"---")
        print(f"ID: {log['id']} | 状态: {log['status']} | 耗时: {log.get('duration_ms')}ms")
        print(f"命令: {log['command']}")
        print(f"输出: {log.get('output', '')[:200]}...")
        print(f"时间: {log.get('created_at')}")

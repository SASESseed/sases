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

def test_summarize(token, hours=1):
    resp = requests.post(
        f"{BASE_URL}/work/summarize",
        params={"hours": hours},
        headers={"Authorization": f"Bearer {token}"}
    )
    print("状态码:", resp.status_code)
    try:
        data = resp.json()
        print("响应:", data)
    except:
        print("响应文本:", resp.text)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python test_summarize.py 用户名 密码")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    token = login(username, password)
    print("登录成功，正在触发总结...")
    test_summarize(token, hours=1)

# test_group.py
import urllib.request
import urllib.parse
import json

BASE = "http://127.0.0.1:8001"

def login(username, password):
    data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(f"{BASE}/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def create_group(token, name, mode):
    url = f"{BASE}/group/create?name={urllib.parse.quote(name)}&mode={mode}"
    req = urllib.request.Request(url, method="POST", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

if __name__ == "__main__":
    # 使用测试账号，密码请根据实际修改
    token_data = login("test", "123456")
    token = token_data.get("access_token") or token_data.get("token")
    print("登录成功，token：", token[:20] + "...")
    result = create_group(token, "test_group", "cooperative")
    print("创建群组结果：", result)

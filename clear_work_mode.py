import requests
import sys
import os
import shutil

BASE_URL = "http://127.0.0.1:8001"

def login(username, password):
    resp = requests.post(
        f"{BASE_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def list_conversations(token):
    resp = requests.get(
        f"{BASE_URL}/messages/conversations",
        headers={"Authorization": f"Bearer {token}"}
    )
    resp.raise_for_status()
    return resp.json().get("conversations", [])

def delete_conversation(token, conversation_id):
    resp = requests.delete(
        f"{BASE_URL}/messages/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.status_code == 200

def clear_database_tables(username, password):
    """手动清理工作日志和记忆表（直接通过 API 不可行，这里提示使用 SQLite 或脚本）"""
    # 该函数预留，实际清理通过本地脚本删除 DB 文件或使用 SQLite 命令
    pass

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python clear_work_mode.py 用户名 密码")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    token = login(username, password)
    conversations = list_conversations(token)
    print(f"找到 {len(conversations)} 个会话，准备删除...")

    for conv in conversations:
        conv_id = conv["id"]
        title = conv.get("title", "未知")
        print(f"正在删除会话 ID {conv_id}：{title}")
        if delete_conversation(token, conv_id):
            print("  删除成功")
        else:
            print("  删除失败")

    print("所有会话已删除。")

    # 删除自动生成的 Harness 模块目录
    harness_dir = os.path.join(os.path.dirname(__file__), "harness_modules")
    if os.path.exists(harness_dir):
        deleted_auto = 0
        for item in os.listdir(harness_dir):
            if item.startswith("auto_"):
                item_path = os.path.join(harness_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    deleted_auto += 1
        print(f"已删除 {deleted_auto} 个自动生成的 Harness 模块。")
    else:
        print("harness_modules 目录不存在。")

    print("清理完成。")

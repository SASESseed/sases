# add_admin_field.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查并添加 is_admin 字段
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'is_admin' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        print("已添加 is_admin 字段")
    else:
        print("is_admin 字段已存在")

    # 将 ID=1 的账号设为管理员
    cursor.execute("UPDATE users SET is_admin=1 WHERE id=1")
    conn.commit()
    print("已将用户 ID=1 设置为管理员")

    # 查询当前所有管理员
    cursor.execute("SELECT id, username FROM users WHERE is_admin=1")
    admins = cursor.fetchall()
    print("当前管理员：", admins if admins else "无")

    conn.close()

if __name__ == '__main__':
    main()

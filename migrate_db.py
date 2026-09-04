# migrate_db.py
import sqlite3
import os
import secrets
import string

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def generate_sases_id():
    alphabet = string.ascii_lowercase + string.digits
    return "sases_" + ''.join(secrets.choice(alphabet) for _ in range(8))

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 检查 users 表是否存在
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cur.fetchone():
        print("users 表不存在，请先启动应用初始化数据库")
        return

    # 检查 sases_id 列是否存在
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if 'sases_id' not in columns:
        print("添加 sases_id 列（不带 UNIQUE）...")
        cur.execute("ALTER TABLE users ADD COLUMN sases_id TEXT")
    else:
        print("sases_id 列已存在")

    # 创建唯一索引（若不存在）
    print("创建/更新唯一索引...")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_sases_id ON users(sases_id)")

    # 为已有用户填充 sases_id
    cur.execute("SELECT id, sases_id FROM users WHERE sases_id IS NULL")
    rows = cur.fetchall()
    for user_id, _ in rows:
        new_id = generate_sases_id()
        cur.execute("UPDATE users SET sases_id=? WHERE id=?", (new_id, user_id))
        print(f"用户 ID {user_id} 生成 sases_id: {new_id}")

    conn.commit()
    conn.close()
    print("迁移完成")

if __name__ == '__main__':
    main()

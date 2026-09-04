# core/db.py
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'users.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_db():
    return get_connection()

@contextmanager
def db_cursor(commit=False):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    finally:
        conn.close()

def _ensure_column(cur, table: str, column: str, definition: str):
    if "CURRENT_TIMESTAMP" in definition.upper():
        definition = definition.replace("CURRENT_TIMESTAMP", "NULL")
    cur.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cur.fetchall()]
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    with db_cursor(commit=True) as cur:
        # 用户表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                sases_id TEXT,
                credits REAL DEFAULT 0,
                gender TEXT,
                region TEXT,
                signature TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _ensure_column(cur, "users", "sases_id", "TEXT")
        _ensure_column(cur, "users", "credits", "REAL DEFAULT 0")
        _ensure_column(cur, "users", "gender", "TEXT")
        _ensure_column(cur, "users", "region", "TEXT")
        _ensure_column(cur, "users", "signature", "TEXT")

        # API Key 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 知识库表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                branch_a TEXT,
                branch_b TEXT,
                solution TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 贡献日志表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contribution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT,
                event_type TEXT DEFAULT 'manual',
                points REAL DEFAULT 0,
                model_source TEXT DEFAULT 'api',
                model_id TEXT,
                detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "contribution_log", "action", "TEXT")
        _ensure_column(cur, "contribution_log", "event_type", "TEXT DEFAULT 'manual'")
        _ensure_column(cur, "contribution_log", "points", "REAL DEFAULT 0")
        _ensure_column(cur, "contribution_log", "model_source", "TEXT DEFAULT 'api'")
        _ensure_column(cur, "contribution_log", "model_id", "TEXT")
        _ensure_column(cur, "contribution_log", "detail", "TEXT")
        _ensure_column(cur, "contribution_log", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

        # 模型配置表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS model_configs (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                model_type TEXT NOT NULL,
                name TEXT NOT NULL,
                provider TEXT,
                api_key_encrypted TEXT,
                node_url TEXT,
                model_name TEXT,
                capabilities TEXT,
                is_shared INTEGER DEFAULT 0,
                visibility TEXT DEFAULT 'private',
                price REAL DEFAULT 1.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 会话表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                agent_id TEXT,
                title TEXT DEFAULT '新会话',
                unread_count INTEGER DEFAULT 0,
                is_pinned INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "conversations", "unread_count", "INTEGER DEFAULT 0")
        _ensure_column(cur, "conversations", "is_pinned", "INTEGER DEFAULT 0")

        # 消息表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                sender_agent_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        _ensure_column(cur, "messages", "sender_agent_id", "TEXT")

        # 好友关系表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                friend_agent_id TEXT NOT NULL,
                target_user_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (target_user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "agent_friendships", "target_user_id", "INTEGER")

        # 群组表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        """)

        # 群成员表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER,
                agent_id TEXT,
                role TEXT DEFAULT 'member',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "group_members", "agent_id", "TEXT")

        # 群聊消息表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                sender_id INTEGER,
                sender_agent_id TEXT,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(id),
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "group_messages", "sender_agent_id", "TEXT")

        # 交易市场订单表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_type TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'open',
                accepted_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (accepted_by) REFERENCES users(id)
            )
        """)

        # AI 圈帖子表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ai_circle_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                owner_user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                post_type TEXT DEFAULT 'daily',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id)
            )
        """)

        # 交易表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                tx_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        """)

        # 种子任务表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS seed_tasks (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                domain TEXT,
                difficulty TEXT DEFAULT 'medium',
                user_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")

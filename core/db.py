import sqlite3
from core import config

DB_FILE = config.DB_FILE

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # 用户表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            credits INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # 积分流水
        conn.execute("""
        CREATE TABLE IF NOT EXISTS credit_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        # 系统消息
        conn.execute("""
        CREATE TABLE IF NOT EXISTS system_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'SASES助手',
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        # 通用用户设置
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (user_id, key),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        # API Key 管理
        conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            encrypted_key TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        # 知识库表（新增）
        conn.execute("""
        CREATE TABLE IF NOT EXISTS kb_entries (
            id TEXT PRIMARY KEY,
            task TEXT,
            branch_a TEXT,
            branch_b TEXT,
            solution TEXT,
            verified INTEGER DEFAULT 0,
            model_id TEXT,
            user_id TEXT,
            timestamp TEXT,
            backtrack_count INTEGER DEFAULT 0,
            test_cases TEXT
        )
        """)
        # 为已有表添加可能缺失的字段（兼容旧库）
        for col, dtype in [
            ("state_hash", "TEXT DEFAULT ''"),
            ("last_sync_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("tampered_flag", "INTEGER DEFAULT 0"),
            ("auto_pollinate_enabled", "INTEGER DEFAULT 1"),
            ("is_admin", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {dtype}")
            except sqlite3.OperationalError:
                pass
        # 贡献日志表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contribution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            target_id TEXT,
            metadata TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # 添加贡献日志索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contrib_user ON contribution_log(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contrib_event ON contribution_log(event_type)")

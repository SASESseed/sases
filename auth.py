import sqlite3, os, json, time
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

DB_FILE = "users.db"
SECRET_KEY = os.environ.get("SASES_SECRET_KEY", "sases-dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1天

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
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
        # 预留防篡改字段
        try:
            conn.execute("ALTER TABLE users ADD COLUMN state_hash TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN tampered_flag INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        # 自动授粉开关字段
        try:
            conn.execute("ALTER TABLE users ADD COLUMN auto_pollinate_enabled INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        # 管理员字段
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

def create_user(username: str, email: str, password: str):
    with get_db() as conn:
        try:
            hash = pwd_context.hash(password)
            conn.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                         (username, email, hash))
            return True, "注册成功"
        except sqlite3.IntegrityError:
            return False, "用户名或邮箱已存在"

def authenticate_user(username: str, password: str):
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and pwd_context.verify(password, user["password_hash"]):
            return user
    return None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_id(user_id: int):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

def add_credits(user_id: int, amount: int, reason: str = ""):
    with get_db() as conn:
        conn.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, user_id))
        conn.execute("INSERT INTO credit_ledger (user_id, amount, reason) VALUES (?, ?, ?)",
                     (user_id, amount, reason))

def deduct_credits(user_id: int, amount: int, reason: str = ""):
    """扣除用户积分。返回 (成功布尔, 错误消息)。"""
    with get_db() as conn:
        user = conn.execute("SELECT credits FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "用户不存在"
        if user["credits"] < amount:
            return False, "积分不足"
        conn.execute("UPDATE users SET credits = credits - ? WHERE id = ?", (amount, user_id))
        conn.execute("INSERT INTO credit_ledger (user_id, amount, reason) VALUES (?, ?, ?)",
                     (user_id, -amount, reason))
        return True, "扣除成功"

def get_leaderboard(top_n=10):
    with get_db() as conn:
        rows = conn.execute("SELECT username, credits FROM users ORDER BY credits DESC LIMIT ?", (top_n,)).fetchall()
        return [{"username": r["username"], "credits": r["credits"]} for r in rows]

def get_credit_ledger(user_id: int, limit: int = 20):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT amount, reason, timestamp FROM credit_ledger WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [{"amount": r["amount"], "reason": r["reason"], "timestamp": r["timestamp"]} for r in rows]

# ========== 系统消息（SASES助手） ==========
def add_system_message(user_id: int, content: str, title: str = "SASES助手"):
    """向用户发送系统消息。"""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO system_messages (user_id, title, content) VALUES (?, ?, ?)",
            (user_id, title, content)
        )

def get_system_messages(user_id: int, limit: int = 50):
    """获取用户系统消息，返回未读数量。"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, content, is_read, timestamp FROM system_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        messages = [{
            "id": r["id"],
            "title": r["title"],
            "content": r["content"],
            "is_read": r["is_read"],
            "timestamp": r["timestamp"]
        } for r in rows]
        unread_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM system_messages WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()["cnt"]
        return messages, unread_count

def mark_messages_read(user_id: int):
    """标记所有消息为已读。"""
    with get_db() as conn:
        conn.execute(
            "UPDATE system_messages SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (user_id,)
        )

# ========== 授粉设置 ==========
def get_user_settings(user_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT auto_pollinate_enabled FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if row:
            return {"auto_pollinate_enabled": bool(row["auto_pollinate_enabled"])}
        return None

def update_user_settings(user_id: int, auto_pollinate_enabled: bool):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET auto_pollinate_enabled = ? WHERE id = ?",
            (1 if auto_pollinate_enabled else 0, user_id)
        )
        return True

# ========== 管理员 ==========
def is_admin(user_id: int) -> bool:
    """检查用户是否为管理员。"""
    with get_db() as conn:
        row = conn.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        if row and row["is_admin"] == 1:
            return True
        return False

def set_admin(user_id: int, admin: bool = True):
    """设置或取消用户的管理员身份。"""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET is_admin = ? WHERE id = ?",
            (1 if admin else 0, user_id)
        )
        return True

# ========== 防篡改锚点（预留） ==========
def generate_state_signature(user_id: int):
    """预留：未来对用户状态生成签名。当前返回空字符串。"""
    return ""

def verify_state_signature(user_id: int, signature: str):
    """预留：未来验证用户提交的签名。当前始终返回 True。"""
    return True

def log_tamper_event(user_id: int, detail: str):
    """预留：未来记录篡改事件。当前只写入本地文件，不参与业务。"""
    entry = {
        "user_id": user_id,
        "detail": detail,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open("tamper_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# 初始化数据库
init_db()

import sqlite3, os, json, time, hmac, hashlib
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

DB_FILE = "users.db"
SECRET_KEY = os.environ.get("SASES_SECRET_KEY", "sases-dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1天

# 状态签名密钥文件
SIGN_KEY_FILE = "secret_key.bin"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _load_or_create_sign_key():
    """加载或创建 HMAC 签名密钥。"""
    if os.path.exists(SIGN_KEY_FILE):
        with open(SIGN_KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = os.urandom(32)
        with open(SIGN_KEY_FILE, "wb") as f:
            f.write(key)
        return key

SIGN_KEY = _load_or_create_sign_key()

def sign_state(user_id: int, credits: int) -> str:
    """对用户积分状态生成 HMAC 签名。"""
    message = f"{user_id}:{credits}".encode()
    return hmac.new(SIGN_KEY, message, hashlib.sha256).hexdigest()

def verify_state(user_id: int, credits: int, signature: str) -> bool:
    """验证用户积分状态签名是否有效。"""
    expected = sign_state(user_id, credits)
    return hmac.compare_digest(expected, signature)

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
            # 为新用户生成初始状态签名
            user = conn.execute("SELECT id, credits FROM users WHERE username = ?", (username,)).fetchone()
            if user:
                conn.execute("UPDATE users SET state_hash = ? WHERE id = ?",
                             (sign_state(user["id"], user["credits"]), user["id"]))
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

def _update_state_hash(user_id: int):
    """根据当前积分更新用户状态哈希。"""
    with get_db() as conn:
        user = conn.execute("SELECT credits FROM users WHERE id = ?", (user_id,)).fetchone()
        if user:
            new_hash = sign_state(user_id, user["credits"])
            conn.execute("UPDATE users SET state_hash = ? WHERE id = ?", (new_hash, user_id))
            return True
        return False

def add_credits(user_id: int, amount: int, reason: str = ""):
    with get_db() as conn:
        conn.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, user_id))
        conn.execute("INSERT INTO credit_ledger (user_id, amount, reason) VALUES (?, ?, ?)",
                     (user_id, amount, reason))
    # 更新状态签名
    _update_state_hash(user_id)

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
    # 更新状态签名
    _update_state_hash(user_id)
    return True, "扣除成功"

def verify_user_integrity(user_id: int) -> bool:
    """检查用户积分与状态哈希是否匹配。"""
    with get_db() as conn:
        user = conn.execute("SELECT credits, state_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False
        return verify_state(user_id, user["credits"], user["state_hash"])

def check_all_users_integrity():
    """扫描所有用户，返回积分被篡改的用户ID列表。"""
    tampered = []
    with get_db() as conn:
        users = conn.execute("SELECT id, credits, state_hash FROM users").fetchall()
        for u in users:
            if not verify_state(u["id"], u["credits"], u["state_hash"]):
                tampered.append(u["id"])
    return tampered

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
    with get_db() as conn:
        conn.execute(
            "INSERT INTO system_messages (user_id, title, content) VALUES (?, ?, ?)",
            (user_id, title, content)
        )

def get_system_messages(user_id: int, limit: int = 50):
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
    with get_db() as conn:
        row = conn.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        if row and row["is_admin"] == 1:
            return True
        return False

def set_admin(user_id: int, admin: bool = True):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET is_admin = ? WHERE id = ?",
            (1 if admin else 0, user_id)
        )
        return True

# ========== 防篡改锚点（预留） ==========
def generate_state_signature(user_id: int):
    """返回当前用户状态签名。"""
    user = get_user_by_id(user_id)
    if user:
        return sign_state(user_id, user["credits"])
    return ""

def verify_state_signature(user_id: int, signature: str):
    """验证用户提交的签名是否与当前状态一致。"""
    user = get_user_by_id(user_id)
    if not user:
        return False
    return verify_state(user_id, user["credits"], signature)

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

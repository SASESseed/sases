import os
import json
import time
import hmac
import hashlib
from datetime import datetime, timedelta

from passlib.context import CryptContext
from jose import JWTError, jwt

from core import config
from core.db import get_db, init_db

SECRET_KEY = config.SASES_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
SIGN_KEY_FILE = config.SIGN_KEY_FILE

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _load_or_create_sign_key():
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
    message = f"{user_id}:{credits}".encode()
    return hmac.new(SIGN_KEY, message, hashlib.sha256).hexdigest()

def verify_state(user_id: int, credits: int, signature: str) -> bool:
    expected = sign_state(user_id, credits)
    return hmac.compare_digest(expected, signature)

def create_user(username: str, email: str, password: str):
    with get_db() as conn:
        try:
            hash = pwd_context.hash(password)
            conn.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                         (username, email, hash))
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
    _update_state_hash(user_id)

def deduct_credits(user_id: int, amount: int, reason: str = "") -> tuple:
    if amount <= 0:
        return False, "扣减金额必须大于0"
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE users SET credits = credits - ? WHERE id = ? AND credits >= ?",
            (amount, user_id, amount)
        )
        if cur.rowcount == 0:
            return False, "积分不足"
        conn.execute("INSERT INTO credit_ledger (user_id, amount, reason) VALUES (?, ?, ?)",
                     (user_id, -amount, reason))
    _update_state_hash(user_id)
    return True, "扣除成功"

def verify_user_integrity(user_id: int) -> bool:
    with get_db() as conn:
        user = conn.execute("SELECT credits, state_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False
        return verify_state(user_id, user["credits"], user["state_hash"])

def check_all_users_integrity():
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

# ========== 通用用户设置 ==========
def get_all_user_settings(user_id: int) -> dict:
    settings = {}
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM user_settings WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        for r in rows:
            try:
                settings[r["key"]] = json.loads(r["value"])
            except:
                settings[r["key"]] = r["value"]
    user = get_user_by_id(user_id)
    if user:
        settings["auto_pollinate_enabled"] = bool(user["auto_pollinate_enabled"])
    return settings

def update_all_user_settings(user_id: int, settings: dict) -> dict:
    with get_db() as conn:
        if "auto_pollinate_enabled" in settings:
            val = settings.pop("auto_pollinate_enabled")
            conn.execute(
                "UPDATE users SET auto_pollinate_enabled = ? WHERE id = ?",
                (1 if val else 0, user_id)
            )
        for key, value in settings.items():
            conn.execute("""
                INSERT INTO user_settings (user_id, key, value) VALUES (?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value
            """, (user_id, key, json.dumps(value, ensure_ascii=False)))
    return get_all_user_settings(user_id)

def export_kb():
    kb_file = config.KB_FILE
    if not os.path.exists(kb_file):
        return []
    with open(kb_file, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

# 兼容旧函数
def get_user_settings(user_id: int):
    return get_all_user_settings(user_id)

def update_user_settings(user_id: int, auto_pollinate_enabled: bool):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET auto_pollinate_enabled = ? WHERE id = ?",
            (1 if auto_pollinate_enabled else 0, user_id)
        )
        return True

# ========== API Key 管理 ==========
def add_api_key(user_id: int, provider: str, key: str, priority: int = 0) -> bool:
    from core.encryption import encrypt_text
    encrypted = encrypt_text(key)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE api_keys SET encrypted_key = ?, priority = ?, is_active = 1 WHERE id = ?",
                (encrypted, priority, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO api_keys (user_id, provider, encrypted_key, priority) VALUES (?, ?, ?, ?)",
                (user_id, provider, encrypted, priority)
            )
    return True

def list_api_keys(user_id: int) -> list:
    keys = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, provider, encrypted_key, priority, is_active FROM api_keys WHERE user_id = ? ORDER BY priority DESC",
            (user_id,)
        ).fetchall()
        for r in rows:
            keys.append({
                "id": r["id"],
                "provider": r["provider"],
                "masked_key": "****" + (r["encrypted_key"][-4:] if r["encrypted_key"] else ""),
                "priority": r["priority"],
                "is_active": r["is_active"]
            })
    return keys

def delete_api_key(user_id: int, key_id: int) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
    return True

def set_api_key_priority(user_id: int, key_id: int, priority: int) -> bool:
    with get_db() as conn:
        conn.execute("UPDATE api_keys SET priority = ? WHERE id = ? AND user_id = ?", (priority, key_id, user_id))
    return True

def get_active_api_keys(user_id: int) -> list:
    from core.encryption import decrypt_text
    result = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT provider, encrypted_key, priority FROM api_keys WHERE user_id = ? AND is_active = 1 ORDER BY priority DESC",
            (user_id,)
        ).fetchall()
        for r in rows:
            key = decrypt_text(r["encrypted_key"])
            if key:
                result.append({"provider": r["provider"], "key": key, "priority": r["priority"]})
    return result

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

# ========== 防篡改锚点 ==========
def generate_state_signature(user_id: int):
    user = get_user_by_id(user_id)
    if user:
        return sign_state(user_id, user["credits"])
    return ""

def verify_state_signature(user_id: int, signature: str):
    user = get_user_by_id(user_id)
    if not user:
        return False
    return verify_state(user_id, user["credits"], signature)

def log_tamper_event(user_id: int, detail: str):
    entry = {
        "user_id": user_id,
        "detail": detail,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open("tamper_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# 初始化数据库
init_db()

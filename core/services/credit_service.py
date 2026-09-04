# core/services/credit_service.py
from ..db import db_cursor


def get_balance(user_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT credits FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()
    if not user:
        return None
    return user["credits"] or 0


def get_history(user_id: int, limit: int = 50):
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, action, event_type, points, model_source, detail, created_at
            FROM contribution_log
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def add_credit(user_id: int, amount: float, action: str = "手动调整", detail: str = "", event_type: str = "manual"):
    """增加积分（或负数扣减），并写入日志"""
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE users SET credits = credits + ? WHERE id=?", (amount, user_id))
        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, action, event_type, amount, detail))
    return True

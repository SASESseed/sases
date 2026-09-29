from datetime import datetime
from typing import Optional
from ...db import db_cursor

# ========== 工具函数 ==========

def pick_swarm_agents(user_id: int) -> tuple:
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, name FROM model_configs WHERE user_id=? ORDER BY id ASC",
            (user_id,)
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return None, None

    commander_id = None
    executor_id = None

    for r in rows:
        name = (r.get("name") or "").lower()
        if commander_id is None and ("指挥" in name or "commander" in name):
            commander_id = r["id"]
        if executor_id is None and ("执行" in name or "executor" in name):
            executor_id = r["id"]

    if commander_id is None:
        commander_id = rows[0]["id"]
    if executor_id is None:
        if len(rows) >= 2:
            for r in rows:
                if r["id"] != commander_id:
                    executor_id = r["id"]
                    break
            if executor_id is None:
                executor_id = commander_id
        else:
            executor_id = commander_id

    return commander_id, executor_id


def _get_conversation_history(conversation_id: int, limit: int = 10) -> str:
    if not conversation_id:
        return ""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT sender, content, sender_agent_id
            FROM messages
            WHERE conversation_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, limit)
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return ""

    rows.reverse()

    lines = []
    for r in rows:
        content = (r.get("content") or "").strip()
        if content.startswith("[TASK]:") or content.startswith("[STEP_DONE]:"):
            continue
        if content.startswith("[RETRY_TASK]:"):
            continue
        if content.startswith("[TASK_DRAFT]:"):
            continue
        if not content:
            continue
        if len(content) > 200:
            content = content[:200] + "..."

        sender = r.get("sender", "?")
        if sender == "user":
            who = "用户"
        else:
            who = "AI"
        lines.append(f"{who}: {content}")

    if not lines:
        return ""

    return "\n".join(lines[-limit:])


def _insert_message(conversation_id: int, content: str, sender_agent_id: Optional[str] = None):
    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
                (conversation_id, content, sender_agent_id)
            )
        else:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'user', ?)",
                (conversation_id, content)
            )
        cur.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (datetime.now().isoformat(), conversation_id)
        )
        return cur.lastrowid

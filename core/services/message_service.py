# core/services/message_service.py
import base64
import json
import httpx
from datetime import datetime
from typing import Optional
from ..db import db_cursor
from ..security import decrypt_api_key, normalize_provider
from . import work_service

# ---------- 会话相关 ----------

def list_conversations(user_id: int):
    with db_cursor() as cur:
        cur.execute("""
            SELECT c.id, c.title, c.agent_id, c.updated_at, c.unread_count, c.is_pinned,
                   (SELECT content FROM messages WHERE conversation_id=c.id ORDER BY id DESC LIMIT 1) as last_message,
                   (SELECT sender FROM messages WHERE conversation_id=c.id ORDER BY id DESC LIMIT 1) as last_sender,
                   (SELECT sender_agent_id FROM messages WHERE conversation_id=c.id ORDER BY id DESC LIMIT 1) as last_sender_agent_id
            FROM conversations c
            WHERE c.user_id=?
            ORDER BY c.is_pinned DESC, c.updated_at DESC
        """, (user_id,))
        rows = cur.fetchall()

    conversations = []
    for row in rows:
        row = dict(row)
        if row.get("last_sender_agent_id"):
            with db_cursor() as cur2:
                cur2.execute("SELECT name FROM model_configs WHERE id=?", (row["last_sender_agent_id"],))
                agent = cur2.fetchone()
                row["last_sender_name"] = agent["name"] if agent else "智能体"
        else:
            row["last_sender_name"] = "我" if row.get("last_sender") == "user" else "AI"
        conversations.append(row)

    return conversations

def create_conversation(user_id: int, agent_id: str = None, title: str = "新会话"):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO conversations (user_id, agent_id, title)
            VALUES (?, ?, ?)
        """, (user_id, agent_id, title))
        return cur.lastrowid

def get_messages(user_id: int, conversation_id: int, limit: int = 50, offset: int = 0, after_id: Optional[int] = None):
    with db_cursor() as cur:
        cur.execute("SELECT id FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))
        if not cur.fetchone():
            return None

        query = """
            SELECT m.id, m.sender, m.content, m.sender_agent_id, m.created_at,
                   CASE WHEN m.sender_agent_id IS NOT NULL THEN mc.name
                        WHEN m.sender = 'user' THEN '我'
                        ELSE 'AI' END as sender_name
            FROM messages m
            LEFT JOIN model_configs mc ON m.sender_agent_id = mc.id
            WHERE m.conversation_id=?
        """
        params = [conversation_id]

        if after_id is not None:
            query += " AND m.id > ?"
            params.append(after_id)

        query += " ORDER BY m.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

    messages = [dict(row) for row in rows]
    messages.reverse()
    return messages

def mark_conversation_read(user_id: int, conversation_id: int):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE conversations SET unread_count=0 WHERE id=? AND user_id=?", (conversation_id, user_id))
    return True

def toggle_pin_conversation(user_id: int, conversation_id: int, pinned: bool):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE conversations SET is_pinned=? WHERE id=? AND user_id=?", (1 if pinned else 0, conversation_id, user_id))
    return True

def delete_conversation(user_id: int, conversation_id: int):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
        cur.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))
    return True

# ---------- 模型调用 ----------

async def call_model_with_config(model_config: dict, query: str) -> str:
    try:
        if model_config["model_type"] == "api":
            provider = normalize_provider(model_config["provider"])
            api_key = decrypt_api_key(model_config["api_key_encrypted"])
            if not api_key:
                raise Exception("API Key 解密失败")

            if provider == "deepseek":
                api_base = "https://api.deepseek.com/v1"
                model_name = "deepseek-chat"
            elif provider == "moonshot":
                api_base = "https://api.moonshot.cn/v1"
                model_name = "moonshot-v1-8k"
            elif provider == "openai":
                api_base = "https://api.openai.com/v1"
                model_name = "gpt-3.5-turbo"
            else:
                raise Exception(f"不支持的供应商: {provider}")

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": [{"role": "user", "content": query}], "temperature": 0.7}
                )
                if resp.status_code != 200:
                    raise Exception(f"上游API错误 ({resp.status_code}): {resp.text}")
                data = resp.json()
                return data["choices"][0]["message"]["content"]

        elif model_config["model_type"] == "local":
            node_url = model_config["node_url"].rstrip("/")
            model_name = model_config["model_name"]
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{node_url}/api/generate",
                    json={"model": model_name, "prompt": query, "stream": False}
                )
                if resp.status_code != 200:
                    raise Exception(f"本地模型错误 ({resp.status_code}): {resp.text}")
                data = resp.json()
                return data.get("response", "")

        else:
            raise Exception("未知模型类型")
    except Exception as e:
        raise e

# ---------- 发送消息 ----------

async def send_message(
    user_id: int,
    conversation_id: int,
    agent_id: str,
    content: str,
    sender_agent_id: str = None,
    mode: str = "normal"
):
    print(f"[MSG_DEBUG] content={content!r} | mode={mode!r} | agent_id={agent_id!r}")

    # ========== 自然语言意图分流 ==========
    if (
        mode in ("normal", "free")
        and content
        and content.strip()
        and not content.startswith("[")
        and not content.startswith("执行：")
    ):
        try:
            from . import intent_service, swarm_service

            is_task = await intent_service.is_task_intent(content)
            print(f"[MSG_DEBUG] is_task={is_task}")

            if is_task:
                if not conversation_id:
                    title = "蜂群任务"
                    if agent_id:
                        with db_cursor() as cur:
                            cur.execute("SELECT name FROM model_configs WHERE id=?", (agent_id,))
                            row = cur.fetchone()
                            if row:
                                title = row["name"]
                    conversation_id = create_conversation(user_id, agent_id, title)

                plan_result = await swarm_service.plan_task(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    user_input=content
                )
                print(f"[MSG_DEBUG] plan_result={plan_result}")

                status = plan_result.get("status", "")
                if status == "planned":
                    reply = "已启动执行，请稍候…"
                elif status == "no_plan":
                    reply = "没有识别出可执行的命令。如果这不是任务，请点下方按钮。"
                elif status == "no_agent":
                    reply = "未找到可用智能体，请先在模型管理中创建。"
                else:
                    reply = "执行失败，请重试。"

                return {
                    "conversation_id": conversation_id,
                    "user_message": content,
                    "assistant_reply": reply,
                    "agent_id": agent_id,
                    "sender_agent_id": sender_agent_id,
                    "mode": mode,
                    "swarm": True,
                    "swarm_status": status,
                    "task_id": plan_result.get("task_id")
                }
        except Exception as e:
            import traceback
            print(f"[MSG_DEBUG] 分流异常: {e}")
            traceback.print_exc()

    # ========== 蜂群模式：执行者汇报 [STEP_DONE] ==========
    if content.startswith("[STEP_DONE]:") and sender_agent_id:
        try:
            step_payload = json.loads(content[len("[STEP_DONE]:"):])
        except json.JSONDecodeError:
            return {"status": "error", "message": "步骤汇报格式错误"}

        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
                (conversation_id, content, sender_agent_id)
            )
            cur.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?",
                (datetime.now().isoformat(), conversation_id)
            )

        from . import swarm_service
        swarm_result = await swarm_service.handle_step_done(conversation_id, step_payload, sender_agent_id)

        return {
            "status": "step_received",
            "conversation_id": conversation_id,
            "sender_agent_id": sender_agent_id,
            "swarm": swarm_result
        }

    # ========== 自由模式下执行指令 ==========
    if mode == "free" and content.startswith("执行："):
        command = content.replace("执行：", "", 1).strip()
        if not command:
            return {
                "conversation_id": conversation_id,
                "user_message": content,
                "assistant_reply": "请提供要执行的命令",
                "agent_id": agent_id,
                "sender_agent_id": sender_agent_id,
                "mode": mode
            }
        try:
            work_result = await work_service.execute_work_command(
                user_id=user_id,
                conversation_id=conversation_id,
                command=command,
                sender_agent_id=sender_agent_id
            )
            return {
                "conversation_id": conversation_id,
                "user_message": content,
                "assistant_reply": work_result["output"],
                "agent_id": agent_id,
                "sender_agent_id": sender_agent_id,
                "mode": mode,
                "work_result": work_result
            }
        except Exception as e:
            return {
                "conversation_id": conversation_id,
                "user_message": content,
                "assistant_reply": f"指令执行失败：{str(e)}",
                "agent_id": agent_id,
                "sender_agent_id": sender_agent_id,
                "mode": mode
            }

    # ========== 蜂群模式在单聊中不支持 ==========
    if mode == "swarm":
        return {
            "conversation_id": conversation_id,
            "user_message": content,
            "assistant_reply": "蜂群模式仅在群聊中可用，请切换到群聊或使用其他模式。",
            "agent_id": agent_id,
            "sender_agent_id": sender_agent_id,
            "mode": mode
        }

    # ========== 普通模式或自由模式下的普通消息 ==========
    if not conversation_id:
        title = "新会话"
        if agent_id:
            with db_cursor() as cur:
                cur.execute("SELECT name FROM model_configs WHERE id=?", (agent_id,))
                row = cur.fetchone()
                if row:
                    title = row["name"]
        conversation_id = create_conversation(user_id, agent_id, title)

    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'user', ?, ?)",
                        (conversation_id, content, sender_agent_id))
        else:
            cur.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'user', ?)",
                        (conversation_id, content))
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))

    if agent_id:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM model_configs WHERE id=? AND user_id=?", (agent_id, user_id))
            model_row = cur.fetchone()
        if not model_row:
            assistant_reply = "错误：找不到绑定的智能体模型"
        else:
            model_config = dict(model_row)
            try:
                assistant_reply = await call_model_with_config(model_config, content)
            except Exception as e:
                assistant_reply = f"模型调用失败：{str(e)}"
    else:
        assistant_reply = "请先在“我的→模型管理”中配置模型，或从智能体页面发起对话"

    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'assistant', ?)",
                    (conversation_id, assistant_reply))
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))

    return {
        "conversation_id": conversation_id,
        "user_message": content,
        "assistant_reply": assistant_reply,
        "agent_id": agent_id,
        "sender_agent_id": sender_agent_id,
        "mode": mode
    }

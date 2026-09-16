# core/services/swarm_service.py
import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

import openai

from .. import config
from ..db import db_cursor

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=40,
    max_retries=2
)

MODEL = config.MODEL_NAME

COMMANDER_SYSTEM_PROMPT = """你是 SASES 指挥官。用户会给你一个任务，你需要拆解为可执行的 Windows CMD 命令序列。

【工作目录】
命令在项目根目录 C:\\Users\\xiaomai\\sases 下执行。

【规则】
1. 每个命令必须是单行的 Windows CMD 命令
2. 最多 5 步
3. 只输出 JSON 数组，格式：[{"step":1,"description":"...","command":"..."},...]
4. 不要输出任何其他文字，不要用 markdown 代码块
5. 禁止 uvicorn 等服务器启停命令
6. 如果任务模糊，输出：[{"step":1,"description":"任务模糊","command":"echo 请提供更具体的任务说明"}]

【跨步骤引用语法（重要）】
如果后续步骤需要用到前面步骤的输出，用占位符 {{stepN}} 引用。
例如：
[
  {"step": 1, "description": "定位文件", "command": "dir /s /b discover.js"},
  {"step": 2, "description": "在找到的文件里搜索", "command": "findstr /n \\"function\\" {{step1}}"}
]
执行器会自动把 {{step1}} 替换为第 1 步的第一行输出。

【常用命令】
- 列出目录：dir <路径>
- 查找文件：dir /s /b <文件名>
- 查看文件内容：type <文件路径>
- 在文件中搜索：findstr /n "关键词" <文件路径>
- 只显示文件名：dir /b
- 当前路径：cd
- 当前用户：whoami

【会话上下文】
你会看到"最近的会话历史"，其中包含之前任务的消息。**如果用户当前输入引用了之前的内容（如"这个文件"、"刚才那个目录"），请结合历史理解。**

【路径规则】
- 已知项目结构：static/modules/ 放前端 JS，core/ 放后端 Python
- 如果不知道文件路径，第 1 步用 dir /s /b 定位；第 2 步用 {{step1}} 引用定位结果
"""

SUMMARY_SYSTEM_PROMPT = """请根据用户任务和执行结果，用一句话总结这次任务的结果。直接输出总结，不要任何前缀。"""

_pending: Dict[str, Dict[str, Any]] = {}
_feedback_table_ready = False


def _ensure_feedback_table():
    global _feedback_table_ready
    if _feedback_table_ready:
        return
    with db_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS intent_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id TEXT,
                original_input TEXT NOT NULL,
                feedback_type TEXT NOT NULL DEFAULT 'false_positive',
                note TEXT,
                created_at TEXT NOT NULL
            )
        """)
    _feedback_table_ready = True


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
    """读取会话最近 N 条消息，格式化为文本上下文"""
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

    rows.reverse()  # 按时间正序

    lines = []
    for r in rows:
        content = (r.get("content") or "").strip()
        # 跳过协议消息
        if content.startswith("[TASK]:") or content.startswith("[STEP_DONE]:"):
            continue
        # 跳过空消息
        if not content:
            continue
        # 截断过长内容
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


async def _call_llm(prompt: str, system_prompt: str = "") -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=500
    )
    return resp.choices[0].message.content.strip()


def _parse_plan(raw: str) -> Optional[List[Dict[str, Any]]]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        steps = json.loads(raw[start:end+1])
        if not isinstance(steps, list) or not steps:
            return None
        return steps[:5]
    except json.JSONDecodeError:
        return None


async def plan_task(
    user_id: int,
    conversation_id: int,
    user_input: str,
    commander_id: str = None,
    executor_id: str = None,
    timeout: int = 30
) -> Dict[str, Any]:
    if not commander_id or not executor_id:
        auto_cmd, auto_exec = pick_swarm_agents(user_id)
        commander_id = commander_id or auto_cmd
        executor_id = executor_id or auto_exec

    if not commander_id:
        err_msg = "[SUMMARY]:未找到可用智能体，请先在模型管理中创建智能体。"
        _insert_message(conversation_id, err_msg, sender_agent_id=None)
        return {"status": "no_agent", "message": "用户没有可用智能体"}

    # 读取会话历史（在插入用户消息之前，避免包含自己）
    history_text = _get_conversation_history(conversation_id, limit=10)

    _insert_message(conversation_id, user_input, sender_agent_id=None)

    # 构造带上下文的 prompt
    if history_text:
        full_prompt = f"""【最近的会话历史】
{history_text}

【用户当前任务】
{user_input}

请根据上下文拆解为命令序列。"""
    else:
        full_prompt = user_input

    try:
        raw = await _call_llm(full_prompt, COMMANDER_SYSTEM_PROMPT)
    except Exception as e:
        err_msg = f"[SUMMARY]:任务拆解失败：{str(e)}"
        _insert_message(conversation_id, err_msg, sender_agent_id=commander_id)
        return {"status": "error", "message": str(e)}

    steps = _parse_plan(raw)
    if not steps:
        task_id = f"noplan_{int(time.time() * 1000)}"
        _pending[task_id] = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_text": user_input,
            "steps": [],
            "results": [],
            "done": set(),
            "commander_id": commander_id,
            "executor_id": executor_id,
            "created_at": datetime.now().isoformat(),
            "cancelled": True,
            "no_plan": True
        }
        return {
            "status": "no_plan",
            "message": "无法拆解任务",
            "task_id": task_id
        }

    task_id = f"t_{int(time.time() * 1000)}"
    _pending[task_id] = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "user_text": user_input,
        "steps": steps,
        "results": [],
        "done": set(),
        "commander_id": commander_id,
        "executor_id": executor_id,
        "created_at": datetime.now().isoformat(),
        "cancelled": False,
        "no_plan": False
    }

    task_payload = {"task_id": task_id, "steps": steps}
    task_msg = "[TASK]:" + json.dumps(task_payload, ensure_ascii=False)
    _insert_message(conversation_id, task_msg, sender_agent_id=commander_id)

    return {
        "status": "planned",
        "task_id": task_id,
        "steps": steps,
        "conversation_id": conversation_id,
        "commander_id": commander_id,
        "executor_id": executor_id
    }


def cancel_task(task_id: str, user_id: int) -> Dict[str, Any]:
    if task_id not in _pending:
        return {"status": "not_found", "message": "任务不存在或已完成"}

    task = _pending[task_id]
    if task["user_id"] != user_id:
        return {"status": "forbidden", "message": "无权取消该任务"}

    if task.get("no_plan"):
        del _pending[task_id]
        return {"status": "cancelled", "task_id": task_id}

    task["cancelled"] = True
    cancel_msg = f"[SUMMARY]:任务已取消。"
    _insert_message(task["conversation_id"], cancel_msg, sender_agent_id=task["commander_id"])
    return {"status": "cancelled", "task_id": task_id}


def submit_feedback(
    user_id: int,
    task_id: str = None,
    original_input: str = "",
    feedback_type: str = "false_positive",
    note: str = ""
) -> Dict[str, Any]:
    _ensure_feedback_table()

    if (not original_input) and task_id and task_id in _pending:
        original_input = _pending[task_id].get("user_text", "")

    if task_id and task_id in _pending and _pending[task_id]["user_id"] == user_id:
        task = _pending[task_id]
        task["cancelled"] = True
        if not task.get("no_plan"):
            conv_id = task["conversation_id"]
            cmd_id = task["commander_id"]
            cancel_msg = "[SUMMARY]:已取消，并记录为误判。"
            _insert_message(conv_id, cancel_msg, sender_agent_id=cmd_id)
        del _pending[task_id]

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO intent_feedback (user_id, task_id, original_input, feedback_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, task_id or "", original_input, feedback_type, note, datetime.now().isoformat())
        )

    return {
        "status": "recorded",
        "task_id": task_id,
        "feedback_type": feedback_type,
        "original_input": original_input
    }


async def handle_step_done(
    conversation_id: int,
    payload: Dict[str, Any],
    executor_id: str
) -> Optional[Dict[str, Any]]:
    task_id = payload.get("task_id")
    step_id = payload.get("step")
    if not task_id or task_id not in _pending:
        return None

    task = _pending[task_id]

    if task.get("cancelled"):
        del _pending[task_id]
        return {"status": "cancelled", "task_id": task_id}

    if step_id in task["done"]:
        return None

    task["done"].add(step_id)
    task["results"].append({
        "step": step_id,
        "description": payload.get("description", ""),
        "status": payload.get("status", "unknown")
    })

    if len(task["done"]) == len(task["steps"]):
        summary = await _summarize(task["user_text"], task["results"])
        summary_msg = f"[SUMMARY]:{summary}"
        _insert_message(conversation_id, summary_msg, sender_agent_id=task["commander_id"])
        del _pending[task_id]
        return {"status": "completed", "task_id": task_id, "summary": summary}

    return {
        "status": "in_progress",
        "task_id": task_id,
        "done": len(task["done"]),
        "total": len(task["steps"])
    }


async def _summarize(user_text: str, results: List[Dict[str, Any]]) -> str:
    result_text = "\n".join(
        f"步骤{r['step']}({r['description']}): {r['status']}" for r in results
    )
    prompt = f"用户任务：{user_text}\n\n执行结果：\n{result_text}\n\n请用一句话总结这次任务的结果。"
    try:
        return await _call_llm(prompt, SUMMARY_SYSTEM_PROMPT)
    except Exception:
        return "任务执行完成。"

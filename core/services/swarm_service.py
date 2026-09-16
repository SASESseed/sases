# core/services/swarm_service.py
import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import openai

from .. import config
from ..db import db_cursor
from . import memory_service

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=40,
    max_retries=2
)

MODEL = config.MODEL_NAME

# ========== 修复 3：prompt 禁用 if ==========
COMMANDER_SYSTEM_PROMPT = """你是 SASES 指挥官。用户会给你一个任务，你需要拆解为可执行的 Windows CMD 命令序列。

【工作目录】
命令在项目根目录 C:\\Users\\xiaomai\\sases 下执行。

【规则】
1. 每个命令必须是单行的 Windows CMD 命令
2. 最多 5 步
3. 只输出 JSON 数组，格式：[{"step":1,"description":"...","command":"..."},...]
4. 不要输出任何其他文字，不要用 markdown 代码块
5. 禁止 uvicorn 等服务器启停命令
6. 禁止使用 if、for、while 等控制流语句，只用简单命令
7. 如果任务模糊，输出：[{"step":1,"description":"任务模糊","command":"echo 请提供更具体的任务说明"}]

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
你会看到"最近的会话历史"和"相关历史经验"。如果用户当前输入引用了之前的内容（如"这个文件"、"刚才那个目录"），请结合历史理解。如果历史经验中有类似任务的成功拆解，可以参考。

【路径规则】
- 已知项目结构：static/modules/ 放前端 JS，core/ 放后端 Python
- 如果不知道文件路径，第 1 步用 dir /s /b 定位；第 2 步用 {{step1}} 引用定位结果
"""

SUMMARY_SYSTEM_PROMPT = """请根据用户任务和执行结果，用一句话总结这次任务的结果。直接输出总结，不要任何前缀。"""

REPLAN_SYSTEM_PROMPT = """你是 SASES 指挥官。之前的命令执行失败了，请针对失败的步骤重新拆解命令。

【必须遵守】
1. 只输出 JSON 数组，不要任何解释、不要 markdown 代码块
2. 格式必须是：[{"step":1,"description":"...","command":"..."}]
3. 每步一个命令，Windows CMD 单行命令
4. 最多 5 步
5. 禁止 uvicorn 等服务器启停命令
6. 禁止使用 if、for、while 等控制流语句

【重拆策略】
- 如果失败原因是"文件找不到"：尝试用 dir /s /b 搜索相似文件名
- 如果失败原因是"路径错误"：先用 dir 确认目录，再用 {{stepN}} 引用
- 如果失败原因是"命令语法错误"：换一种命令写法
- 如果任务本身不可完成：输出 [{"step":1,"description":"无法完成","command":"echo 任务无法完成，请用户确认"}]

现在输出 JSON 数组："""

# ========== 审核员规则 ==========

ERROR_KEYWORDS = [
    "FINDSTR: 无法打开",
    "FINDSTR: Cannot open",
    "系统找不到指定的路径",
    "系统找不到指定的文件",
    "The system cannot find",
    "No such file",
    "拒绝访问",
    "Access is denied",
    "Access denied",
    "不是内部或外部命令",
    "is not recognized as an internal",
    "无法将",
    "cannot be found",
]

COMMANDS_THAT_SHOULD_OUTPUT = ("dir", "ls", "type", "cat", "findstr", "grep", "find", "where")

UNRECOVERABLE_KEYWORDS = ["找不到文件", "系统找不到", "文件不存在", "拒绝访问", "Access is denied"]


# ========== 修复 2：review_step 处理 skipped ==========
def review_step(step: Dict[str, Any], status: str, output: str) -> Tuple[str, str]:
    """审核员：判断单步是否通过，返回 (result, reason)"""
    if status in ("failed", "timeout", "error"):
        return "retry", f"命令状态: {status}"

    if status == "blocked":
        return "retry", "命令被安全策略拒绝"

    if status == "skipped":
        return "retry", "跳过：依赖步骤失败"

    output_str = output or ""
    output_lower = output_str.lower()
    for kw in ERROR_KEYWORDS:
        if kw.lower() in output_lower:
            return "retry", f"输出含错误: {kw}"

    cmd = (step.get("command") or "").strip()
    cmd_first = cmd.split()[0].lower() if cmd.split() else ""
    if cmd_first in COMMANDS_THAT_SHOULD_OUTPUT and not output_str.strip():
        return "retry", "命令应有输出但为空"

    return "pass", ""


# ========== 全局状态 ==========

_pending: Dict[str, Dict[str, Any]] = {}
_feedback_table_ready = False
_review_table_ready = False


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


def _ensure_review_table():
    global _review_table_ready
    if _review_table_ready:
        return
    with db_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS swarm_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                conversation_id INTEGER,
                step_id INTEGER,
                command TEXT,
                exec_status TEXT,
                review_result TEXT,
                review_reason TEXT,
                output_preview TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_task ON swarm_reviews(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_time ON swarm_reviews(created_at)")
    _review_table_ready = True


def _log_review(task_id, conversation_id, step_id, command, exec_status,
                review_result, review_reason, output):
    _ensure_review_table()
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO swarm_reviews
            (task_id, conversation_id, step_id, command, exec_status, review_result, review_reason, output_preview, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                conversation_id,
                step_id,
                (command or "")[:500],
                exec_status,
                review_result,
                review_reason,
                (output or "")[:200],
                datetime.now().isoformat()
            )
        )


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


async def _call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 500) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=max_tokens
    )
    content = resp.choices[0].message.content
    return (content or "").strip()


def _parse_plan(raw: str) -> Optional[List[Dict[str, Any]]]:
    if not raw:
        return None
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


# ========== 主流程 ==========

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

    history_text = _get_conversation_history(conversation_id, limit=10)

    # ========== 读取相关记忆 ==========
    memory_text = ""
    try:
        memories = memory_service.recall(
            user_id=user_id,
            query=user_input,
            top_k=2
        )
        memories = memories[:2]
        if memories:
            lines = []
            for m in memories:
                content = (m.get("content") or "").replace("\n", " ")[:120]
                lines.append(f"- {content}")
            memory_text = "\n".join(lines)
            print(f"[swarm] 检索到 {len(memories)} 条相关记忆")
        else:
            print(f"[swarm] 检索到 0 条相关记忆")
    except Exception as e:
        print(f"[swarm] 记忆检索失败: {e}")

    _insert_message(conversation_id, user_input, sender_agent_id=None)

    # 构造 prompt
    prompt_parts = []
    if memory_text:
        prompt_parts.append(f"【相关历史经验（仅供参考）】\n{memory_text}")
    if history_text:
        prompt_parts.append(f"【最近的会话历史】\n{history_text}")
    prompt_parts.append(f"【用户当前任务】\n{user_input}")
    prompt_parts.append(
        "请拆解为命令序列。\n"
        "必须只输出 JSON 数组，格式：[{\"step\":1,\"description\":\"...\",\"command\":\"...\"}]\n"
        "不要输出任何其他文字，不要用 markdown 代码块。"
    )
    full_prompt = "\n\n".join(prompt_parts)

    try:
        raw = await _call_llm(full_prompt, COMMANDER_SYSTEM_PROMPT)
    except Exception as e:
        err_msg = f"[SUMMARY]:任务拆解失败：{str(e)}"
        _insert_message(conversation_id, err_msg, sender_agent_id=commander_id)
        return {"status": "error", "message": str(e)}

    steps = _parse_plan(raw)
    if not steps:
        print(f"[swarm] 拆解失败，LLM 原始返回: {raw[:500]!r}")
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
            "no_plan": True,
            "retry_count": 0,
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
        "no_plan": False,
        "retry_count": 0,
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


async def replan_failed_steps(task: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """针对失败的步骤，让指挥官重拆"""
    failed_info = []
    for r in task["results"]:
        if r.get("review") == "retry":
            failed_info.append({
                "step": r["step"],
                "description": r.get("description", ""),
                "original_command": r.get("command", ""),
                "failure_reason": r.get("reason", ""),
                "output_preview": (r.get("output") or "")[:200],
            })

    if not failed_info:
        return None

    all_unrecoverable = True
    for f in failed_info:
        output = (f.get("output_preview") or "") + (f.get("failure_reason") or "")
        if not any(kw in output for kw in UNRECOVERABLE_KEYWORDS):
            all_unrecoverable = False
            break

    if all_unrecoverable:
        print(f"[swarm] 所有失败均为不可恢复错误，跳过重拆")
        return None

    prompt = f"""原任务：{task['user_text']}

已完成的步骤及结果：
{json.dumps(task['results'], ensure_ascii=False, indent=2)}

失败的步骤（需要你重新拆解）：
{json.dumps(failed_info, ensure_ascii=False, indent=2)}

请针对上述失败步骤重新拆解命令。要求：
1. 必须输出 JSON 数组，不要任何解释文字
2. 格式：[{{"step":1,"description":"...","command":"..."}}]
3. 如果是"文件找不到"，请先尝试搜索类似文件名
4. 用 {{{{stepN}}}} 引用前序步骤的输出
5. 禁止使用 if、for、while 等控制流语句

只输出 JSON 数组，现在开始："""

    try:
        raw = await _call_llm(prompt, REPLAN_SYSTEM_PROMPT, max_tokens=1000)
        print(f"[swarm] 重拆 LLM 返回长度: {len(raw)}, 前 300 字: {raw[:300]!r}")
    except Exception as e:
        print(f"[swarm] 重拆 LLM 异常: {e}")
        return None

    if not raw or not raw.strip():
        print(f"[swarm] 重拆 LLM 返回空，放弃重拆")
        return None

    steps = _parse_plan(raw)
    if not steps:
        print(f"[swarm] 重拆 JSON 解析失败，原始输出: {raw[:500]!r}")
        return None

    for i, s in enumerate(steps):
        s["step"] = i + 1
    print(f"[swarm] 重拆成功，新步骤数: {len(steps)}")
    return steps


async def handle_step_done(
    conversation_id: int,
    payload: Dict[str, Any],
    executor_id: str
) -> Optional[Dict[str, Any]]:
    """处理执行者汇报的 [STEP_DONE]:，含审核员判定"""
    task_id = payload.get("task_id")
    step_id = payload.get("step")
    if not task_id or task_id not in _pending:
        return None

    task = _pending[task_id]

    if task.get("cancelled"):
        del _pending[task_id]
        return {"status": "cancelled", "task_id": task_id}

    # 找到原始步骤
    original_step = None
    for s in task["steps"]:
        if s.get("step") == step_id:
            original_step = s
            break
    if original_step is None:
        original_step = {"step": step_id, "command": ""}

    # 审核员判断
    status = payload.get("status", "unknown")
    output = payload.get("output", "")
    review_result, review_reason = review_step(original_step, status, output)

    task["done"].add(step_id)
    task["results"].append({
        "step": step_id,
        "description": payload.get("description", ""),
        "command": original_step.get("command", ""),
        "status": status,
        "review": review_result,
        "reason": review_reason,
        "output": (output or "")[:300],
    })

    print(f"[swarm] step {step_id} 审核: {review_result} | {review_reason}")

    # ========== 单步失败时写失败记忆 ==========
    if review_result == "retry":
        try:
            fail_cmd = original_step.get("command", "")
            fail_content = (
                f"命令「{fail_cmd[:150]}」执行失败。\n"
                f"失败原因：{review_reason}"
            )
            memory_service.remember(
                user_id=task["user_id"],
                memory_type="failure_pattern",
                content=fail_content,
                task_id=task_id,
                importance=0.5,
                tags="failure,swarm"
            )
            print(f"[swarm] 失败记忆已写入")
        except Exception as e:
            print(f"[swarm] 写失败记忆失败: {e}")

    # 审核日志入库
    try:
        _log_review(
            task_id=task_id,
            conversation_id=conversation_id,
            step_id=step_id,
            command=original_step.get("command", ""),
            exec_status=status,
            review_result=review_result,
            review_reason=review_reason,
            output=output
        )
    except Exception as e:
        print(f"[swarm] 审核日志入库失败: {e}")

    # 全部完成
    if len(task["done"]) >= len(task["steps"]):
        failed = [r for r in task["results"] if r.get("review") == "retry"]
        blocked = [r for r in task["results"] if r.get("status") == "blocked"]

        # 有命令被安全策略拒绝 → 直接汇总，不重拆
        if blocked:
            print(f"[swarm] 发现 {len(blocked)} 个被拒绝的命令，跳过重拆")
            summary = await _summarize(task["user_text"], task["results"])
            summary_msg = f"[SUMMARY]:{summary}"
            _insert_message(conversation_id, summary_msg, sender_agent_id=task["commander_id"])
            del _pending[task_id]
            return {"status": "completed_with_blocks", "task_id": task_id}

        if failed and task["retry_count"] < 2:
            task["retry_count"] += 1
            print(f"[swarm] 发现 {len(failed)} 个失败步骤，触发重拆 (第 {task['retry_count']} 次)")
            new_steps = await replan_failed_steps(task)

            if new_steps:
                task["results"] = []
                task["done"] = set()
                task["steps"] = new_steps

                retry_payload = {"task_id": task_id, "steps": new_steps}
                retry_msg = "[RETRY_TASK]:" + json.dumps(retry_payload, ensure_ascii=False)
                _insert_message(conversation_id, retry_msg, sender_agent_id=task["commander_id"])

                return {
                    "status": "retry_triggered",
                    "task_id": task_id,
                    "new_steps": new_steps,
                    "retry_count": task["retry_count"]
                }
            else:
                print(f"[swarm] 重拆失败或跳过，直接汇总")
                summary = await _summarize(task["user_text"], task["results"])
                summary_msg = f"[SUMMARY]:{summary}"
                _insert_message(conversation_id, summary_msg, sender_agent_id=task["commander_id"])
                del _pending[task_id]
                return {"status": "completed_with_failures", "task_id": task_id}
        else:
            if failed:
                print(f"[swarm] 重试次数已达上限，标记失败并汇总")
            else:
                # 全部通过 → 写成功记忆
                try:
                    steps_desc = "\n".join(
                        f"  {r['step']}. {r.get('command', '')[:80]}"
                        for r in task["results"]
                    )
                    success_content = (
                        f"任务「{task['user_text']}」成功完成。\n"
                        f"使用命令：\n{steps_desc}"
                    )
                    memory_service.remember(
                        user_id=task["user_id"],
                        memory_type="task_result",
                        content=success_content,
                        task_id=task_id,
                        importance=0.6,
                        tags="success,swarm"
                    )
                    print(f"[swarm] 成功记忆已写入")
                except Exception as e:
                    print(f"[swarm] 写成功记忆失败: {e}")

            summary = await _summarize(task["user_text"], task["results"])
            summary_msg = f"[SUMMARY]:{summary}"
            _insert_message(conversation_id, summary_msg, sender_agent_id=task["commander_id"])
            del _pending[task_id]
            return {"status": "completed", "task_id": task_id, "summary": summary}

    return {
        "status": "in_progress",
        "task_id": task_id,
        "done": len(task["done"]),
        "total": len(task["steps"]),
        "review": review_result,
    }


async def _summarize(user_text: str, results: List[Dict[str, Any]]) -> str:
    result_text = "\n".join(
        f"步骤{r['step']}({r['description']}): {r['status']} [审核:{r.get('review','?')}]"
        for r in results
    )
    prompt = f"用户任务：{user_text}\n\n执行结果：\n{result_text}\n\n请用一句话总结这次任务的结果。"
    try:
        return await _call_llm(prompt, SUMMARY_SYSTEM_PROMPT)
    except Exception:
        return "任务执行完成。"

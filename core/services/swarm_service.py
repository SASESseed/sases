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
    timeout=180,
    max_retries=3
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
6. 禁止使用 if 条件语句，只用简单命令
7. 如果任务模糊，输出：[{"step":1,"description":"任务模糊","command":"echo 请提供更具体的任务说明"}]
8. 每步 description 不超过 30 字，command 不超过 200 字，总输出不超过 800 字。
9. 修改类任务（file_patch）执行成功后，不要再生成 findstr 或 type 等验证命令。工具返回 success 即为完成。多余的验证步骤会干扰判断。
10. 只有用户明确要求"检查"时，才生成查询命令。
11. 一个任务最多生成 1 个 file_patch 步骤。多处修改请让用户分批发送指令，不要一次性拆成多个 patch。
12. 生成查询命令时，禁止使用以下字符：& < > ^ % ` $ 
    如果搜索关键词包含这些字符，改用不含特殊字符的短关键词代替。
    例如：不要写 findstr /c:"() => openRedPacketDialog()"，要写 findstr /c:"openRedPacketDialog"。

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

- 读长文件：优先用 file_read harness 工具，例如 {"step":1,"type":"harness","module_id":"file_read","params":{"file_path":"core/x.py","max_lines":50}}。禁止使用 more / less / head / tail。
- 在文件中搜索：findstr /n "关键词" <文件路径>
- 只显示文件名：dir /b
- 当前路径：cd
- 当前用户：whoami

【可用 Harness 工具】

调用格式：{"step":N,"type":"harness","module_id":"工具ID","params":{...}}

【harness 工具参数速查（重要）】
- file_read: file_path(必填), max_lines(默认200), offset(默认0)
- file_patch: file_path(必填) + 三选一模式：
    锚点模式: anchor_pattern + position(before/after/replace_line) + new_content
    精确片段: old_snippet + new_snippet + expected_count
    整体覆写: overwrite=true + new_content
- grep_code: pattern(必填！不是 keyword/query), path, file_ext, max_results
- dir_tree: path(默认.), max_depth(默认2)
- run_python: code(Python源码字符串)
- api_call: url(必填), method(默认GET), headers, body
- verify_patch: file_path(必填), expect_contains, expect_not_contains
- harness_reload: 无参数
- web_fetch: url(必填)
- git_ops: action(必填: status/diff/log/add/commit/push/pull/rollback/snapshot)

【路径铁律】所有 file_path 必须用相对路径（如 core/services/x.py）。禁止用 C: 开头的绝对路径。dir 输出里的绝对路径要手工截取成相对部分。

【Windows 命令纪律】
Windows CMD 不支持 pwd，用 cd 代替。
Windows CMD 不支持 ls，用 dir 代替。
Windows CMD 不支持 cat，用 type 代替。
Windows CMD 不支持 grep，用 findstr 代替。

【搜索纪律】禁止 dir /s /b 全盘扫描（会超时 30 秒）。必须先指定目录：
  正确: dir /s /b core/services/*.py
  错误: dir /s /b *.py

【类比迁移纪律（重要）】
当任务描述含"类似X""参考X""仿照X"时：
1. 第一步必须用 grep_code 搜索 X 相关关键词，定位 X 的实现在哪些文件
2. 用 file_read 读 X 的实现，看清它的格式（如 uploadImage: async (file) => 而非 async function uploadImage）
3. 复制 X 的格式，把名字换掉，做对应改动
4. 禁止凭经验猜锚点，锚点必须从 file_read 输出的原文里复制

【文件假设纪律】不要假设文件存在（如 red_packet_routes.py 可能不存在）。做任何 patch 前先用 grep_code 或 file_read 确认路径。




【改动后必验证】
- 每次 file_patch 修改 .py 或 .js 文件后，必须紧接着调用 verify_syntax（type=harness, module_id=verify_syntax, params: {file_path}）
- 如果 verify_syntax 返回 success=False，说明改动引入了语法错误
- 此时应该用 verify_syntax 返回的 latest_backup 路径，通过 file_patch overwrite 还原，或直接放弃本次改动
【file_patch 后必须验证（重要）】
- 每次 file_patch 改 .py 或 .js 成功后，下一步应调 verify_syntax 验证
- 例如：{"step":N,"type":"harness","module_id":"verify_syntax","params":{"file_path":"<刚改的文件>","auto_rollback":true}}
- verify_syntax 返回 syntax_ok=false 时，会自动从 .backups/ 恢复，你只需据此重新规划
- 若 modify 后不验证，坏语法可能在用户下次刷新时崩溃浏览器


【执行纪律（重要）】
- 一次任务中，同一步骤只做一件事。不要一次 file_patch 改多处，也不要一次生成多个 harness 调用。
- 改 core/ 下的 .py 后，在 description 里提醒"需重启服务"；改 static/ 下的 .js 不需要重启。
- 遇到路径不确定，先用 dir_tree 或 grep_code 确认，不要凭记忆猜路径。


【harness 调用铁律（极其重要）】
- 任何 harness 工具（file_read / file_patch / run_python / api_call / grep_code / dir_tree / web_fetch / git_ops / harness_reload 等）必须用 type=harness + module_id + params 三个字段
- 绝对不能写成 command: "harness:xxx" 或 command: "file_read" 或 command: "file_patch ..."
- 只有系统命令（dir / type / findstr / echo / cd 等）才用 command 字段
- 正确示例：{"step":1,"type":"harness","module_id":"file_read","params":{"file_path":"core/x.py","max_lines":50}}
- 错误示例：{"step":1,"command":"harness:file_read"} 或 {"step":1,"command":"file_read core/x.py"}
- 生成每步之前，自问：这步是系统命令还是 harness 工具？如果模块名以 _ 分隔（file_read / run_python）或用 - 分隔（base64-codec），几乎肯定是 harness 工具，用 type=harness 格式。


具体可用工具清单见下方【当前可用 Harness 工具】（运行时动态注入）。


【run_python 安全函数】


【步数铁律】最多生成 5 步。超过 5 步时，只生成前 5 步，剩余部分用 answer 工具告诉用户「剩余任务请再发一次」。（step 数量 > 5 会被系统截断，后 5 步直接丢失）

- list_dir(path)：列目录（例：list_dir('core/services')）
- read_file(path)：读文件（例：read_file('core/config.py')）
- write_file(path, content)：写文件
禁止 import os/sys/subprocess/open，需要文件操作用以上函数。


- file_patch：修改项目文件（允许目录：static/ / core/ / scripts/ / docs/）。支持两种模式：

  【模式 A：锚点模式（强烈推荐，默认用这个）】
  格式：{"step":1,"type":"harness","module_id":"file_patch","params":{
    "file_path":"static/modules/chat_ui.js",
    "anchor_pattern":"export function createMessageElement",
    "position":"after",
    "new_content":"    if (typeof content === 'string' && content.startsWith('[RED_PACKET]:')) { return renderRedPacketBubble(content); }"
  },"description":"在函数开头插入红包判断"}

  参数说明：
  - anchor_pattern：一段**唯一出现**的短关键词（10~60 字符），
    通常是函数名、变量名、或一行独特代码的一部分。
    **不要**用整行代码，只要片段就够，因为 anchor 只需要能唯一定位一行。
  - position：
    "after" — 在锚点行的下一行插入 new_content
    "before" — 在锚点行的上一行插入 new_content
    "replace_line" — 用 new_content 替换锚点行
  - new_content：要插入或替换的内容，可包含缩进（用 \n 分隔多行时，缩进要自己加）

  【模式 B：精确片段模式（仅在你能看到完整原文时用）】
  格式：{"step":1,...,"params":{
    "file_path":"...",
    "old_snippet":"完全精确的旧片段",
    "new_snippet":"新片段",
    "expected_count":1
  }}

  【file_patch 铁律】
  a) **绝对不要凭猜测生成 old_snippet**。你无法知道文件的真实内容，除非前序步骤用
     type / findstr 读出来了。
  b) **优先用模式 A（锚点模式）**，它只需要你知道一个短关键词，不需要知道完整原文。
  c) 如果任务要求"在函数 X 里加一行"，用：
       step 1: findstr /n "function X" <文件>   （确认函数存在）
       step 2: file_patch 用 anchor_pattern="function X"，position="after"
  d) 锚点必须唯一。如果 findstr 显示匹配多行，换更长的锚点。
  e) 一次 patch 只改一处。多处修改请拆成多个 step。
  f) 允许修改：static/ / core/ / scripts/ / docs/ 下的文件。
     禁止修改：users.db / .env / *.key / *.bin / *.pem / *.crt。
     修改 core/ 下的文件后，用户需要重启服务才能生效，请在 description 中提醒。

【会话上下文】
你会看到"最近的会话历史"和"相关历史经验"。如果用户当前输入引用了之前的内容（如"这个文件"、"刚才那个目录"），请结合历史理解。

【复杂修改任务的拆解策略】
当用户要求改功能 / 加功能 / 修 bug，且不清楚要改哪些文件时：
1. 先派探测步骤，不要直接改：
   - grep_code 搜索相关关键词定位文件
   - file_read 读关键函数的代码
   - dir_tree 了解目录结构
2. 基于探测结果，再生成修改步骤（file_patch）
3. 一次任务最多 5 步。若不够，只完成探测加关键修改，在 description 说明还有剩余工作

示例：用户说改红包功能：
  step 1: grep_code 搜索 red_packet 定位文件
  step 2: file_read 读 transfer_service.py 相关函数
  step 3: file_patch 完成修改

不要盲目开始修改。先读再改。


【路径规则】
- 已知项目结构：static/modules/ 放前端 JS；core/ 放核心模块；core/services/ 放业务逻辑（swarm_service.py / message_service.py / memory_service.py / pattern_service.py 等都在这）；core/api_routes/ 放 API 路由；harness_modules/ 放 harness 工具；scripts/ 放脚本；docs/ 放文档

- 禁止把 *_service.py 直接写到 core/ 下，业务代码统统在 core/services/ 下。例：core/services/swarm_service.py（对），core/swarm_service.py（错）。
- 禁止把 *_routes.py 直接写到 core/ 下，路由代码统统在 core/api_routes/ 下。例：core/api_routes/message_routes.py（对）。

- 【重要】若用户输入以 [MODIFY] 开头，说明之前已经探测过但没动手。此时禁止再生成纯探测步骤（grep_code / file_read / dir_tree 最多 1 步），剩余步骤必须包含至少 1 个 file_patch。如果信息不足，用最多 1 步 file_read 确认，然后立刻 file_patch，不要重复探测。
- 【重要】若任务明显需要多次修改，优先一次完成最关键的一处，不要把 5 步全用来探测。

- 【重要】若用户输入以 [MODIFY] 开头，说明之前已经探测过但没动手。此时禁止再生成纯探测步骤（grep_code / file_read / dir_tree 最多 1 步），剩余步骤必须包含至少 1 个 file_patch。如果信息不足，用最多 1 步 file_read 确认，然后立刻 file_patch，不要重复探测。
- 【重要】若任务明显需要多次修改，优先一次完成最关键的一处，不要把 5 步全用来探测。
- 如果不知道文件路径，第 1 步用 dir /s /b 定位；第 2 步用 {{step1}} 引用定位结果
"""

SUMMARY_SYSTEM_PROMPT = """请根据用户任务和执行结果，用一句话总结这次任务的结果。直接输出总结，不要任何前缀。"""

REPLAN_SYSTEM_PROMPT = """你是 SASES 指挥官。之前的命令执行失败了，请针对失败的步骤重新拆解命令。

【必须遵守】
1. 只输出 JSON 数组，不要任何解释、不要 markdown 代码块
2. 格式必须是：[{"step":1,"description":"...","command":"..."}]
3. 每步一个命令，Windows CMD 单行命令
4. harness 工具必须用 {"step":N,"type":"harness","module_id":"file_patch","params":{...}} 格式，不要写成 command 字段。禁止把 file_patch 写成 command
5. file_patch 参数：file_path / anchor_pattern / position / new_content 或 file_path / old_snippet / new_snippet / expected_count
6. 读文件用 {"type":"harness","module_id":"file_read","params":{"file_path":"..."}}，禁止用 type / cat / more 命令读大文件
7. 最多 5 步
8. 禁止 uvicorn 等服务器启停命令
9. 禁止使用 copy / move / del / powershell / for / if / 重定向（> < &）等命令
10. 只允许使用：dir / ls / tree / type / cat / head / tail / findstr / find / grep / where / echo / pwd / cd / whoami / hostname / wc

【严格禁止占位符（极其重要）】
11. 禁止在 params 的 code / new_content / old_snippet / new_snippet 里使用 "..."、"省略"、"同上"、"（略）" 等占位符
12. 禁止生成空壳步骤（如 "code": "..."）
13. 每个 string 参数必须包含完整可执行或可匹配的内容，可以直接使用，无需二次补充
14. 如果内容太长：拆成多个 step，每步内容完整，而不是用占位符偷懒
15. 生成 JSON 后必须自检：每个字符串参数是否可以独立使用？如果不是，重新生成
16. 需要写多行 Python 代码时，用 chr(10) 拼接，不要用真实换行导致 JSON 转义失败

【重拆策略】
- 如果失败原因是"old_snippet 未找到"：先用 findstr /n /c:"片段" 精确确认原文，再 patch
- 如果失败原因是"文件找不到"：尝试用 dir /s /b 搜索相似文件名
- 如果失败原因是"路径错误"：先用 dir 确认目录，再用 {{stepN}} 引用
- 如果失败原因是"命令语法错误"：换一种命令写法
- 如果 task 需要多处修改：拆成多个 step，每个 step 一处 patch
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


def review_step(step: Dict[str, Any], status: str, output: str) -> Tuple[str, str]:
    # 查询类命令"没找到"属于正常结果，不算失败
    cmd = (step.get("command") or "").strip()
    cmd_first = cmd.split()[0].lower() if cmd.split() else ""
    if cmd_first in ("findstr", "find", "grep", "where") and status == "failed":
        _out = (output or "").lower()
        if "cannot open" in _out or "无法打开" in _out or "系统找不到" in _out or "cannot find" in _out:
            return "retry", "目标文件不存在，路径可能有误"
        return "pass", "查询无结果（正常）"

    if status in ("failed", "timeout", "error"):
        detail = (output or "").strip()[:200]
        return "retry", f"命令状态: {status} | {detail}"

    if status == "blocked":
        return "retry", "命令被安全策略拒绝"

    if status == "skipped":
        return "retry", "跳过：依赖步骤失败"

    output_str = output or ""
    output_lower = output_str.lower()
    for kw in ERROR_KEYWORDS:
        if kw.lower() in output_lower:
            return "retry", f"输出含错误: {kw}"

    if cmd_first in COMMANDS_THAT_SHOULD_OUTPUT and not output_str.strip():
        return "retry", "命令应有输出但为空"

    return "pass", ""


# ========== 全局内存缓存 ==========
_pending: Dict[str, Dict[str, Any]] = {}
_feedback_table_ready = False
_review_table_ready = False


# ========== 数据库同步 ==========

def clear_conversation_lock(conversation_id: str) -> bool:
    cleared = False
    for task_id in list(_pending.keys()):
        task = _pending.get(task_id) or {}
        if task.get("conversation_id") == conversation_id and task.get("status") in ("pending", "running"):
            task["status"] = "cancelled"
            del _pending[task_id]
            cleared = True
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE swarm_pending_tasks SET status='cancelled' WHERE conversation_id=? AND status IN ('pending','running')",
            (conversation_id,),
        )
        if cur.rowcount:
            cleared = True
        cur.execute(
            "UPDATE supervisor_runs SET status='interrupted' WHERE conversation_id=? AND status IN ('running','proposed')",
            (conversation_id,),
        )
        if cur.rowcount:
            cleared = True
        conn.commit()
        conn.close()
    except Exception:
        pass
    return cleared



def _save_pending(task: Dict[str, Any]):
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO swarm_pending_tasks
                (task_id, conversation_id, user_id, commander_id, executor_id,
                 user_text, steps, results, done_steps, retry_count,
                 is_draft, cancelled, no_plan, status, created_at, updated_at, supervisor_id, supervisor_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    conversation_id=excluded.conversation_id,
                    user_id=excluded.user_id,
                    commander_id=excluded.commander_id,
                    executor_id=excluded.executor_id,
                    user_text=excluded.user_text,
                    steps=excluded.steps,
                    results=excluded.results,
                    done_steps=excluded.done_steps,
                    retry_count=excluded.retry_count,
                    is_draft=excluded.is_draft,
                    cancelled=excluded.cancelled,
                    no_plan=excluded.no_plan,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    supervisor_id=excluded.supervisor_id,
                    supervisor_run_id=excluded.supervisor_run_id
                """,
                (
                    task["task_id"],
                    task.get("conversation_id"),
                    task["user_id"],
                    task.get("commander_id"),
                    task.get("executor_id"),
                    task.get("user_text", ""),
                    json.dumps(task.get("steps", []), ensure_ascii=False),
                    json.dumps(task.get("results", []), ensure_ascii=False),
                    json.dumps(sorted(list(task.get("done", set()))), ensure_ascii=False),
                    task.get("retry_count", 0),
                    1 if task.get("is_draft") else 0,
                    1 if task.get("cancelled") else 0,
                    1 if task.get("no_plan") else 0,
                    _derive_status(task),
                    task.get("created_at", datetime.now().isoformat()),
                    datetime.now().isoformat(),
                    task.get("supervisor_id"),
                    task.get("supervisor_run_id"),
                )
            )
    except Exception as e:
        print(f"[swarm] DB 写入失败: {e}")


def _derive_status(task: Dict[str, Any]) -> str:
    if task.get("cancelled"):
        return "cancelled"
    if task.get("no_plan"):
        return "no_plan"
    if task.get("is_draft"):
        return "draft"
    if len(task.get("done", set())) >= len(task.get("steps", [])):
        return "completed"
    if len(task.get("done", set())) > 0:
        return "running"
    return "pending"


def _has_active_task_in_conversation(conversation_id: int) -> bool:
    if not conversation_id:
        return False

    for task in _pending.values():
        if task.get("conversation_id") != conversation_id:
            continue
        if task.get("cancelled") or task.get("no_plan") or task.get("is_draft"):
            continue
        done = task.get("done", set())
        steps = task.get("steps", [])
        if len(done) >= len(steps):
            continue
        return True

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as cnt FROM swarm_pending_tasks
                WHERE conversation_id=? AND status IN ('pending', 'running')
                """,
                (conversation_id,)
            )
            row = cur.fetchone()
            return bool(row and row["cnt"] > 0)
    except Exception as e:
        print(f"[swarm] 检查活跃任务失败: {e}")
        return False


def _delete_pending_from_db(task_id: str):
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM swarm_pending_tasks WHERE task_id=?", (task_id,))
    except Exception as e:
        print(f"[swarm] DB 删除失败: {e}")


def _load_pending(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM swarm_pending_tasks WHERE task_id=?", (task_id,))
            row = cur.fetchone()
        if not row:
            return None
        row = dict(row)
        return {
            "task_id": row["task_id"],
            "conversation_id": row["conversation_id"],
            "user_id": row["user_id"],
            "commander_id": row["commander_id"],
            "executor_id": row["executor_id"],
            "user_text": row["user_text"] or "",
            "steps": json.loads(row["steps"] or "[]"),
            "results": json.loads(row["results"] or "[]"),
            "done": set(json.loads(row["done_steps"] or "[]")),
            "retry_count": row["retry_count"] or 0,
            "is_draft": bool(row["is_draft"]),
            "cancelled": bool(row["cancelled"]),
            "no_plan": bool(row["no_plan"]),
            "created_at": row["created_at"],
            "supervisor_id": row["supervisor_id"] if "supervisor_id" in row.keys() else None,
            "supervisor_run_id": row["supervisor_run_id"] if "supervisor_run_id" in row.keys() else None,
        }
    except Exception as e:
        print(f"[swarm] DB 加载失败: {e}")
        return None


def restore_pending_tasks():
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT task_id FROM swarm_pending_tasks WHERE status IN ('pending', 'running', 'draft')"
            )
            rows = cur.fetchall()
        count = 0
        for row in rows:
            task = _load_pending(row["task_id"])
            if task:
                _pending[task["task_id"]] = task
                count += 1
        print(f"[swarm] 已恢复 {count} 个待处理任务")
        return count
    except Exception as e:
        print(f"[swarm] 恢复任务失败: {e}")
        return 0


# ========== 表格初始化 ==========

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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_conversation ON swarm_reviews(conversation_id)")
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
                task_id, conversation_id, step_id,
                (command or "")[:500], exec_status,
                review_result, review_reason,
                (output or "")[:200], datetime.now().isoformat()
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


async def _call_llm(prompt: str, system_prompt: str = "", max_tokens: int = None) -> str:
    if max_tokens is None:
        max_tokens = config.COMMANDER_MAX_TOKENS
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

    choice = resp.choices[0]
    content = choice.message.content
    finish_reason = choice.finish_reason

    print(f"[swarm-debug] finish_reason={finish_reason}, content_len={len(content) if content else 0}")

    # 优先返回 content
    if content and content.strip():
        return content.strip()

    # 兜底：从 reasoning_content 提取 JSON
    rc = getattr(choice.message, 'reasoning_content', None)
    if rc:
        print(f"[swarm-debug] content 为空，尝试从 reasoning_content 提取 JSON")
        import re as _re
        m = _re.search(r'\[\s*\{.*\}\s*\]', rc, _re.DOTALL)
        if m:
            return m.group(0)

    return ""


def _normalize_steps(steps):
    """把误写成 command 的 harness 调用自动纠正为 type=harness 格式"""
    import json as _j_norm
    out = []
    for s in (steps or []):
        if not isinstance(s, dict):
            continue
        cmd = s.get('command', '')
        if not isinstance(cmd, str):
            out.append(s)
            continue
        cmd_stripped = cmd.strip()
        handled = False
        # 情况1：command 是 JSON
        if cmd_stripped.startswith('{') and 'module_id' in cmd_stripped:
            try:
                j = _j_norm.loads(cmd_stripped)
                if isinstance(j, dict) and j.get('module_id'):
                    out.append({  'step': s.get('step'), 'type': 'harness', 'module_id': j['module_id'], 'params': j.get('params', {}), 'description': s.get('description', '') })
                    print('[_normalize] JSON command 转 harness: ' + j['module_id'])
                    handled = True
            except Exception:
                pass
        # 情况2：command 是 harness:xxx 或 harness xxx
        if not handled and ('harness:' in cmd_stripped or cmd_stripped.startswith('harness ')):
            body = cmd_stripped.replace('harness:', '', 1).replace('harness ', '', 1).strip()
            mid = body.split(' ')[0].split(':')[0].strip()
            if mid:
                out.append({  'step': s.get('step'), 'type': 'harness', 'module_id': mid, 'params': {}, 'description': s.get('description', '') })
                print('[_normalize] harness 前缀转 module_id: ' + mid)
                handled = True
        if not handled:
            out.append(s)
    return out

def _parse_plan(raw: str) -> Optional[List[Dict[str, Any]]]:
    if not raw:
        return None
    raw = raw.strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            steps = json.loads(raw[start:end+1])
            if isinstance(steps, list) and steps:
                return steps[:5]
        except json.JSONDecodeError:
            pass

    if start != -1:
        candidate = raw[start:]
        depth = 0
        last_valid = None
        for i, ch in enumerate(candidate):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    last_valid = i
        if last_valid is not None:
            try:
                fixed = candidate[:last_valid+1] + "]"
                steps = json.loads(fixed)
                if isinstance(steps, list) and steps:
                    print(f"[swarm] _parse_plan 三级修复成功，步骤数: {len(steps)}")
                    return steps[:5]
            except json.JSONDecodeError:
                pass

    if start != -1:
        objects = []
        depth = 0
        obj_start = None
        for i, ch in enumerate(raw[start:], start=start):
            if ch == "{":
                if depth == 0:
                    obj_start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and obj_start is not None:
                    try:
                        obj = json.loads(raw[obj_start:i+1])
                        if isinstance(obj, dict) and ("command" in obj or "type" in obj):
                            objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    obj_start = None
        if objects:
            for i, s in enumerate(objects):
                s["step"] = i + 1
            print(f"[swarm] _parse_plan 四级修复成功，步骤数: {len(objects)}")
            return objects[:5]

    return None


# ========== 主流程 ==========

def clear_conversation_lock(conversation_id):
    """清理指定会话的锁状态。"""
    _locks = globals().get('_conversation_locks', None)
    if isinstance(_locks, dict):
        _locks.pop(conversation_id, None)
    return {'ok': True, 'conversation_id': conversation_id}



async def plan_task(
    user_id: int,
    conversation_id: int,
    user_input: str,
    commander_id: str = None,
    executor_id: str = None,
    timeout: int = 30,
    require_confirmation: bool = False,
    supervisor_id: str = None,
    supervisor_run_id: int = None
) -> Dict[str, Any]:
    if conversation_id and _has_active_task_in_conversation(conversation_id):
        err_msg = "[SUMMARY]:当前会话有正在执行的任务，请等待完成或取消后再提交新任务。"
        _insert_message(conversation_id, err_msg, sender_agent_id=None)
        print(f"[swarm] 会话 {conversation_id} 已有活跃任务，拒绝新任务")
        return {"status": "busy", "message": "会话已有运行中的任务"}

    if not commander_id or not executor_id:
        auto_cmd, auto_exec = pick_swarm_agents(user_id)
        commander_id = commander_id or auto_cmd
        executor_id = executor_id or auto_exec

    if not commander_id:
        err_msg = "[SUMMARY]:未找到可用智能体，请先在模型管理中创建智能体。"
        _insert_message(conversation_id, err_msg, sender_agent_id=None)
        return {"status": "no_agent", "message": "用户没有可用智能体"}

    history_text = _get_conversation_history(conversation_id, limit=10)

    success_text = ""
    failure_text = ""
    try:
        success_memories = memory_service.recall(
            user_id=user_id, query=user_input, top_k=2, memory_type="task_result"
        )[:2]
        if success_memories:
            lines = []
            for m in success_memories:
                content = (m.get("content") or "").replace("\n", " ")[:120]
                lines.append(f"- {content}")
            success_text = "\n".join(lines)
            print(f"[swarm] 检索到 {len(success_memories)} 条成功经验")
        else:
            print(f"[swarm] 检索到 0 条成功经验")
    except Exception as e:
        print(f"[swarm] 成功记忆检索失败: {e}")

    try:
        failure_memories = memory_service.recall(
            user_id=user_id, query=user_input, top_k=2, memory_type="failure_pattern"
        )[:2]
        if failure_memories:
            lines = []
            for m in failure_memories:
                content = (m.get("content") or "").replace("\n", " ")[:120]
                lines.append(f"- {content}")
            failure_text = "\n".join(lines)
            print(f"[swarm] 检索到 {len(failure_memories)} 条失败教训")
        else:
            print(f"[swarm] 检索到 0 条失败教训")
    except Exception as e:
        print(f"[swarm] 失败记忆检索失败: {e}")

    _insert_message(conversation_id, user_input, sender_agent_id=None)

    # 项目库检索（v0.17.0）
    project_text = ""
    try:
        from . import project_service
        chunks = project_service.retrieve_project_chunks(user_input, top_k=3, user_id=user_id)
        if chunks:
            project_text = project_service.format_chunks_for_prompt(chunks)
            print(f"[swarm] 检索到 {len(chunks)} 条项目资料")
        else:
            print(f"[swarm] 项目库无匹配")
    except Exception as e:
        print(f"[swarm] 项目库检索失败: {e}")


    pattern_text = ''
    try:
        import random as _rnd
        if _rnd.random() < 0.5:
            from . import pattern_service
            _pats = pattern_service.retrieve_patterns(user_input, domain='dev', top_k=3)
            if _pats:
                pattern_text = pattern_service.format_patterns_for_prompt(_pats)
                print(f'[swarm] 注入 {len(_pats)} 条 pattern (A组)')
            else:
                print('[swarm] 无相关 pattern (A组)')
        else:
            print('[swarm] 跳过 pattern 注入 (B组)')
    except Exception as e:
        print(f'[swarm] pattern 检索失败: {e}')


    prompt_parts = []
    if pattern_text:
        prompt_parts.append(pattern_text)


    if project_text:
        prompt_parts.append(project_text)


    if success_text:
        prompt_parts.append(f"【可参考的成功经验】\n{success_text}")
    if failure_text:
        prompt_parts.append(f"【需要避免的失败教训】\n{failure_text}")
    if history_text:
        prompt_parts.append(f"【最近的会话历史】\n{history_text}")
    try:
        from .. import harness_runtime as _hr
        _tools = _hr.harness_runtime.list_tools()
        if _tools:
            _tl = ['【当前可用 Harness 工具】']
            for _t in _tools:
                _mid = getattr(_t, 'module_id', '') or ''
                _name = getattr(_t, 'name', '') or ''
                _desc = (getattr(_t, 'description', '') or '')[:100]
                if _mid:
                    _tl.append('- ' + _mid + '：' + _name + ' —— ' + _desc)
            if len(_tl) > 1:
                prompt_parts.append(chr(10).join(_tl))
    except Exception as _te:
        print('[swarm] 注入工具清单失败: ' + str(_te))


    prompt_parts.append(f"【用户当前任务】\n{user_input}")
    prompt_parts.append(
        "请拆解为命令序列。\n"
        "必须只输出 JSON 数组，格式：[{\"step\":1,\"description\":\"...\",\"command\":\"...\"}]\n"
        "不要输出任何其他文字，不要用 markdown 代码块。"
    )
    full_prompt = "\n\n".join(prompt_parts)

    raw = ""
    last_err = None
    for attempt in range(2):
        try:
            raw = await _call_llm(full_prompt, COMMANDER_SYSTEM_PROMPT)
            if raw and raw.strip():
                print(f"[swarm-debug] 第 {attempt+1} 次成功，raw 长度={len(raw)}")
                break
            print(f"[swarm] LLM 返回空，重试第 {attempt+1} 次")
        except Exception as e:
            last_err = e
            print(f"[swarm] LLM 调用异常: {e}")

    if not raw or not raw.strip():
        err_msg = f"[SUMMARY]:任务拆解失败（LLM 返回空，请查看服务端日志）"
        _insert_message(conversation_id, err_msg, sender_agent_id=commander_id)
        return {"status": "error", "message": "LLM empty response"}

    steps = _parse_plan(raw)
    if not steps:
        if raw.strip() == "[DONE]":
            print("[swarm] 指挥官判定任务完成")
            return {"status": "done", "message": "任务完成", "task_id": None}


        print(f"[swarm] 拆解失败，LLM 原始返回: {raw[:500]!r}")
        task_id = f"noplan_{int(time.time() * 1000)}"
        task = {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
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
            "is_draft": False,
        }
        _pending[task_id] = task
        _save_pending(task)
        return {"status": "no_plan", "message": "无法拆解任务", "task_id": task_id}

    task_id = f"t_{int(time.time() * 1000)}"

    is_draft = bool(require_confirmation)
    task = {
        "task_id": task_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
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
        "is_draft": is_draft,
        "supervisor_id": supervisor_id or commander_id,
        "supervisor_run_id": supervisor_run_id,
    }
    _pending[task_id] = task
    _save_pending(task)

    if is_draft:
        draft_payload = {"task_id": task_id, "steps": steps}
        draft_msg = "[TASK_DRAFT]:" + json.dumps(draft_payload, ensure_ascii=False)
        _insert_message(conversation_id, draft_msg, sender_agent_id=commander_id)
        print(f"[swarm] 草稿模式：任务 {task_id} 已生成草稿，等待用户确认")
        return {
            "status": "draft",
            "task_id": task_id,
            "steps": steps,
            "conversation_id": conversation_id,
            "commander_id": commander_id,
            "executor_id": executor_id
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


def confirm_task(
    task_id: str,
    user_id: int,
    edited_steps: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    if task_id not in _pending:
        return {"status": "not_found", "message": "任务不存在"}

    task = _pending[task_id]
    if task["user_id"] != user_id:
        return {"status": "forbidden", "message": "无权确认该任务"}

    if not task.get("is_draft"):
        return {"status": "not_draft", "message": "该任务不是草稿"}

    if edited_steps:
        task["steps"] = edited_steps[:5]
        print(f"[swarm] 用户已编辑草稿 {task_id}，新步骤数: {len(edited_steps)}")

    task["is_draft"] = False
    _save_pending(task)

    task_payload = {"task_id": task_id, "steps": task["steps"]}
    task_msg = "[TASK]:" + json.dumps(task_payload, ensure_ascii=False)
    _insert_message(task["conversation_id"], task_msg, sender_agent_id=task["commander_id"])

    print(f"[swarm] 草稿 {task_id} 已确认，下发执行")
    return {
        "status": "confirmed",
        "task_id": task_id,
        "steps": task["steps"]
    }


def reject_task(task_id: str, user_id: int) -> Dict[str, Any]:
    if task_id not in _pending:
        return {"status": "not_found"}

    task = _pending[task_id]
    if task["user_id"] != user_id:
        return {"status": "forbidden"}

    _insert_message(task["conversation_id"], "[SUMMARY]:任务草稿已被用户取消。", sender_agent_id=task["commander_id"])
    del _pending[task_id]
    _delete_pending_from_db(task_id)
    return {"status": "rejected", "task_id": task_id}


def cancel_task(task_id: str, user_id: int) -> Dict[str, Any]:
    if task_id not in _pending:
        return {"status": "not_found", "message": "任务不存在或已完成"}

    task = _pending[task_id]
    if task["user_id"] != user_id:
        return {"status": "forbidden", "message": "无权取消该任务"}

    if task.get("no_plan"):
        del _pending[task_id]
        _delete_pending_from_db(task_id)
        return {"status": "cancelled", "task_id": task_id}

    task["cancelled"] = True
    _save_pending(task)
    _insert_message(task["conversation_id"], "[SUMMARY]:任务已取消。", sender_agent_id=task["commander_id"])
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
        if not task.get("no_plan") and not task.get("is_draft"):
            _insert_message(task["conversation_id"], "[SUMMARY]:已取消，并记录为误判。", sender_agent_id=task["commander_id"])
        del _pending[task_id]
        _delete_pending_from_db(task_id)

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
3. 只允许命令：dir / ls / tree / type / cat / head / tail / findstr / find / grep / where / echo / pwd / cd / whoami / hostname / wc
4. 禁止 copy / move / del / powershell / for / if / 重定向
5. 如果是"old_snippet 未找到"：先用 findstr 精确确认原文再 patch
6. 用 {{{{stepN}}}} 引用前序步骤的输出

只输出 JSON 数组，现在开始："""

    try:
        raw = await _call_llm(prompt, REPLAN_SYSTEM_PROMPT, max_tokens=config.REPLAN_MAX_TOKENS)
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
    task_id = payload.get("task_id")
    step_id = payload.get("step")
    if not task_id:
        return None

    if task_id not in _pending:
        task = _load_pending(task_id)
        if task:
            _pending[task_id] = task
        else:
            return None

    task = _pending[task_id]

    if task.get("cancelled"):
        del _pending[task_id]
        _delete_pending_from_db(task_id)
        return {"status": "cancelled", "task_id": task_id}

    original_step = None
    for s in task["steps"]:
        if s.get("step") == step_id:
            original_step = s
            break
    if original_step is None:
        original_step = {"step": step_id, "command": ""}

    status = payload.get("status", "unknown")
    output = payload.get("output", "")
    review_result, review_reason = review_step(original_step, status, output)

    task["done"].add(step_id)
    task["results"].append({
        "step": step_id,
        "description": payload.get("description", ""),
        "command": original_step.get("command", "") or original_step.get("module_id", ""),
        "status": status,
        "review": review_result,
        "reason": review_reason,
        "output": (output or "")[:300],
    })
    _save_pending(task)

    print(f"[swarm] step {step_id} 审核: {review_result} | {review_reason}")

    if review_result == "retry":
        try:
            fail_cmd = original_step.get("command", "") or original_step.get("module_id", "")
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

    try:
        _log_review(
            task_id=task_id,
            conversation_id=conversation_id,
            step_id=step_id,
            command=original_step.get("command", "") or original_step.get("module_id", ""),
            exec_status=status,
            review_result=review_result,
            review_reason=review_reason,
            output=output
        )
    except Exception as e:
        print(f"[swarm] 审核日志入库失败: {e}")

    if len(task["done"]) >= len(task["steps"]):
        failed = [r for r in task["results"] if r.get("review") == "retry"]
        blocked = [r for r in task["results"] if r.get("status") == "blocked"]

        if blocked:
            print(f"[swarm] 发现 {len(blocked)} 个被拒绝的命令，跳过重拆")
            summary = await _summarize(task["user_text"], task["results"], user_id=task["user_id"], task_id=task_id)
            _insert_message(conversation_id, f"[SUMMARY]:{summary}", sender_agent_id=_summary_sender(task))
            del _pending[task_id]
            _delete_pending_from_db(task_id)
            _run_id = task.get("supervisor_run_id")
            # answer tool output => finish directly
            from . import supervisor_service as _sv_a
            _has_answer = any(
                (r.get('module_id') == 'answer' or r.get('command') == 'answer')
                and r.get('status') == 'success'
                for r in task['results']
            )
            if _has_answer:
                print('[supervisor] run ' + str(_run_id) + ' completed')
                _sv_a.finish_run(_run_id, 'completed')
                return {"status": "completed", "task_id": task_id, "summary": "answer 工具产出"}

            if _run_id:
                # v0.18.1: 单步任务全成功 -> 直接完成，不续轮
                _is_simple = (len(task.get('steps', [])) == 1 and len(task.get('results', [])) == 1 and all(r.get('review') != 'retry' for r in task.get('results', [])))
                _s1_chk = task.get('steps', [{}])[0] if task.get('steps') else {}
                _s1_mod = _s1_chk.get('module_id', '') or ''
                _s1_type = _s1_chk.get('type', 'command')
                _is_hands_on = (_s1_type == 'harness' and _s1_mod in ('file_patch', 'run_python', 'verify_patch'))
                if not _is_hands_on:
                    _is_simple = False
                if _is_simple:
                    from . import supervisor_service as _sv_done
                    _sv_done.finish_run(_run_id, 'completed')
                    print(f"[supervisor] run {_run_id} 单步任务成功，直接完成")
                    return {'status': 'completed', 'task_id': task_id, 'summary': summary}
                try:
                    from . import supervisor_service
                    _steps_text = ' | '.join([str(r.get('step')) + '.' + str(r.get('description', ''))[:40] for r in task['results']])
                    _exec_text = chr(10).join([str(r.get('step')) + '.[' + str(r.get('status', '?')) + '] ' + str(r.get('command') or r.get('module_id') or '')[:80] for r in task['results']])
                    _has_core_change = False
                    try:
                        for _r in task['results']:
                            _cmd = str(_r.get('command') or '')
                            _desc = str(_r.get('description') or '')
                            _params = str(_r.get('params') or '')
                            if _cmd == 'file_patch' and ('core/' in _desc or 'core/' in _params or 'core/' in str(_r.get('output') or '')):
                                _has_core_change = True
                                break
                    except Exception:
                        pass
                    if _has_core_change:
                        try:
                            supervisor_service.finish_run(_run_id, 'restart_pending')
                            print(f"[supervisor] run {_run_id} 标记 restart_pending（改了 core/，需重启验证）")
                        except Exception as _e:
                            print(f"[supervisor] 标记 restart_pending 失败: {_e}")
                        return {"status": "restart_pending", "task_id": task_id}
                    _review = None
                    if getattr(supervisor_service, 'USE_STRUCTURED_REVIEW', False):
                        _review = await supervisor_service.task_summarizer(task)
                    _continue, _ = await supervisor_service.check_and_continue(_run_id, summary, plan_text=_steps_text, exec_text=_exec_text, review=_review)
                    if _continue:
                        if _review and getattr(supervisor_service, 'USE_STRUCTURED_REVIEW', False):
                            if _review.get('goal_achieved'):
                                _decision = {'action': 'done'}
                            else:
                                _decision = {'action': 'execute', 'task': '[MODIFY] ' + (_review.get('next_hint') or '继续完成目标')}
                        else:
                            _decision = await supervisor_service.decide_next_step(_run_id)
                        if _decision and _decision.get("action") == "done":
                            supervisor_service.finish_run(_run_id, "completed")
                            print(f"[supervisor] run {_run_id} 已完成（调度者判定）")
                        elif _decision and _decision.get("task"):
                            print(f"[supervisor] run {_run_id} 继续下一轮（blocked）：{_decision.get('action')}")
                            _insert_message(conversation_id, '[SUPERVISOR_PROGRESS]:🧠 第 ' + str((task.get('current_round') or 0) + 1) + ' 轮', sender_agent_id=_summary_sender(task))
                            _next_result = await plan_task(
                                user_id=task["user_id"],
                                conversation_id=conversation_id,
                                user_input=_decision["task"],
                                supervisor_id=task.get("supervisor_id"),
                                supervisor_run_id=_run_id,
                            )
                            if isinstance(_next_result, dict) and _next_result.get("status") == "done":
                                supervisor_service.finish_run(_run_id, "completed")
                        else:
                            supervisor_service.finish_run(_run_id, "completed")
                    else:
                        supervisor_service.finish_run(_run_id, "completed")
                except Exception as e:
                    print(f"[supervisor] 续轮失败: {e}")
                    try:
                        supervisor_service.finish_run(_run_id, "error")
                    except Exception:
                        pass
            return {"status": "completed_with_blocks", "task_id": task_id}

        if failed and task["retry_count"] < 2:
            task["retry_count"] += 1
            print(f"[swarm] 发现 {len(failed)} 个失败步骤，触发重拆 (第 {task['retry_count']} 次)")
            new_steps = await replan_failed_steps(task)

            if new_steps:
                task["results"] = []
                task["done"] = set()
                task["steps"] = new_steps
                _save_pending(task)

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
                summary = await _summarize(task["user_text"], task["results"], user_id=task["user_id"], task_id=task_id)
                _insert_message(conversation_id, f"[SUMMARY]:{summary}", sender_agent_id=_summary_sender(task))
                del _pending[task_id]
                _delete_pending_from_db(task_id)
                return {"status": "completed_with_failures", "task_id": task_id}
        else:
            if failed:
                print(f"[swarm] 重试次数已达上限，标记失败并汇总")
            else:
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

            summary = await _summarize(task["user_text"], task["results"], user_id=task["user_id"], task_id=task_id)
            _insert_message(conversation_id, f"[SUMMARY]:{summary}", sender_agent_id=_summary_sender(task))
            del _pending[task_id]
            _delete_pending_from_db(task_id)

            _run_id = task.get("supervisor_run_id")
            # answer tool output => finish directly
            from . import supervisor_service as _sv_a
            _has_answer = any(
                (r.get('module_id') == 'answer' or r.get('command') == 'answer')
                and r.get('status') == 'success'
                for r in task['results']
            )
            if _has_answer:
                print('[supervisor] run ' + str(_run_id) + ' completed')
                _sv_a.finish_run(_run_id, 'completed')
                return {"status": "completed", "task_id": task_id, "summary": "answer 工具产出"}

            if _run_id:
                # v0.18.1: 单步任务全成功 -> 直接完成，不续轮
                _is_simple = (len(task.get('steps', [])) == 1 and len(task.get('results', [])) == 1 and all(r.get('review') != 'retry' for r in task.get('results', [])))
                _s1_chk = task.get('steps', [{}])[0] if task.get('steps') else {}
                _s1_mod = _s1_chk.get('module_id', '') or ''
                _s1_type = _s1_chk.get('type', 'command')
                _is_hands_on = (_s1_type == 'harness' and _s1_mod in ('file_patch', 'run_python', 'verify_patch'))
                if not _is_hands_on:
                    _is_simple = False
                if _is_simple:
                    from . import supervisor_service as _sv_done
                    _sv_done.finish_run(_run_id, 'completed')
                    print(f"[supervisor] run {_run_id} 单步任务成功，直接完成")
                    return {'status': 'completed', 'task_id': task_id, 'summary': summary}
                try:
                    from . import supervisor_service
                    _steps_text = ' | '.join([str(r.get('step')) + '.' + str(r.get('description', ''))[:40] for r in task['results']])
                    _exec_text = chr(10).join([str(r.get('step')) + '.[' + str(r.get('status', '?')) + '] ' + str(r.get('command') or r.get('module_id') or '')[:80] for r in task['results']])
                    _has_core_change = False
                    try:
                        for _r in task['results']:
                            _cmd = str(_r.get('command') or '')
                            _desc = str(_r.get('description') or '')
                            _params = str(_r.get('params') or '')
                            if _cmd == 'file_patch' and ('core/' in _desc or 'core/' in _params or 'core/' in str(_r.get('output') or '')):
                                _has_core_change = True
                                break
                    except Exception:
                        pass
                    if _has_core_change:
                        try:
                            supervisor_service.finish_run(_run_id, 'restart_pending')
                            print(f"[supervisor] run {_run_id} 标记 restart_pending（改了 core/，需重启验证）")
                        except Exception as _e:
                            print(f"[supervisor] 标记 restart_pending 失败: {_e}")
                        return {"status": "restart_pending", "task_id": task_id}
                    _review = None
                    if getattr(supervisor_service, 'USE_STRUCTURED_REVIEW', False):
                        _review = await supervisor_service.task_summarizer(task)
                    _continue, _ = await supervisor_service.check_and_continue(_run_id, summary, plan_text=_steps_text, exec_text=_exec_text, review=_review)
                    if _continue:
                        if _review and getattr(supervisor_service, 'USE_STRUCTURED_REVIEW', False):
                            if _review.get('goal_achieved'):
                                _decision = {'action': 'done'}
                            else:
                                _decision = {'action': 'execute', 'task': '[MODIFY] ' + (_review.get('next_hint') or '继续完成目标')}
                        else:
                            _decision = await supervisor_service.decide_next_step(_run_id)
                        if _decision and _decision.get("action") == "done":
                            supervisor_service.finish_run(_run_id, "completed")
                            print(f"[supervisor] run {_run_id} 已完成（调度者判定）")
                        elif _decision and _decision.get("task"):
                            print(f"[supervisor] run {_run_id} 继续下一轮：{_decision.get('action')} - {_decision.get('task', '')[:50]}")
                            _next_result = await plan_task(
                                user_id=task["user_id"],
                                conversation_id=conversation_id,
                                user_input=_decision["task"],
                                supervisor_id=task.get("supervisor_id"),
                                supervisor_run_id=_run_id,
                            )
                            if isinstance(_next_result, dict) and _next_result.get("status") == "done":
                                supervisor_service.finish_run(_run_id, "completed")
                        else:
                            supervisor_service.finish_run(_run_id, "completed")
                    else:
                        supervisor_service.finish_run(_run_id, "completed")
                        print(f"[supervisor] run {_run_id} 已完成（轮次用尽）")
                except Exception as e:
                    print(f"[supervisor] 续轮失败: {e}")
                    try:
                        supervisor_service.finish_run(_run_id, "error")
                    except Exception:
                        pass

            return {"status": "completed", "task_id": task_id, "summary": summary}

    return {
        "status": "in_progress",
        "task_id": task_id,
        "done": len(task["done"]),
        "total": len(task["steps"]),
        "review": review_result,
    }


def _summary_sender(task):
    """优先用 supervisor_id，回退 commander_id"""
    return task.get("supervisor_id") or task.get("commander_id")



async def _summarize(user_text: str, results: List[Dict[str, Any]], user_id: int = None, task_id: str = None) -> str:
    # P0：记录经验 pattern（静默失败，不阻塞主流程）
    try:
        if user_id and task_id and results:
            from . import pattern_service
            n = pattern_service.record_pattern(user_id, task_id, "dev", results)
            if n:
                print(f"[swarm] 已记录 {n} 条 pattern")
    except Exception as e:
        print(f"[swarm] pattern 记录失败（已忽略）: {e}")

    # 自动快照（方案 C：仅当任务包含 file_patch 成功步骤时）
    try:
        _has_patch = any(
            r.get("command") == "file_patch" and r.get("status") == "success"
            for r in results
        )
        if _has_patch and task_id:
            import subprocess as _sp
            import os as _os
            _repo = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
            _msg = f"auto: {task_id}"
            _sp.run("git add -A", shell=True, cwd=_repo, capture_output=True, encoding="utf-8", errors="replace")
            _r = _sp.run(f'git commit -m "{_msg}"', shell=True, cwd=_repo, capture_output=True, encoding="utf-8", errors="replace")
            if _r.returncode == 0:
                print(f"[swarm] 已自动快照: {_msg}")
            else:
                print(f"[swarm] 自动快照跳过")
    except Exception as _e:
        print(f"[swarm] 自动快照失败: {_e}")


    # 写入执行笔记（v0.17.0）
    try:
        if user_id and task_id and results:
            from . import project_service
            _digest = ' | '.join([str(r.get('step')) + '.' + str(r.get('status', '?')) for r in results[:5]])
            _outcome = 'success' if all(r.get('review') != 'retry' for r in results) else 'partial'
            _preview = ' | '.join([str(r.get('description', ''))[:30] for r in results[:3]])
            project_service.import_execution_note(
                task_id=task_id, user_id=user_id,
                user_input=user_text, summary=_preview,
                steps_digest=_digest, outcome=_outcome
            )
    except Exception as e:
        print(f"[swarm] 执行笔记写入失败: {e}")


    result_text = "\n".join(
        f"步骤{r['step']}({r['description']}): {r['status']} [审核:{r.get('review','?')}]"
        for r in results
    )
    prompt = f"用户任务：{user_text}\n\n执行结果：\n{result_text}\n\n请用一句话总结这次任务的结果。"
    try:
        return await _call_llm(prompt, SUMMARY_SYSTEM_PROMPT, max_tokens=config.SUMMARY_MAX_TOKENS)
    except Exception:
        return "任务执行完成。"

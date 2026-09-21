import json
from datetime import datetime
from ..db import db_cursor
from . import credit_service

MAX_ROUNDS = 10
CREDITS_PER_ROUND = 2
USE_STRUCTURED_REVIEW = True



def build_context(user_id, conversation_id, query):
    parts = []
    try:
        _skip_prefixes = ('[TASK]:', '[STEP_DONE]:', '[SUMMARY]:', '[TASK_DRAFT]:', '[RETRY_TASK]:', '[RED_PACKET]:', '[IMAGE]:')
        with db_cursor() as cur:
            cur.execute(
                "SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 50",
                (conversation_id,),
            )
            rows = cur.fetchall()
        _count = 0
        for row in reversed(rows):
            sender = row["sender"] if "sender" in row.keys() else "?"
            content = row["content"] or ""
            if any(content.startswith(p) for p in _skip_prefixes):
                continue
            if not content.strip():
                continue
            parts.append(sender + "：" + content[:100])
            _count += 1
            if _count >= 3:
                break
    except Exception as e:
        print("[supervisor] build_context 历史读取失败: " + str(e))
    try:
        from . import memory_service
        mems = memory_service.recall(user_id, query, 2)
        for m in (mems or []):
            mc = (m.get("content") or "")[:100] if isinstance(m, dict) else ""
            if mc:
                parts.append("记忆：" + mc)
    except Exception as e:
        print("[supervisor] build_context 记忆读取失败: " + str(e))
    return "\n".join(parts)


# (旧版 build_context 已删除，见上方新版本)



# (旧版 build_context 已删除)



def _dict(row):
    return dict(row) if row else None


def get_run(run_id):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM supervisor_runs WHERE id=?', (run_id,))
        return _dict(cur.fetchone())


def get_active_run(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM supervisor_runs WHERE user_id=? AND status='running' ORDER BY id DESC LIMIT 1", (user_id,))
        return _dict(cur.fetchone())


def create_run(user_id, conversation_id, supervisor_id, goal):
    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history) VALUES (?, ?, ?, ?, 'running', 0, ?, '[]')", (user_id, conversation_id, supervisor_id, goal, MAX_ROUNDS))
        return cur.lastrowid


def cancel_run(run_id, user_id):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status='cancelled', finished_at=? WHERE id=? AND user_id=? AND status='running'", (datetime.now().isoformat(), run_id, user_id))
        return cur.rowcount > 0


def finish_run(run_id, status='completed'):
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE supervisor_runs SET status=?, finished_at=? WHERE id=?', (status, datetime.now().isoformat(), run_id))


def record_round(run_id, plan_summary, exec_summary):
    run = get_run(run_id)
    if not run:
        return
    try:
        history = json.loads(run['history'] or '[]')
    except Exception:
        history = []
    new_round = (run['current_round'] or 0) + 1
    history.append({'round': new_round, 'plan': (plan_summary or '')[:300], 'exec': (exec_summary or '')[:500], 'at': datetime.now().isoformat()})
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE supervisor_runs SET history=?, current_round=? WHERE id=?', (json.dumps(history, ensure_ascii=False), new_round, run_id))


def deduct_round(run_id):
    run = get_run(run_id)
    if not run:
        return False
    try:
        bal = credit_service.get_balance(run['user_id'])
    except Exception as e:
        print('[supervisor] 查询余额失败: ' + str(e))
        return False
    if bal < CREDITS_PER_ROUND:
        return False
    try:
        credit_service.deduct_credits(run['user_id'], CREDITS_PER_ROUND, reason='自主模式第' + str((run['current_round'] or 0) + 1) + '轮')
    except Exception as e:
        print('[supervisor] 扣分失败: ' + str(e))
        return False
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE supervisor_runs SET credits_used = credits_used + ? WHERE id=?', (CREDITS_PER_ROUND, run_id))
    return True


def build_next_input(run_id):
    run = get_run(run_id)
    if not run:
        return None
    try:
        history = json.loads(run['history'] or '[]')
    except Exception:
        history = []
    if not history:
        return run['goal']
    lines = ['目标：' + run['goal'], '', '已完成：']
    for h in history[-3:]:
        lines.append('第 ' + str(h['round']) + ' 轮：' + (h.get('plan', '') or '')[:80])
        lines.append('  结果：' + (h.get('exec', '') or '')[:200])
    lines.append('')
    lines.append('请判断目标是否已完成。如果已完成，只输出 [DONE]。否则输出下一步要做的任务（一句话）。')
    return chr(10).join(lines)


async def decide_next_step(run_id):
    import openai
    import asyncio
    from .. import config
    run = get_run(run_id)
    if not run:
        return None
    try:
        history = json.loads(run['history'] or '[]')
    except Exception:
        history = []
    history_text = ''
    for h in history[-5:]:
        history_text += '第 ' + str(h.get('round', '?')) + ' 轮：' + (h.get('plan') or '')[:80] + chr(10)
        history_text += '  结果：' + (h.get('exec') or '')[:300] + chr(10)
    prompt = '你是 SASES 自主调度者。目标：' + run['goal'] + chr(10) + chr(10) + '已完成：' + chr(10) + (history_text or '(无)') + chr(10) + '可用工具：file_read / dir_tree / grep_code / file_patch / harness_reload / git_ops / web_fetch' + chr(10) + chr(10) + '请判断下一步，只输出 JSON：{"action": "probe" 或 "build_harness" 或 "execute" 或 "done", "task": "一句话描述"}' + chr(10) + 'probe=先读代码；build_harness=缺工具先建；execute=可以改代码；done=目标达成' + chr(10) + '注意：如果最近的执行结果里有 blocked 或 retry，说明上一步失败，不能判定 done，应继续 probe 或 execute 修正。' + chr(10) + '另外：只有确认用户目标的所有子任务都完成，才能判定 done。只改了 1 处不代表全部完成时，应继续 execute 改其他地方。判断标准：回顾原始目标的每一个关键词，逐一确认是否已实现。' + chr(10) + '关键规则：如果用户目标包含实现/打通/改/加/建/修复等动作词，而 history 里从来没有出现过 file_patch 或 harness_reload，说明只做了探测没做实际修改，此时不能 done，必须输出 execute。'
    client = openai.OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL, timeout=30)
    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=config.MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.3,
            max_tokens=200
        )
        raw = resp.choices[0].message.content.strip()
        i = raw.find('{')
        j = raw.rfind('}')
        if i >= 0 and j > i:
            _result = json.loads(raw[i:j+1])
            _goal = run.get('goal', '')
            _action_words = ['实现', '打通', '改', '加', '建', '修复', '增加', '添加', '删除', '创建', '完成']
            _need_action = any(w in _goal for w in _action_words)
            _history_str = json.dumps(history, ensure_ascii=False)
            _has_patch = '[success] file_patch' in _history_str or '[success]harness_reload' in _history_str or '[success] harness_reload' in _history_str
            if _need_action and not _has_patch and _result.get('action') == 'done':
                print('[supervisor] 强制覆盖 done → execute（历史无 file_patch）')
                _result['action'] = 'execute'
                _result['task'] = '根据前面探测结果实际修改代码，完成目标：' + _goal[:100]
            return _result
        return {'action': 'done', 'task': 'parse failed'}
    except Exception as e:
        print('[supervisor] decide_next_step 失败: ' + str(e))
        return {'action': 'done', 'task': 'LLM failed'}



async def check_and_continue(run_id, last_summary, plan_text=None, exec_text=None):
    import openai
    from .. import config
    run = get_run(run_id)
    if not run or run['status'] != 'running':
        return False, None
    record_round(run_id, plan_text or run.get('goal', ''), exec_text or last_summary)
    run = get_run(run_id)
    if not run or (run['current_round'] or 0) >= (run['max_rounds'] or 5):
        return False, None
    if not deduct_round(run_id):
        finish_run(run_id, status='insufficient_credits')
        return False, None
    return True, build_next_input(run_id)

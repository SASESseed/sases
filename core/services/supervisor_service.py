import json
from datetime import datetime
from ..db import db_cursor
from . import credit_service

MAX_ROUNDS = 10
CREDITS_PER_ROUND = 5


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


async def check_and_continue(run_id, last_summary):
    import openai
    from .. import config
    run = get_run(run_id)
    if not run or run['status'] != 'running':
        return False, None
    record_round(run_id, run.get('goal', ''), last_summary)
    run = get_run(run_id)
    if not run or (run['current_round'] or 0) >= (run['max_rounds'] or 5):
        return False, None
    if not deduct_round(run_id):
        finish_run(run_id, status='insufficient_credits')
        return False, None
    return True, build_next_input(run_id)

import json
from datetime import datetime
from ..db import db_cursor
from . import credit_service

MAX_ROUNDS = 10
CREDITS_PER_ROUND = 2
USE_STRUCTURED_REVIEW = True



import time as _ctx_time
_CTX_CACHE = {}
_CTX_TTL = 5
_CTX_MAX = 200


def _ctx_key(user_id, conversation_id, mode, supervisor_id, query):
    return (user_id, conversation_id, mode, supervisor_id, (query or '')[:50])


def import_file_to_kb(file_url, original_name, user_id):
    """把用户上传的文件导入项目库"""
    import os as _os_i
    try:
        from . import project_service
    except Exception as e:
        return {'success': False, 'error': 'project_service import failed: ' + str(e)}
    fn = (file_url or '').split('/')[-1]
    if not fn:
        return {'success': False, 'error': 'no filename'}
    fp = _os_i.path.join('uploads', fn)
    if not _os_i.path.exists(fp):
        return {'success': False, 'error': 'file not found'}
    try:
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
    except Exception as e:
        return {'success': False, 'error': 'read failed: ' + str(e)}
    if not raw:
        return {'success': False, 'error': 'empty file'}
    src = original_name or fn
    try:
        n = project_service.import_document(src, 'v1.0-upload', raw, user_id=user_id)
    except Exception as e:
        return {'success': False, 'error': 'import failed: ' + str(e)}
    return {'success': True, 'chunks': n, 'file': src}



def build_context(user_id, conversation_id, query, mode='execute', supervisor_id=None):
    _ck = _ctx_key(user_id, conversation_id, mode, supervisor_id, query)
    _ct = _ctx_time.time()
    if _ck in _CTX_CACHE:
        _cts, _cval = _CTX_CACHE[_ck]
        if _ct - _cts < _CTX_TTL:
            print('[supervisor] build_context 缓存命中')
            return _cval
        else:
            del _CTX_CACHE[_ck]
    parts = []
    try:
        _hard_skip = ('[TASK]:', '[TASK_DRAFT]:', '[RETRY_TASK]:', '[RED_PACKET]:', '[IMAGE]:')
        with db_cursor() as cur:
            cur.execute(
                "SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 80",
                (conversation_id,),
            )
            rows = cur.fetchall()
        _chat_lines = []
        _summary_line = None
        _step_lines = []
        for row in reversed(rows):
            sender = row["sender"] if "sender" in row.keys() else "?"
            content = row["content"] or ""
            if any(content.startswith(p) for p in _hard_skip):
                continue
            if content.startswith('[SUMMARY]:'):
                _summary_line = "任务总结：" + content[10:][:150]
                continue
            if content.startswith('[STEP_DONE]:'):
                try:
                    import json as _json
                    d = _json.loads(content[12:])
                    desc = (d.get('description') or '')[:40]
                    status = d.get('status', '?')
                    out = (d.get('output') or '')[:80]
                    _step_lines.append(str(d.get('step', '?')) + '.[' + status + '] ' + desc + ' → ' + out)
                except Exception:
                    pass
                continue
            if not content.strip():
                continue
            _chat_lines.append(sender + "：" + content[:100])
        for line in _chat_lines[-2:]:
            parts.append(line)
        if _step_lines:
            parts.append("执行步骤：" + " | ".join(_step_lines[-3:]))
        if _summary_line:
            parts.append(_summary_line)
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
    if mode == 'chat':
        _allow_project = bool(supervisor_id) and supervisor_id.startswith('sases_assistant')
        if _allow_project:
            try:
                from . import project_service
                _chunks = project_service.retrieve_project_chunks(query, top_k=3, user_id=user_id)
                if _chunks:
                    _pctx = project_service.format_chunks_for_prompt(_chunks)
                    if _pctx:
                        parts.append(_pctx[:1000])
            except Exception as _e:
                print('[supervisor] chat mode 项目库失败: ' + str(_e))
        try:
            with db_cursor() as _cur:
                _cur.execute('SELECT user_input, summary FROM execution_notes WHERE user_id=? ORDER BY id DESC LIMIT 5', (user_id,))
                _rows = _cur.fetchall()
            if _rows:
                _lines = []
                for _r in _rows[:3]:
                    _ui = (_r['user_input'] if 'user_input' in _r.keys() else '') or ''
                    _sm = (_r['summary'] if 'summary' in _r.keys() else '') or ''
                    if _ui:
                        _lines.append('- ' + _ui[:60] + ' → ' + _sm[:60])
                if _lines:
                    parts.append('【历史任务】' + chr(10) + chr(10).join(_lines))
        except Exception as _e:
            print('[supervisor] chat mode 执行笔记失败: ' + str(_e))
        try:
            from . import pattern_service
            _pats = pattern_service.retrieve_patterns(query, domain='dev', top_k=3)
            if _pats:
                _plines = []
                for _p in _pats:
                    _ev = (_p.get('evidence') or '')[:80] if isinstance(_p, dict) else ''
                    if _ev:
                        _plines.append('- ' + _ev)
                if _plines:
                    parts.append('【相关经验】' + chr(10) + chr(10).join(_plines))
        except Exception as _e:
            print('[supervisor] chat mode 经验库失败: ' + str(_e))


    _result = "\n".join(parts)
    _CTX_CACHE[_ck] = (_ct, _result)
    if len(_CTX_CACHE) > _CTX_MAX:
        _sorted_keys = sorted(_CTX_CACHE.items(), key=lambda x: x[1][0])[:50]
        for _k, _ in _sorted_keys:
            _CTX_CACHE.pop(_k, None)
    return _result


# (旧版 build_context 已删除，见上方新版本)



# (旧版 build_context 已删除)



def _dict(row):
    return dict(row) if row else None


def get_run(run_id):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM supervisor_runs WHERE id=?', (run_id,))
        return _dict(cur.fetchone())


def create_proposed_run(user_id, conversation_id, supervisor_id, goal):
    """创建 proposed 状态的 run，等用户确认"""
    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history) VALUES (?, ?, ?, ?, 'proposed', 0, ?, '[]')", (user_id, conversation_id, supervisor_id, goal, MAX_ROUNDS))
        return cur.lastrowid


def confirm_run(run_id, user_id):
    """用户确认，改状态为 running"""
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status='running' WHERE id=? AND user_id=? AND status='proposed'", (run_id, user_id))
        return cur.rowcount > 0


def reject_run(run_id, user_id):
    """用户拒绝，改状态为 rejected"""
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status='rejected', finished_at=? WHERE id=? AND user_id=? AND status='proposed'", (datetime.now().isoformat(), run_id, user_id))
        return cur.rowcount > 0


def get_proposed_run(user_id, conversation_id=None):
    """取最近一条 proposed run"""
    with db_cursor() as cur:
        if conversation_id:
            cur.execute("SELECT * FROM supervisor_runs WHERE user_id=? AND conversation_id=? AND status='proposed' ORDER BY id DESC LIMIT 1", (user_id, conversation_id))
        else:
            cur.execute("SELECT * FROM supervisor_runs WHERE user_id=? AND status='proposed' ORDER BY id DESC LIMIT 1", (user_id,))
        return _dict(cur.fetchone())



def get_active_run(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM supervisor_runs WHERE user_id=? AND status IN ('running', 'proposed') ORDER BY id DESC LIMIT 1", (user_id,))
        run = _dict(cur.fetchone())

    # 只有 running 状态才检查超时；proposed 等用户确认，不自动清
    if run and run.get('status') == 'running':
        try:
            from datetime import timedelta
            history = json.loads(run['history'] or '[]')
            last_at = None
            if history:
                last_at = history[-1].get('at')
            if not last_at:
                last_at = run.get('created_at')
            if last_at:
                last_dt = datetime.fromisoformat(last_at.replace('Z', '').replace(' ', 'T'))
                if datetime.now() - last_dt > timedelta(minutes=30):
                    print('[supervisor] run ' + str(run['id']) + ' 超时 30 分钟，自动中断')
                    finish_run(run['id'], 'timeout')
                    return None
        except Exception as e:
            print('[supervisor] 超时检测失败: ' + str(e))

    return run


def create_run(user_id, conversation_id, supervisor_id, goal):
    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history) VALUES (?, ?, ?, ?, 'running', 0, ?, '[]')", (user_id, conversation_id, supervisor_id, goal, MAX_ROUNDS))
        return cur.lastrowid


def cancel_run(run_id, user_id):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE supervisor_runs SET status='cancelled', finished_at=? WHERE id=? AND user_id=? AND status IN ('running', 'proposed')", (datetime.now().isoformat(), run_id, user_id))
        _ok = cur.rowcount > 0
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE swarm_pending_tasks SET cancelled=1, status='cancelled', updated_at=? WHERE supervisor_run_id=? AND status IN ('pending', 'running')", (datetime.now().isoformat(), run_id))
            _n = cur.rowcount
            if _n:
                print('[supervisor] cancel_run ' + str(run_id) + ' 同时取消 ' + str(_n) + ' 个 swarm 任务')
    except Exception as e:
        print('[supervisor] cancel_run 中断 swarm 失败: ' + str(e))
    return _ok


def finish_run(run_id, status='completed'):
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE supervisor_runs SET status=?, finished_at=? WHERE id=?', (status, datetime.now().isoformat(), run_id))


# (旧版 build_context 已删除，用第 12 行版本)

def record_round(run_id, plan_summary, exec_summary, review=None):
    run = get_run(run_id)
    if not run:
        return
    try:
        history = json.loads(run['history'] or '[]')
    except Exception:
        history = []
    new_round = (run['current_round'] or 0) + 1
    history.append({'round': new_round, 'plan': (plan_summary or '')[:300], 'exec': (exec_summary or '')[:500], 'review': review, 'at': datetime.now().isoformat()})
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


async def task_summarizer(task):
    import openai
    import asyncio
    from .. import config
    user_text = task.get('user_text', '')
    _orig_run_id = task.get('supervisor_run_id')
    if _orig_run_id:
        try:
            _orig_run = get_run(_orig_run_id)
            if _orig_run and _orig_run.get('goal'):
                user_text = _orig_run['goal']
        except Exception:
            pass
    results = task.get('results', [])
    steps = []
    for r in results:
        step = r.get('step', '?')
        desc = (r.get('description') or '')[:50]
        status = r.get('status', '?')
        cmd = r.get('command') or r.get('module_id') or ''
        out = (r.get('output') or r.get('answer') or '')[:300]
        steps.append(str(step) + '.[' + str(status) + '] ' + desc + ' | ' + str(cmd)[:50] + ' | ' + out)
    # 代码级规则：命中未完成/待续字眼，直接判 false，不依赖 LLM
    _all_text = (user_text or '') + ' | ' + ' | '.join(steps)
    _suspicious_kws = ['剩余', '请继续', '请分批', '请再发', '下一步', '未完成', '待完成',
                       'rolled_back', 'verify fail', '已回滚', '请回复',
                       '请确认', '请检查', '未做', '待做', '请用户', '需要用户', '请先', '请提供']
    _hit = [kw for kw in _suspicious_kws if kw in _all_text]
    if _hit:
        print('[supervisor] task_summarizer 代码规则命中: ' + ','.join(_hit))
        return {'goal_achieved': False, 'goal_reason': '代码规则命中可疑字眼: ' + ','.join(_hit), 'missing': _hit, 'next_hint': '请继续完成剩余部分'}


    prompt = '你是任务完成度评估器。用户目标：' + user_text + '。执行步骤：' + chr(10).join(steps) + '。请只输出 JSON：{"goal_achieved": true 或 false, "goal_reason": "理由", "missing": ["未完成项"], "next_hint": "下一步具体命令"}。判断规则：第一，逐条列出原始目标里的每一个要求（编号1/2/3/4），逐一核对是否真的通过 file_patch/file_read/run_python 等工具执行过，没执行过的放入missing。第二，如果执行结果里出现"剩余""请继续""请分批""请再发""下一步""未完成"等字眼，强制 goal_achieved=false。第三，把用户目标拆成子任务逐一核对，不因某一子任务完成就判整体完成。目标含总结/回答/分析/说明，必须有文字产出。目标含改/加/实现/修复，必须有成功 file_patch。目标含读/查看/列出，有 file_read 或 dir 即可。next_hint 必须具体写清工具+文件路径+动作，不许写重新探测。'
    client = openai.OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL, timeout=30)
    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=config.MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.2,
            max_tokens=3000
        )
        raw = resp.choices[0].message.content.strip()
        i = raw.find('{')
        j = raw.rfind('}')
        if i >= 0 and j > i:
            return json.loads(raw[i:j+1])
        return {'goal_achieved': False, 'goal_reason': 'parse failed', 'next_hint': '重新探测'}
    except Exception as e:
        print('[supervisor] task_summarizer 失败: ' + str(e))
        return {'goal_achieved': False, 'goal_reason': 'LLM failed', 'next_hint': '重新探测'}



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
    try:
        from .. import harness_runtime as _hr
        _tools = _hr.harness_runtime.list_tools()
        _names = ' / '.join([getattr(t, 'module_id', '') for t in _tools if getattr(t, 'module_id', '')])
        _tool_line = '可用工具：' + _names
    except Exception:
        _tool_line = '可用工具：file_read / file_patch'
    prompt = '你是 SASES 自主调度者。目标：' + run['goal'] + chr(10) + chr(10) + '已完成：' + chr(10) + (history_text or '(无)') + chr(10) + _tool_line + chr(10) + chr(10) + '请判断下一步，只输出 JSON：{"action": "probe" 或 "build_harness" 或 "execute" 或 "done", "task": "一句话描述"}' + chr(10) + 'probe=先读代码；build_harness=缺工具先建；execute=可以改代码；done=目标达成' + chr(10) + '注意：如果最近的执行结果里有 blocked 或 retry，说明上一步失败，不能判定 done，应继续 probe 或 execute 修正。' + chr(10) + '另外：只有确认用户目标的所有子任务都完成，才能判定 done。只改了 1 处不代表全部完成时，应继续 execute 改其他地方。判断标准：回顾原始目标的每一个关键词，逐一确认是否已实现。' + chr(10) + '关键规则：如果用户目标包含实现/打通/改/加/建/修复等动作词，而 history 里从来没有出现过 file_patch 或 harness_reload，说明只做了探测没做实际修改，此时不能 done，必须输出 execute。' + chr(10) + '补充规则：如果 history 里已经读到目标文件的具体行号/代码片段/参数格式，说明探测够了，下一步必须输出 execute，不要再 probe。饱和判定：如果最近 2 轮的 exec 内容高度相似（同一路径、同一文件、同一结果），说明探测饱和，应输出 done。不要因为没总结就继续探测。'
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



# (重复的 build_context 已删除，用第 12 行的版本)


def signal_restart(run_id, reason=''):
    try:
        import time
        content = f"run_id={run_id}|reason={reason}|at={int(time.time())}"
        with open('restart_signal.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[supervisor] signal_restart failed: {e}")
        return False


async def resume_restart_pending_runs():
    import asyncio
    import sqlite3
    await asyncio.sleep(10)
    try:
        from core.services import swarm_service
        conn = sqlite3.connect('sases.db')
        cur = conn.cursor()
        cur.execute("SELECT run_id, conversation_id, user_id, goal FROM supervisor_runs WHERE status='restart_pending' LIMIT 5")
        rows = cur.fetchall()
        for run_id, conversation_id, user_id, goal in rows:
            cur.execute("UPDATE supervisor_runs SET status='running' WHERE run_id=?", (run_id,))
            conn.commit()
            cur2 = conn.cursor()
            cur2.execute("SELECT plan FROM supervisor_history WHERE run_id=? ORDER BY id DESC LIMIT 1", (run_id,))
            r = cur2.fetchone()
            last_plan = r[0] if r else ''
            text = f"继续未完成的任务。原目标：{goal}。上一轮完成：{last_plan}。请继续做剩余部分。"
            try:
                await swarm_service.plan_task(user_id=user_id, conversation_id=conversation_id, user_input=text)
            except Exception as e:
                print(f"[supervisor] resume failed: {e}")
        conn.close()
    except Exception as e:
        print(f"[supervisor] resume_restart_pending_runs failed: {e}")



async def check_and_continue(run_id, last_summary, plan_text=None, exec_text=None, review=None):
    import openai
    from .. import config
    run = get_run(run_id)
    if not run or run['status'] != 'running':
        return False, None

    # 死循环检测：连续 3 轮 plan 高度相似 → 强制停止
    try:
        import difflib as _dl
        _hist = json.loads(run['history'] or '[]')
        if len(_hist) >= 3:
            _p1 = (_hist[-1].get('plan') or '')[:200]
            _p2 = (_hist[-2].get('plan') or '')[:200]
            _p3 = (_hist[-3].get('plan') or '')[:200]
            if _p1 and _p2 and _p3:
                _s12 = _dl.SequenceMatcher(None, _p1, _p2).ratio()
                _s23 = _dl.SequenceMatcher(None, _p2, _p3).ratio()
                if _s12 >= 0.9 and _s23 >= 0.9:
                    print('[supervisor] 检测到死循环（连续3轮相似度 ' + str(round(_s12, 2)) + '/' + str(round(_s23, 2)) + '），强制停止')
                    finish_run(run_id, 'loop_detected')
                    return False, None
    except Exception as _le:
        print('[supervisor] 死循环检测异常: ' + str(_le))

    # v0.18.3: no_progress check with plan similarity
    try:
        import difflib as _dl2
        _hist_check = json.loads(run['history'] or '[]')
        if len(_hist_check) >= 5:
            _recent5 = _hist_check[-5:]
            _any_patch = False
            for _h in _recent5:
                _etxt = str(_h.get('exec', ''))
                if '[success] file_patch' in _etxt or '[success] run_python' in _etxt or '[success] verify_patch' in _etxt:
                    _any_patch = True
                    break
            if not _any_patch:
                _plans = [(h.get('plan') or '')[:200] for h in _recent5]
                _similar = False
                for _i in range(len(_plans) - 1):
                    if _plans[_i] and _plans[_i+1]:
                        _sr = _dl2.SequenceMatcher(None, _plans[_i], _plans[_i+1]).ratio()
                        if _sr >= 0.85:
                            _similar = True
                            break
                if _similar:
                    print('[supervisor] no_progress stop')
                    finish_run(run_id, 'no_progress')
                    return False, None
    except Exception as _pe:
        print('[supervisor] check failed: ' + str(_pe))

    record_round(run_id, plan_text or run.get('goal', ''), exec_text or last_summary, review=review)
    run = get_run(run_id)
    if not run or (run['current_round'] or 0) >= (run['max_rounds'] or 5):
        return False, None
    if (run['credits_used'] or 0) >= 16:
        print('[supervisor] 成本达到 16 积分，提前停止')
        finish_run(run_id, 'budget_exceeded')
        return False, None

    if not deduct_round(run_id):
        finish_run(run_id, status='insufficient_credits')
        return False, None
    return True, build_next_input(run_id)

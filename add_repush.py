p = 'core/services/group_task_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

new_code = '''

def repush_pending_tasks(hours=12):
    """重播超过 N 小时未完成的任务卡片"""
    from datetime import datetime, timedelta
    import json as _json
    now = datetime.utcnow()
    threshold = (now - timedelta(hours=hours)).isoformat()
    repushed = []
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM group_tasks WHERE status='open' AND (last_repushed_at IS NULL AND created_at < ? OR last_repushed_at IS NOT NULL AND last_repushed_at < ?)",
            (threshold, threshold)
        )
        rows = cur.fetchall()
    for t in rows:
        try:
            payload = _json.dumps({
                'task_id': t['id'],
                'title': t['title'],
                'reward': t['reward_credits'],
                'status': t['status']
            }, ensure_ascii=False)
            card_msg = '[TASK_CARD]:' + payload
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO group_messages (group_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
                    (t['group_id'], t['created_by'], card_msg, 'task_card')
                )
                cur.execute(
                    "UPDATE group_tasks SET last_repushed_at=?, repush_count=COALESCE(repush_count,0)+1 WHERE id=?",
                    (now.isoformat(), t['id'])
                )
            repushed.append(t['id'])
        except Exception as e:
            print(f'[repush] task {t["id"]} failed: {e}')
    return repushed
'''

if 'def repush_pending_tasks' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')
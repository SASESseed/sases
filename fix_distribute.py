import re

p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 找函数起点到函数终点
start = c.find('def distribute_group_red_packet(group_id, user_id):')
if start < 0:
    print('start not found')
else:
    # 找下一个顶层 def
    next_def = c.find('\ndef ', start + 10)
    if next_def < 0:
        next_def = len(c)

    new_func = '''def distribute_group_red_packet(group_id, user_id, total_amount=None, total_count=None):
    """群主发放群福利手气红包（从群池扣分）"""
    from . import group_red_packet_service
    with db_cursor() as cur:
        cur.execute('SELECT owner_id, credits FROM groups WHERE id=?', (group_id,))
        row = cur.fetchone()
        if not row or row['owner_id'] != user_id:
            return False, '只有群主可以发群福利'
        pool = row['credits'] or 0
        if pool < 100:
            return False, '群池可用余额不足 100'
    if total_amount is None:
        total_amount = round(pool * 0.1, 2)
        if total_amount < 1:
            total_amount = 1.0
    if total_count is None:
        total_count = 5
    if total_amount > pool:
        total_amount = pool
    ok, res = group_red_packet_service.create_packet(
        group_id, user_id, total_amount, int(total_count),
        message='群福利红包', source_type='group_pool', packet_type='lucky'
    )
    if not ok:
        return False, res
    # 记录发放日期，防止重复
    from datetime import datetime
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE groups SET last_red_packet_date=? WHERE id=?', (today, group_id))
    return True, res

'''

    c = c[:start] + new_func + c[next_def + 1:]
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('done')
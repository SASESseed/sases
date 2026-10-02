p = 'core/services/airdrop_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. 改门槛
c = c.replace('MIN_TOTAL_CREDITS = 100.0', 'MIN_TOTAL_CREDITS = 10.0')

# 2. 去掉质押人数检查
old1 = """        with db_cursor() as cur:
            cur.execute("SELECT COUNT(*) as c FROM group_stakes WHERE group_id=? AND status='active'", (g['id'],))
            if (cur.fetchone()['c'] or 0) < 1:
                continue"""
if old1 in c:
    c = c.replace(old1, "        # 质押人数检查已移除")
    print('1. removed stake check')
else:
    print('1. stake check NOT FOUND')

# 3. 去掉活跃度检查
old2 = """        activity = _calc_activity(g['id'], date_str)
        if activity < MIN_ACTIVITY:
            continue
        eligible.append({'group_id': g['id'], 'activity': activity})"""
new2 = """        activity = _calc_activity(g['id'], date_str)
        eligible.append({'group_id': g['id'], 'activity': activity})"""
if old2 in c:
    c = c.replace(old2, new2)
    print('2. removed activity check')
else:
    print('2. activity check NOT FOUND')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
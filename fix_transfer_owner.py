p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

old = '''    # 解析目标用户
    target_uid = None
    try:
        target_uid = int(target_username_or_id)
    except (ValueError, TypeError):
        pass
    with db_cursor() as cur:
        if target_uid is None:
            cur.execute('SELECT id FROM users WHERE username=? OR sases_id=?', (target_username_or_id, target_username_or_id))
            u = cur.fetchone()
            if not u:
                return False, '用户不存在'
            target_uid = u['id']'''

new = '''    # 解析目标用户：先按 username/sases_id 查，再尝试 ID
    target_uid = None
    with db_cursor() as cur:
        cur.execute('SELECT id FROM users WHERE username=? OR sases_id=?', (target_username_or_id, target_username_or_id))
        u = cur.fetchone()
        if u:
            target_uid = u['id']
        else:
            try:
                _try_id = int(target_username_or_id)
                cur.execute('SELECT id FROM users WHERE id=?', (_try_id,))
                u2 = cur.fetchone()
                if u2:
                    target_uid = u2['id']
            except (ValueError, TypeError):
                pass
        if target_uid is None:
            return False, '用户不存在'
    with db_cursor() as cur:'''

if old not in c:
    print('old block not found')
else:
    c = c.replace(old, new)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('done')
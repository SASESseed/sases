p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

new_code = '''

def transfer_owner(group_id, current_owner_id, target_username_or_id):
    """群主转让：原群主 → admin，新群主 → owner"""
    if not _is_owner(group_id, current_owner_id):
        return False, '只有群主可以转让管理权'
    # 解析目标用户
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
            target_uid = u['id']
        if target_uid == current_owner_id:
            return False, '不能转让给自己'
        cur.execute('SELECT role FROM group_members WHERE group_id=? AND user_id=?', (group_id, target_uid))
        m = cur.fetchone()
        if not m:
            return False, '该用户不在群里'
    with db_cursor(commit=True) as cur:
        # 更新 groups.owner_id
        cur.execute('UPDATE groups SET owner_id=? WHERE id=?', (target_uid, group_id))
        # 新群主：role=owner
        cur.execute("UPDATE group_members SET role='owner' WHERE group_id=? AND user_id=?", (group_id, target_uid))
        # 原群主：role=admin
        cur.execute("UPDATE group_members SET role='admin' WHERE group_id=? AND user_id=?", (group_id, current_owner_id))
    return True, {'new_owner_id': target_uid}
'''

if 'def transfer_owner' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')
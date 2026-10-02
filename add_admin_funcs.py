p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 追加到文件末尾
new_code = '''

# ========== 群管理员管理 ==========

def _is_owner(group_id, user_id):
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        return g and g['owner_id'] == user_id


def _is_owner_or_admin(group_id, user_id):
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        if not g:
            return False
        if g['owner_id'] == user_id:
            return True
        cur.execute("SELECT role FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        m = cur.fetchone()
        return bool(m and m['role'] == 'admin')


def set_member_role(group_id, operator_id, target_username_or_id, new_role):
    """群主/管理员设置成员角色（admin/member），只有群主可以设 admin"""
    if not _is_owner_or_admin(group_id, operator_id):
        return False, '只有群主或管理员可以操作'
    if new_role not in ('admin', 'member'):
        return False, '角色只能是 admin 或 member'
    # 只有群主可以任命管理员
    if new_role == 'admin' and not _is_owner(group_id, operator_id):
        return False, '只有群主可以任命管理员'
    with db_cursor() as cur:
        # 解析目标用户
        target_uid = None
        try:
            target_uid = int(target_username_or_id)
        except (ValueError, TypeError):
            pass
        if target_uid is None:
            cur.execute('SELECT id FROM users WHERE username=? OR sases_id=?', (target_username_or_id, target_username_or_id))
            u = cur.fetchone()
            if not u:
                return False, '用户不存在'
            target_uid = u['id']
        # 确认目标在群里
        cur.execute('SELECT role FROM group_members WHERE group_id=? AND user_id=?', (group_id, target_uid))
        m = cur.fetchone()
        if not m:
            return False, '该用户不在群里'
        if m['role'] == 'owner':
            return False, '不能修改群主角色'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE group_members SET role=? WHERE group_id=? AND user_id=?', (new_role, group_id, target_uid))
    return True, {'user_id': target_uid, 'role': new_role}


def list_admins(group_id):
    """列出群主和管理员"""
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        if not g:
            return []
        owner_id = g['owner_id']
        cur.execute('SELECT id, username FROM users WHERE id=?', (owner_id,))
        owner = cur.fetchone()
        result = []
        if owner:
            result.append({'user_id': owner['id'], 'username': owner['username'], 'role': 'owner'})
        cur.execute("SELECT m.user_id, u.username FROM group_members m LEFT JOIN users u ON m.user_id=u.id WHERE m.group_id=? AND m.role='admin'", (group_id,))
        for r in cur.fetchall():
            result.append({'user_id': r['user_id'], 'username': r['username'], 'role': 'admin'})
        return result
'''

if 'def set_member_role' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')
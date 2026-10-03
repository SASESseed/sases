p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

new_code = '''

# ========== 群名称/昵称/免打扰 ==========

def update_group_name(group_id, user_id, new_name):
    """改群名（群主/管理员）"""
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以改群名'
    if not new_name or not new_name.strip():
        return False, '群名不能为空'
    if len(new_name) > 50:
        return False, '群名不能超过 50 字'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE groups SET name=? WHERE id=?', (new_name.strip(), group_id))
    return True, {'name': new_name.strip()}


def set_my_nickname(group_id, user_id, nickname):
    """设置自己在群里的昵称"""
    if len(nickname or '') > 20:
        return False, '昵称不能超过 20 字'
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE group_members SET nickname=? WHERE group_id=? AND user_id=?', (nickname or '', group_id, user_id))
    return True, {'nickname': nickname or ''}


def toggle_mute(group_id, user_id, muted):
    """消息免打扰"""
    with db_cursor(commit=True) as cur:
        cur.execute('UPDATE group_members SET is_muted=? WHERE group_id=? AND user_id=?', (1 if muted else 0, group_id, user_id))
    return True, {'is_muted': bool(muted)}
'''

if 'def update_group_name' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')
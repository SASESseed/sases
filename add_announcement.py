p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

new_code = '''

# ========== 群公告 ==========

def get_announcement(group_id):
    """读取群公告"""
    with db_cursor() as cur:
        cur.execute("SELECT announcement FROM groups WHERE id=?", (group_id,))
        r = cur.fetchone()
        return r['announcement'] if r and r['announcement'] else ''


def set_announcement(group_id, user_id, content):
    """设置群公告（群主/管理员）"""
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以编辑群公告'
    if content and len(content) > 2000:
        return False, '群公告不能超过 2000 字'
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE groups SET announcement=? WHERE id=?", (content or '', group_id))
    return True, {'announcement': content or ''}
'''

if 'def get_announcement' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')
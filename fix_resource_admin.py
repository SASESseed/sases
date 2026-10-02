p = 'core/services/group_resource_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. 替换 _check_owner 的定义
old_def = '''def _check_owner(group_id, user_id):
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        if not g:
            return False
        return g['owner_id'] == user_id'''

new_def = '''def _check_owner(group_id, user_id):
    """检查是否是群主或管理员"""
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        if not g:
            return False
        if g['owner_id'] == user_id:
            return True
        cur.execute("SELECT role FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        m = cur.fetchone()
        if m and m['role'] == 'admin':
            return True
    return False'''

if old_def not in c:
    print('old_def not found')
else:
    c = c.replace(old_def, new_def)
    # 2. 替换错误提示
    c = c.replace("只有群主可以开关蜂群模式", "只有群主或管理员可以开关蜂群模式")
    c = c.replace("只有群主可以配置", "只有群主或管理员可以配置")
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('done')
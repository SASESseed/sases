p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

old = """    if user_id is not None:
        with db_cursor() as cur:
            cur.execute("SELECT owner_id FROM groups WHERE id=?", (group_id,))
            group = cur.fetchone()
            if not group or group["owner_id"] != user_id:
                return False, "只有群主可以切换模式\""""

new = """    if user_id is not None:
        with db_cursor() as cur:
            cur.execute("SELECT owner_id FROM groups WHERE id=?", (group_id,))
            group = cur.fetchone()
            if not group:
                return False, "群不存在"
            if group["owner_id"] == user_id:
                pass
            else:
                cur.execute("SELECT role FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
                m = cur.fetchone()
                if not m or m["role"] != "admin":
                    return False, "只有群主或管理员可以切换模式\""""

if old not in c:
    print('old block not found')
else:
    c = c.replace(old, new)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('done')
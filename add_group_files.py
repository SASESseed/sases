p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

new_code = '''

def list_group_files(group_id, user_id, limit=100):
    """列出群里所有共享文件"""
    if not _is_member(group_id, user_id):
        return None
    with db_cursor() as cur:
        cur.execute("""
            SELECT m.id, m.content, m.created_at, m.sender_id, m.sender_agent_id,
                   u.username as sender_name
            FROM group_messages m
            LEFT JOIN users u ON m.sender_id = u.id
            WHERE m.group_id = ? AND m.content LIKE '[FILE]:%'
            ORDER BY m.id DESC LIMIT ?
        """, (group_id, limit))
        rows = cur.fetchall()
    files = []
    for r in rows:
        content = r['content'] or ''
        body = content[len('[FILE]:'):]
        parts = body.split('|')
        if len(parts) < 3:
            continue
        files.append({
            'msg_id': r['id'],
            'url': parts[0],
            'name': parts[1],
            'size': parts[2],
            'sender_name': r['sender_name'] or '群友',
            'created_at': r['created_at']
        })
    return files
'''

if 'def list_group_files' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')
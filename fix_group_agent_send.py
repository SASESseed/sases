p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. 替换智能体检查逻辑，允许群共享
old = """        if sender_agent_id:
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, sender_agent_id))
            if not cur.fetchone():
                return False, "智能体不在群中"
            cur.execute("INSERT INTO group_messages (group_id, sender_agent_id, content, global_msg_id, origin_node) VALUES (?, ?, ?, ?, ?)", (group_id, sender_agent_id, content, _global_msg_id, _cfg.HIVE_NODE_ID if _global_msg_id else None))"""

new = """        if sender_agent_id:
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, sender_agent_id))
            _in_members = cur.fetchone()
            if not _in_members:
                # 回退：检查是否在群资源池（蜂群模式共享）
                cur.execute("SELECT id FROM group_resource_pool WHERE group_id=? AND agent_id=? AND enabled=1", (group_id, sender_agent_id))
                if not cur.fetchone():
                    return False, "智能体不在群中"
            cur.execute("INSERT INTO group_messages (group_id, sender_agent_id, content, global_msg_id, origin_node) VALUES (?, ?, ?, ?, ?)", (group_id, sender_agent_id, content, _global_msg_id, _cfg.HIVE_NODE_ID if _global_msg_id else None))"""

if old not in c:
    print('old block not found')
else:
    c = c.replace(old, new)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('done')
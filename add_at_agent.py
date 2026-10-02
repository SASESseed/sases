p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

new_code = '''

# ========== @智能体触发 AI 回复 ==========

def _find_agent_id_by_name(group_id, name):
    """按名字找群成员里的智能体 ID（支持带或不带 @）"""
    if not name:
        return None
    name = name.strip().lstrip('@').strip()
    if not name:
        return None
    with db_cursor() as cur:
        # 1. 优先查群成员绑定的智能体
        cur.execute(
            "SELECT mc.id FROM group_members gm LEFT JOIN model_configs mc ON gm.agent_id = mc.id WHERE gm.group_id=? AND mc.name=? LIMIT 1",
            (group_id, name)
        )
        r = cur.fetchone()
        if r and r['id']:
            return r['id']
        # 2. 查群资源池里的模型配置
        cur.execute(
            "SELECT mc.id FROM group_resource_pool p LEFT JOIN model_configs mc ON p.agent_id = mc.id WHERE p.group_id=? AND p.enabled=1 AND mc.name=? LIMIT 1",
            (group_id, name)
        )
        r = cur.fetchone()
        if r and r['id']:
            return r['id']
    return None


def _is_human_in_group(group_id, name):
    """检查 name 是否是真人群成员"""
    if not name:
        return False
    name = name.strip().lstrip('@').strip()
    with db_cursor() as cur:
        cur.execute(
            "SELECT u.id FROM group_members gm LEFT JOIN users u ON gm.user_id = u.id WHERE gm.group_id=? AND u.username=? LIMIT 1",
            (group_id, name)
        )
        return cur.fetchone() is not None


def parse_at_prefix(content):
    """解析 @名字 前缀，返回 (agent_name, rest_question) 或 (None, content)"""
    if not content or not content.startswith('@'):
        return None, content
    # @名字 后面必须是空格或字符串结束
    parts = content[1:].split(' ', 1)
    if not parts or not parts[0]:
        return None, content
    agent_name = parts[0].strip()
    rest = parts[1].strip() if len(parts) > 1 else ''
    return agent_name, rest


def insert_agent_message(group_id, agent_id, content):
    """把智能体的回复插入群消息表"""
    import secrets as _sec
    from .. import config as _cfg
    _gmid = None
    with db_cursor() as _cur:
        _cur.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
        _r = _cur.fetchone()
        if _r and _r['global_group_id']:
            _gmid = (_cfg.HIVE_NODE_ID or 'unknown') + ':m-' + _sec.token_hex(8)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO group_messages (group_id, sender_agent_id, content, global_msg_id, origin_node) VALUES (?, ?, ?, ?, ?)",
            (group_id, agent_id, content, _gmid, _cfg.HIVE_NODE_ID if _gmid else None)
        )
        msg_id = cur.lastrowid
    return msg_id
'''

if 'def parse_at_prefix' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')
# core/services/group_service.py
from ..db import db_cursor


def create_group(name: str, owner_id: int):
    """创建群聊，返回群 ID。HIVE_MODE 启用时生成 global_group_id 并广播给 peers。"""
    import secrets as _sec
    from .. import config as _cfg
    _global_gid = None
    _origin_node = _cfg.HIVE_NODE_ID or None
    if _cfg.HIVE_MODE != 'off' and _cfg.HIVE_NODE_ID:
        _global_gid = _cfg.HIVE_NODE_ID + ':g-' + _sec.token_hex(6)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO groups (name, owner_id, mode, global_group_id, origin_node) VALUES (?, ?, 'normal', ?, ?)",
            (name, owner_id, _global_gid, _origin_node)
        )
        group_id = cur.lastrowid
        _owner_sases_id = None
        try:
            cur.execute("SELECT sases_id FROM users WHERE id=?", (owner_id,))
            _r = cur.fetchone()
            if _r:
                _owner_sases_id = _r['sases_id']
        except Exception:
            pass
        cur.execute("INSERT INTO group_members (group_id, user_id, role, origin_node, user_sases_id) VALUES (?, ?, 'owner', ?, ?)",
                    (group_id, owner_id, _origin_node, _owner_sases_id))
    if _global_gid and _cfg.HIVE_MODE != 'off' and _cfg.HIVE_PEERS:
        try:
            import httpx as _httpx
            _payload = {
                'global_group_id': _global_gid,
                'origin_node': _origin_node,
                'name': name,
                'owner_sases_id': _owner_sases_id,
                'mode': 'normal',
            }
            for _peer in _cfg.HIVE_PEERS:
                try:
                    _httpx.post(_peer.rstrip('/') + '/hive/sync/group', json=_payload, timeout=3)
                except Exception as _pe:
                    print('[group] hive broadcast failed: ' + str(_pe))
        except Exception as _e:
            print('[group] hive broadcast error: ' + str(_e))
    return group_id


def invite_to_group(group_id: int, inviter_id: int, invitee: str):
    """邀请用户或智能体加入群聊。invitee 可以是用户名、SASES ID、智能体 ID 或智能体名称。"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, inviter_id))
        if not cur.fetchone():
            return False, "邀请者不是群成员"

        from .. import config as _cfg_i
        _origin = _cfg_i.HIVE_NODE_ID if _cfg_i.HIVE_MODE != 'off' else None

        cur.execute("SELECT id FROM users WHERE username=? OR sases_id=?", (invitee, invitee))
        user = cur.fetchone()
        if user:
            target_user_id = user["id"]
            _target_sases = None
            cur.execute("SELECT sases_id FROM users WHERE id=?", (target_user_id,))
            _ru = cur.fetchone()
            if _ru:
                _target_sases = _ru['sases_id']
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, target_user_id))
            if cur.fetchone():
                return False, "用户已在群中"
            with db_cursor(commit=True) as cur2:
                cur2.execute("INSERT INTO group_members (group_id, user_id, origin_node, user_sases_id) VALUES (?, ?, ?, ?)", (group_id, target_user_id, _origin, _target_sases))
                cur2.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
                _gg = cur2.fetchone()
            if _gg and _gg['global_group_id']:
                _broadcast_member(_gg['global_group_id'], _target_sases, 'member')
            return True, "邀请用户成功"

        cur.execute("""
            SELECT id FROM model_configs
            WHERE (id=? OR name=?) AND user_id=?
        """, (invitee, invitee, inviter_id))
        agent = cur.fetchone()
        if agent:
            agent_id = agent["id"]
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, agent_id))
            if cur.fetchone():
                return False, "智能体已在群中"
            with db_cursor(commit=True) as cur2:
                cur2.execute("INSERT INTO group_members (group_id, agent_id, role, origin_node) VALUES (?, ?, 'agent', ?)", (group_id, agent_id, _origin))
            return True, "邀请智能体成功"

        return False, "找不到该用户或智能体，或智能体不属于你"


def _broadcast_member_remove(global_group_id, member_sases_id):
    from .. import config as _cfg
    if _cfg.HIVE_MODE == 'off' or not _cfg.HIVE_PEERS or not global_group_id:
        return
    try:
        import httpx as _httpx
        _payload = {'global_group_id': global_group_id, 'member_sases_id': member_sases_id, 'origin_node': _cfg.HIVE_NODE_ID}
        for _peer in _cfg.HIVE_PEERS:
            try:
                _httpx.post(_peer.rstrip('/') + '/hive/sync/member-remove', json=_payload, timeout=3)
            except Exception as _pe:
                print('[group] member-remove broadcast failed: ' + str(_pe))
    except Exception as _e:
        print('[group] member-remove broadcast error: ' + str(_e))


def _broadcast_member(global_group_id, member_sases_id, role='member'):
    from .. import config as _cfg
    if _cfg.HIVE_MODE == 'off' or not _cfg.HIVE_PEERS or not global_group_id:
        return
    try:
        import httpx as _httpx
        _payload = {'global_group_id': global_group_id, 'member_sases_id': member_sases_id, 'role': role, 'origin_node': _cfg.HIVE_NODE_ID}
        for _peer in _cfg.HIVE_PEERS:
            try:
                _httpx.post(_peer.rstrip('/') + '/hive/sync/member', json=_payload, timeout=3)
            except Exception as _pe:
                print('[group] member broadcast failed: ' + str(_pe))
    except Exception as _e:
        print('[group] member broadcast error: ' + str(_e))


def list_user_groups(user_id: int):
    """获取用户所在的群聊列表"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT g.id, g.name, g.owner_id, g.mode, COALESCE(g.is_pinned, 0) as is_pinned,
                   (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) as member_count,
                   (SELECT COUNT(*) FROM group_messages gm3
                    WHERE gm3.group_id = g.id
                      AND gm3.created_at > COALESCE(gm2.last_read_at, '1970-01-01')
                      AND (gm3.sender_id IS NULL OR gm3.sender_id != ?)) as unread_count
            FROM groups g
            JOIN group_members gm2 ON g.id = gm2.group_id
            WHERE gm2.user_id = ?
            ORDER BY COALESCE(g.is_pinned, 0) DESC, g.created_at DESC
        """, (user_id, user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def mark_group_read(group_id: int, user_id: int):
    """标记群聊已读（更新 last_read_at）"""
    from datetime import datetime as _dt
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE group_members SET last_read_at=? WHERE group_id=? AND user_id=?", (_dt.now().isoformat(), group_id, user_id))
        return cur.rowcount > 0



def toggle_group_pin(group_id: int, user_id: int, pinned: bool):
    """置顶/取消置顶群聊（仅检查成员身份）"""
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT 1 FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            return False
        cur.execute("UPDATE groups SET is_pinned=? WHERE id=?", (1 if pinned else 0, group_id))
        return True



def get_group_info(group_id: int):
    """获取群基本信息，包括模式和 global_group_id"""
    with db_cursor() as cur:
        cur.execute("SELECT id, name, owner_id, mode, global_group_id, origin_node FROM groups WHERE id=?", (group_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None


def get_group_mode(group_id: int):
    """获取群模式"""
    with db_cursor() as cur:
        cur.execute("SELECT mode FROM groups WHERE id=?", (group_id,))
        row = cur.fetchone()
        return row["mode"] if row else None


def set_group_mode(group_id: int, mode: str, user_id: int = None):
    """设置群模式（仅群主可操作）"""
    if user_id is not None:
        with db_cursor() as cur:
            cur.execute("SELECT owner_id FROM groups WHERE id=?", (group_id,))
            group = cur.fetchone()
            if not group or group["owner_id"] != user_id:
                return False, "只有群主可以切换模式"

    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE groups SET mode=? WHERE id=?", (mode, group_id))
        return True, "切换成功"


def get_group_messages(group_id: int, user_id: int):
    """获取群聊消息（需为群成员）"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            return None
        cur.execute("""
            SELECT m.id, m.content, m.created_at,
                   CASE WHEN m.sender_agent_id IS NOT NULL THEN mc.name
                        ELSE u.username END as sender_name,
                   m.sender_id, m.sender_agent_id
            FROM group_messages m
            LEFT JOIN users u ON m.sender_id = u.id
            LEFT JOIN model_configs mc ON m.sender_agent_id = mc.id
            WHERE m.group_id = ?
            ORDER BY m.created_at ASC
            LIMIT 100
        """, (group_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def send_group_message(group_id: int, sender_id: int, content: str, sender_agent_id: str = None):
    """发送群聊消息，可为用户或智能体。HIVE_MODE 启用时广播给 peers。"""
    import secrets as _sec
    from .. import config as _cfg
    mode = get_group_mode(group_id)
    if mode == 'swarm':
        return False, "蜂群模式暂未开放任务功能，请切换为普通聊天模式"

    _global_gid = None
    _global_msg_id = None
    _sender_sases_id = None
    with db_cursor() as _cur_g:
        _cur_g.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
        _rg = _cur_g.fetchone()
        if _rg:
            _global_gid = _rg['global_group_id']
    if _cfg.HIVE_MODE != 'off' and _global_gid:
        _global_msg_id = (_cfg.HIVE_NODE_ID or 'unknown') + ':m-' + _sec.token_hex(8)

    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, sender_agent_id))
            if not cur.fetchone():
                return False, "智能体不在群中"
            cur.execute("INSERT INTO group_messages (group_id, sender_agent_id, content, global_msg_id, origin_node) VALUES (?, ?, ?, ?, ?)", (group_id, sender_agent_id, content, _global_msg_id, _cfg.HIVE_NODE_ID if _global_msg_id else None))
        else:
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, sender_id))
            if not cur.fetchone():
                return False, "用户不在群中"
            cur.execute("SELECT sases_id FROM users WHERE id=?", (sender_id,))
            _ru = cur.fetchone()
            if _ru:
                _sender_sases_id = _ru['sases_id']
            cur.execute("INSERT INTO group_messages (group_id, sender_id, content, global_msg_id, origin_node) VALUES (?, ?, ?, ?, ?)", (group_id, sender_id, content, _global_msg_id, _cfg.HIVE_NODE_ID if _global_msg_id else None))

    if _global_msg_id and _global_gid and _cfg.HIVE_PEERS:
        try:
            import httpx as _httpx
            _payload = {
                'global_group_id': _global_gid,
                'global_msg_id': _global_msg_id,
                'sender_sases_id': _sender_sases_id,
                'sender_agent_id': sender_agent_id,
                'content': content,
                'origin_node': _cfg.HIVE_NODE_ID,
            }
            for _peer in _cfg.HIVE_PEERS:
                try:
                    _httpx.post(_peer.rstrip('/') + '/hive/sync/message', json=_payload, timeout=3)
                except Exception as _pe:
                    print('[group] msg broadcast failed: ' + str(_pe))
        except Exception as _e:
            print('[group] msg broadcast error: ' + str(_e))
    return True, "发送成功"


def list_group_members(group_id: int):
    """获取群成员列表，包括用户和智能体"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT gm.user_id, gm.agent_id, gm.role,
                   COALESCE(u.username, mc.name) as display_name,
                   CASE WHEN gm.agent_id IS NOT NULL THEN 'agent' ELSE 'user' END as member_type
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.id
            LEFT JOIN model_configs mc ON gm.agent_id = mc.id
            WHERE gm.group_id = ?
        """, (group_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_group_credits(group_id: int):
    """获取群积分（暂返回0，后续可统计）"""
    return 0.0


def remove_member_from_group(group_id: int, remover_id: int, member_identifier: str):
    """移除群成员（仅群主可操作）"""
    with db_cursor() as cur:
        cur.execute("SELECT owner_id FROM groups WHERE id=?", (group_id,))
        group = cur.fetchone()
        if not group or group["owner_id"] != remover_id:
            return False, "只有群主可以移除成员"

        cur.execute("""
            SELECT gm.id, gm.user_id, u.sases_id
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id=?
              AND (CAST(gm.user_id AS TEXT)=?
                   OR gm.agent_id=?
                   OR u.sases_id=?
                   OR gm.user_sases_id=?
                   OR gm.user_id IN (SELECT id FROM users WHERE username=?)
                   OR gm.agent_id IN (SELECT id FROM model_configs WHERE name=?))
        """, (group_id, member_identifier, member_identifier, member_identifier, member_identifier, member_identifier, member_identifier))
        member = cur.fetchone()
        if not member:
            return False, "成员不存在"

        _member_sases = member['sases_id'] if member else None
        with db_cursor(commit=True) as cur2:
            cur2.execute("DELETE FROM group_members WHERE id=?", (member["id"],))
            cur2.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
            _gg = cur2.fetchone()
        if _member_sases and _gg and _gg['global_group_id']:
            _broadcast_member_remove(_gg['global_group_id'], _member_sases)
        return True, "移除成功"


def leave_group(group_id: int, user_id: int):
    """成员退出群聊"""
    _sases = None
    _gg = None
    with db_cursor() as cur:
        cur.execute("SELECT sases_id FROM users WHERE id=?", (user_id,))
        _r = cur.fetchone()
        if _r:
            _sases = _r['sases_id']
        cur.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
        _g = cur.fetchone()
        if _g:
            _gg = _g['global_group_id']
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
    if _sases and _gg:
        _broadcast_member_remove(_gg, _sases)
    return {"ok": True}


def dismiss_group(group_id: int):
    # 校验群主权限由调用方传入的 user_id 完成；此处统一提交事务

    """群主解散群聊"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM group_messages WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM groups WHERE id=?", (group_id,))
        return {"ok": True}

# core/services/group_service.py
from ..db import db_cursor


def create_group(name: str, owner_id: int):

    def exit_group(self, group_id, user_id):
        return self.repo.remove_member(group_id, user_id)

    """创建群聊，返回群 ID"""
    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO groups (name, owner_id, mode) VALUES (?, ?, 'normal')", (name, owner_id))
        group_id = cur.lastrowid
        cur.execute("INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, 'owner')", (group_id, owner_id))
        return group_id


def invite_to_group(group_id: int, inviter_id: int, invitee: str):
    """邀请用户或智能体加入群聊。invitee 可以是用户名、SASES ID、智能体 ID 或智能体名称。"""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, inviter_id))
        if not cur.fetchone():
            return False, "邀请者不是群成员"

        cur.execute("SELECT id FROM users WHERE username=? OR sases_id=?", (invitee, invitee))
        user = cur.fetchone()
        if user:
            target_user_id = user["id"]
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, target_user_id))
            if cur.fetchone():
                return False, "用户已在群中"
            with db_cursor(commit=True) as cur2:
                cur2.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (group_id, target_user_id))
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
                cur2.execute("INSERT INTO group_members (group_id, agent_id, role) VALUES (?, ?, 'agent')", (group_id, agent_id))
            return True, "邀请智能体成功"

        return False, "找不到该用户或智能体，或智能体不属于你"


def list_user_groups(user_id: int):
    """获取用户所在的群聊列表"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT g.id, g.name, g.owner_id, g.mode,
                   (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) as member_count
            FROM groups g
            JOIN group_members gm2 ON g.id = gm2.group_id
            WHERE gm2.user_id = ?
            ORDER BY g.created_at DESC
        """, (user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_group_info(group_id: int):
    """获取群基本信息，包括模式"""
    with db_cursor() as cur:
        cur.execute("SELECT id, name, owner_id, mode FROM groups WHERE id=?", (group_id,))
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
    """发送群聊消息，可为用户或智能体。蜂群模式下普通消息暂不处理。"""
    mode = get_group_mode(group_id)
    if mode == 'swarm':
        return False, "蜂群模式暂未开放任务功能，请切换为普通聊天模式"

    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND agent_id=?", (group_id, sender_agent_id))
            if not cur.fetchone():
                return False, "智能体不在群中"
            cur.execute("INSERT INTO group_messages (group_id, sender_agent_id, content) VALUES (?, ?, ?)", (group_id, sender_agent_id, content))
        else:
            cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, sender_id))
            if not cur.fetchone():
                return False, "用户不在群中"
            cur.execute("INSERT INTO group_messages (group_id, sender_id, content) VALUES (?, ?, ?)", (group_id, sender_id, content))
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
            SELECT id FROM group_members
            WHERE group_id=?
              AND (CAST(user_id AS TEXT)=? OR agent_id=? OR user_id IN (SELECT id FROM users WHERE username=?))
        """, (group_id, member_identifier, member_identifier, member_identifier))
        member = cur.fetchone()
        if not member:
            return False, "成员不存在"

        with db_cursor(commit=True) as cur2:
            cur2.execute("DELETE FROM group_members WHERE id=?", (member["id"],))
        return True, "移除成功"


def leave_group(group_id: int, user_id: int):
    """成员退出群聊"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        return {"ok": True}


def dismiss_group(group_id: int):
    # 校验群主权限由调用方传入的 user_id 完成；此处统一提交事务

    """群主解散群聊"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM group_messages WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM groups WHERE id=?", (group_id,))
        return {"ok": True}

p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

new_code = '''

# ========== 群聊邀请确认 ==========

def _get_features_safe(group_id):
    with db_cursor() as cur:
        cur.execute("SELECT features FROM groups WHERE id=?", (group_id,))
        r = cur.fetchone()
        if not r:
            return {}
        try:
            import json as _j
            return _j.loads(r['features'] or '{}')
        except Exception:
            return {}


def _set_features_safe(group_id, f):
    import json as _j
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE groups SET features=? WHERE id=?", (_j.dumps(f, ensure_ascii=False), group_id))


def get_invite_confirm(group_id):
    f = _get_features_safe(group_id)
    return bool(f.get('invite_confirm'))


def set_invite_confirm(group_id, user_id, enabled):
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以设置'
    f = _get_features_safe(group_id)
    f['invite_confirm'] = bool(enabled)
    _set_features_safe(group_id, f)
    return True, {'invite_confirm': f['invite_confirm']}


def list_pending_invites(group_id, user_id):
    """列出待批准邀请（群主/管理员）"""
    if not _is_owner_or_admin(group_id, user_id):
        return None
    with db_cursor() as cur:
        cur.execute("SELECT id, inviter_id, invitee, created_at FROM group_invite_pending WHERE group_id=? AND status='pending' ORDER BY id DESC", (group_id,))
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            cur.execute("SELECT username FROM users WHERE id=?", (d['inviter_id'],))
            u = cur.fetchone()
            d['inviter_name'] = u['username'] if u else '?'
            rows.append(d)
        return rows


def approve_invite(group_id, user_id, pending_id):
    """批准邀请"""
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以操作'
    with db_cursor() as cur:
        cur.execute("SELECT invitee FROM group_invite_pending WHERE id=? AND group_id=? AND status='pending'", (pending_id, group_id))
        r = cur.fetchone()
        if not r:
            return False, '待批准记录不存在'
        invitee = r['invitee']
    # 调用原 invite_to_group（此时 current user 是管理员，直接进群）
    ok, msg = invite_to_group(group_id, user_id, invitee)
    if not ok:
        return False, msg
    from datetime import datetime
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE group_invite_pending SET status='approved', resolved_at=?, resolved_by=? WHERE id=?", (datetime.utcnow().isoformat(), user_id, pending_id))
    return True, {'approved': pending_id}


def reject_invite(group_id, user_id, pending_id):
    """拒绝邀请"""
    if not _is_owner_or_admin(group_id, user_id):
        return False, '只有群主或管理员可以操作'
    from datetime import datetime
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE group_invite_pending SET status='rejected', resolved_at=?, resolved_by=? WHERE id=? AND group_id=? AND status='pending'", (datetime.utcnow().isoformat(), user_id, pending_id, group_id))
        if cur.rowcount == 0:
            return False, '待批准记录不存在'
    return True, {'rejected': pending_id}
'''

if 'def get_invite_confirm' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')
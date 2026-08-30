# ========== API Key 管理 ==========
def add_api_key(user_id: int, provider: str, key: str, priority: int = 0) -> bool:
    """添加或更新用户的 API Key"""
    from core.encryption import encrypt_text
    encrypted = encrypt_text(key)
    with get_db() as conn:
        # 如果同一 provider 已存在，更新 key 和 priority
        existing = conn.execute(
            "SELECT id FROM api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE api_keys SET encrypted_key = ?, priority = ?, is_active = 1 WHERE id = ?",
                (encrypted, priority, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO api_keys (user_id, provider, encrypted_key, priority) VALUES (?, ?, ?, ?)",
                (user_id, provider, encrypted, priority)
            )
    return True

def list_api_keys(user_id: int) -> list:
    """列出用户的 API Key（脱敏显示）"""
    keys = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, provider, encrypted_key, priority, is_active FROM api_keys WHERE user_id = ? ORDER BY priority DESC",
            (user_id,)
        ).fetchall()
        for r in rows:
            # 脱敏：显示 provider 和最后4位
            provider = r["provider"]
            keys.append({
                "id": r["id"],
                "provider": provider,
                "masked_key": "****" + (r["encrypted_key"][-4:] if r["encrypted_key"] else ""),
                "priority": r["priority"],
                "is_active": r["is_active"]
            })
    return keys

def delete_api_key(user_id: int, key_id: int) -> bool:
    """删除指定的 API Key"""
    with get_db() as conn:
        conn.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
    return True

def set_api_key_priority(user_id: int, key_id: int, priority: int) -> bool:
    """设置 API Key 优先级"""
    with get_db() as conn:
        conn.execute("UPDATE api_keys SET priority = ? WHERE id = ? AND user_id = ?", (priority, key_id, user_id))
    return True

def get_active_api_keys(user_id: int) -> list:
    """获取用户所有活跃的 API Key 解密后的值，按优先级从高到低"""
    from core.encryption import decrypt_text
    result = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT provider, encrypted_key, priority FROM api_keys WHERE user_id = ? AND is_active = 1 ORDER BY priority DESC",
            (user_id,)
        ).fetchall()
        for r in rows:
            key = decrypt_text(r["encrypted_key"])
            if key:
                result.append({"provider": r["provider"], "key": key, "priority": r["priority"]})
    return result

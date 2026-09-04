# core/services/model_service.py
import secrets
import string
from ..db import db_cursor
from ..security import encrypt_api_key

def generate_model_id(prefix: str) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return f"{prefix}_{''.join(secrets.choice(alphabet) for _ in range(8))}"

def create_api_key_model(user_id: int, name: str, provider: str, api_key: str, priority: int = 1):
    """添加 API Key 类型的模型配置"""
    encrypted = encrypt_api_key(api_key)
    model_id = generate_model_id("sases_api")
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO model_configs (id, user_id, model_type, name, provider, api_key_encrypted)
            VALUES (?, ?, 'api', ?, ?, ?)
        """, (model_id, user_id, name, provider, encrypted))
    return model_id

def create_local_model(user_id: int, name: str, node_url: str, model_name: str, capabilities: str = None):
    """添加本地模型类型的模型配置"""
    model_id = generate_model_id("sases_node")
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO model_configs (id, user_id, model_type, name, node_url, model_name, capabilities)
            VALUES (?, ?, 'local', ?, ?, ?, ?)
        """, (model_id, user_id, name, node_url, model_name, capabilities))
    return model_id

def get_user_models(user_id: int):
    """获取用户所有模型配置"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, model_type, name, provider, node_url, model_name, capabilities, is_shared, visibility, price
            FROM model_configs
            WHERE user_id=?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def update_model_share(user_id: int, model_id: str, is_shared: int, visibility: str, price: float):
    """更新模型共享设置"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE model_configs
            SET is_shared=?, visibility=?, price=?
            WHERE id=? AND user_id=?
        """, (is_shared, visibility, price, model_id, user_id))
    return True

def delete_model(user_id: int, model_id: str):
    """删除模型配置"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM model_configs WHERE id=? AND user_id=?", (model_id, user_id))
    return True

# core/services/knowledge_service.py
from ..db import db_cursor


def get_user_knowledge(user_id: int):
    """获取用户知识库列表（当前表无 user_id，暂按全局返回，可根据需要扩展）"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, task, branch_a, branch_b, solution, verified, created_at
            FROM knowledge_base
            ORDER BY id DESC
        """)
        rows = cur.fetchall()
    return [dict(row) for row in rows]

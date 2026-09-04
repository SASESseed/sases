# core/services/stats_service.py
import os
import json
from ..db import db_cursor


def get_leaderboard():
    """获取贡献排行榜（按贡献值排序，不直接使用积分）"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT u.id, u.username, u.sases_id,
                   COALESCE(SUM(cl.points), 0) AS contribution_score
            FROM users u
            LEFT JOIN contribution_log cl ON u.id = cl.user_id AND cl.points > 0
            GROUP BY u.id
            ORDER BY contribution_score DESC, u.id ASC
            LIMIT 50
        """)
        rows = cur.fetchall()

    leaderboard = []
    for idx, row in enumerate(rows, start=1):
        leaderboard.append({
            "rank": idx,
            "user_id": row["id"],
            "username": row["username"],
            "sases_id": row["sases_id"] or "",
            "contribution_score": row["contribution_score"] or 0,
            "avatar": row["username"][0].upper() if row["username"] else "?"
        })

    return leaderboard


def get_harness_modules():
    """获取可用的 Harness 模块列表"""
    modules = []
    modules_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'harness_modules')
    if os.path.exists(modules_dir):
        for item in os.listdir(modules_dir):
            manifest_path = os.path.join(modules_dir, item, 'manifest.json')
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    modules.append({
                        "id": manifest.get("id", item),
                        "name": manifest.get("name", item),
                        "description": manifest.get("description", "")
                    })
                except Exception:
                    pass
    return modules

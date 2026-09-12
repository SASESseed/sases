# core/services/memory_service.py
from typing import Optional, List
import json
from datetime import datetime, timedelta
from ..db import db_cursor


def remember(
    user_id: int,
    memory_type: str,
    content: str,
    agent_id: str = None,
    group_id: int = None,
    tags: str = None,
    importance: float = 0.5,
    full_data: dict = None,
    expires_at: str = None
) -> int:
    """写入一条安全记忆"""
    full_data_json = json.dumps(full_data, ensure_ascii=False) if full_data else None
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO safety_memory
            (memory_type, content, full_data, agent_id, user_id, group_id, importance, tags, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (memory_type, content, full_data_json, agent_id, user_id, group_id, importance, tags, expires_at))
        return cur.lastrowid


def recall(
    user_id: int,
    query: str,
    top_k: int = 5,
    memory_type: str = None,
    group_id: int = None
) -> List[dict]:
    """检索用户的安全记忆，支持关键词匹配"""
    with db_cursor() as cur:
        sql = "SELECT * FROM safety_memory WHERE user_id=?"
        params = [user_id]

        if memory_type:
            sql += " AND memory_type=?"
            params.append(memory_type)

        if group_id is not None:
            sql += " AND group_id=?"
            params.append(group_id)

        sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(top_k * 3)

        cur.execute(sql, params)
        rows = cur.fetchall()

    results = []
    query_lower = query.lower()
    for row in rows:
        row = dict(row)
        if query_lower in row["content"].lower() or (row["tags"] and query_lower in row["tags"].lower()):
            results.append(row)
            if len(results) >= top_k:
                break

    return results


def recall_by_type(
    user_id: int,
    memory_type: str,
    top_k: int = 5,
    group_id: int = None
) -> List[dict]:
    """按类型直接获取最新记忆"""
    with db_cursor() as cur:
        sql = "SELECT * FROM safety_memory WHERE user_id=? AND memory_type=?"
        params = [user_id, memory_type]

        if group_id is not None:
            sql += " AND group_id=?"
            params.append(group_id)

        sql += " ORDER BY created_at DESC, importance DESC LIMIT ?"
        params.append(top_k)

        cur.execute(sql, params)
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def forget(user_id: int, memory_id: int) -> bool:
    """删除用户的一条记忆"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM safety_memory WHERE id=? AND user_id=?", (memory_id, user_id))
        return cur.rowcount > 0


def summarize_work_logs(user_id: int, hours: int = 24) -> int:
    """总结最近 N 小时的工作日志，并写入记忆库"""
    since = (datetime.now() - timedelta(hours=hours)).isoformat()

    with db_cursor() as cur:
        cur.execute("""
            SELECT command, output, status, duration_ms, created_at
            FROM work_logs
            WHERE user_id=? AND created_at >= ?
            ORDER BY created_at ASC
        """, (user_id, since))
        rows = cur.fetchall()

    if not rows:
        return 0

    total = len(rows)
    success_count = sum(1 for r in rows if r["status"] == "success")
    failed_count = total - success_count
    avg_duration = sum(r["duration_ms"] or 0 for r in rows) / total

    # 简单统计常见命令
    cmd_counts = {}
    for r in rows:
        base_cmd = r["command"].strip().split()[0] if r["command"].strip() else "unknown"
        cmd_counts[base_cmd] = cmd_counts.get(base_cmd, 0) + 1

    common_cmds = sorted(cmd_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    content = (
        f"过去{hours}小时工作日志总结\n"
        f"总任务数: {total}\n"
        f"成功: {success_count}\n"
        f"失败: {failed_count}\n"
        f"平均耗时: {avg_duration:.0f} ms\n"
        f"常用命令: {', '.join([f'{cmd}({cnt})' for cmd, cnt in common_cmds])}"
    )

    return remember(
        user_id=user_id,
        memory_type="periodic_summary",
        content=content,
        tags="work_summary",
        importance=0.7
    )

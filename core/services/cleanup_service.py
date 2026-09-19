# core/services/cleanup_service.py
"""
SASES 数据清理服务
- safety_memory 过期清理
- swarm_reviews 保留 30 天
- swarm_pending_tasks 完成/取消/无计划 保留 7 天
"""
import asyncio
from datetime import datetime, timedelta
from ..db import db_cursor


def cleanup_expired_memory() -> int:
    """删除 expires_at 已过期的记忆"""
    now = datetime.now().isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM safety_memory WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,)
        )
        return cur.rowcount


def cleanup_old_reviews(days: int = 30) -> int:
    """删除 30 天前的审核日志"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM swarm_reviews WHERE created_at < ?", (cutoff,))
        return cur.rowcount


def cleanup_finished_swarm_tasks(days: int = 7) -> int:
    """删除 7 天前已完成/取消/无计划的蜂群任务"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            DELETE FROM swarm_pending_tasks
            WHERE status IN ('completed', 'cancelled', 'no_plan')
              AND updated_at < ?
            """,
            (cutoff,)
        )
        return cur.rowcount


def cleanup_all() -> dict:
    """执行全部清理任务，返回各项删除数量"""
    result = {
        "expired_memory": 0,
        "old_reviews": 0,
        "finished_swarm_tasks": 0,
    }
    try:
        result["expired_memory"] = cleanup_expired_memory()
    except Exception as e:
        print(f"[cleanup] 过期记忆清理失败: {e}")

    try:
        result["old_reviews"] = cleanup_old_reviews(days=30)
    except Exception as e:
        print(f"[cleanup] 审核日志清理失败: {e}")

    try:
        result["finished_swarm_tasks"] = cleanup_finished_swarm_tasks(days=7)
    except Exception as e:
        print(f"[cleanup] 蜂群任务清理失败: {e}")

    print(f"[cleanup] 清理完成: {result}")
    return result


async def periodic_cleanup(interval_hours: int = 24):
    """后台定时任务：每 24 小时执行一次清理"""
    # 启动时等 5 分钟再执行，避免和启动备份/其他任务抢资源
    await asyncio.sleep(5 * 60)
    while True:
        try:
            await asyncio.to_thread(cleanup_all)
        except Exception as e:
            print(f"[cleanup] 周期任务异常: {e}")
        await asyncio.sleep(interval_hours * 3600)

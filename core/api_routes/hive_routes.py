"""蜂群节点信息路由（阶段 1）"""
from fastapi import APIRouter
from .. import config

router = APIRouter(prefix="/hive", tags=["hive"])


@router.get("/info")
def hive_info():
    return {
        "node_id": config.HIVE_NODE_ID or "unknown",
        "mode": config.HIVE_MODE,
        "peers": config.HIVE_PEERS,
        "version": "1.0"
    }


@router.get("/ping")
def hive_ping():
    return {"ok": True}


@router.post("/sync/group")
def sync_group(body: dict):
    """接收 peer 的群创建通知，写本地影子群"""
    from ..db import db_cursor
    _gid = body.get('global_group_id')
    _origin = body.get('origin_node')
    _name = body.get('name') or '未命名群'
    if not _gid:
        return {'ok': False, 'error': 'missing global_group_id'}
    with db_cursor() as cur:
        cur.execute("SELECT id FROM groups WHERE global_group_id=?", (_gid,))
        if cur.fetchone():
            return {'ok': True, 'skipped': True}
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO groups (name, owner_id, mode, global_group_id, origin_node) VALUES (?, 1, 'normal', ?, ?)",
                (_name, _gid, _origin)
            )
        return {'ok': True, 'created': True, 'global_group_id': _gid}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

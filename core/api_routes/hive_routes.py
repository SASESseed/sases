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

"""WebSocket 群聊实时推送（阶段 B1）"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set

router = APIRouter(tags=["websocket"])

_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast_to_group(global_group_id: str, message: dict):
    """给指定群的所有 WS 连接推送消息"""
    conns = _connections.get(global_group_id, set())
    dead = []
    for ws in list(conns):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        conns.discard(ws)


@router.websocket("/ws/group/{global_group_id}")
async def ws_group(websocket: WebSocket, global_group_id: str):
    await websocket.accept()
    if global_group_id not in _connections:
        _connections[global_group_id] = set()
    _connections[global_group_id].add(websocket)
    print(f"[ws] client connected to group {global_group_id}, total={len(_connections[global_group_id])}")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _connections.get(global_group_id, set()).discard(websocket)
        print(f"[ws] client disconnected from group {global_group_id}")

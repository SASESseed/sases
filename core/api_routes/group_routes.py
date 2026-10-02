# core/api_routes/group_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import group_service

router = APIRouter(prefix="/group", tags=["group"])
@router.post("/group/{group_id}/leave")
async def api_leave_group(group_id: int):
    return group_service.leave_group(group_id)

@router.post("/group/{group_id}/dismiss")
async def api_dismiss_group(group_id: int):
    return group_service.dismiss_group(group_id)

security = HTTPBearer()


class GroupCreateRequest(BaseModel):
    name: str


class GroupInviteRequest(BaseModel):
    group_id: int
    username_or_id: str


class GroupMessageRequest(BaseModel):
    content: str
    agent_id: Optional[str] = None


class GroupRemoveMemberRequest(BaseModel):
    username_or_id: str


class GroupModeRequest(BaseModel):
    mode: str  # normal 或 swarm


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/create")
async def create_group(body: GroupCreateRequest, user_id: int = Depends(get_current_user)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="群名称不能为空")
    group_id = group_service.create_group(body.name.strip(), user_id)
    return {"group_id": group_id, "name": body.name.strip()}


@router.post("/invite")
async def invite_to_group(body: GroupInviteRequest, user_id: int = Depends(get_current_user)):
    success, msg = group_service.invite_to_group(body.group_id, user_id, body.username_or_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "invited"}


@router.get("/list")
async def list_my_groups(user_id: int = Depends(get_current_user)):
    groups = group_service.list_user_groups(user_id)
    return {"groups": groups}


@router.get("/{group_id}/info")
async def get_group_info(group_id: int, user_id: int = Depends(get_current_user)):
    info = group_service.get_group_info(group_id)
    if not info:
        raise HTTPException(status_code=404, detail="群不存在")
    return info


@router.get("/{group_id}/messages")
async def get_group_messages(group_id: int, user_id: int = Depends(get_current_user)):
    messages = group_service.get_group_messages(group_id, user_id)
    if messages is None:
        raise HTTPException(status_code=403, detail="你不是群成员")
    return {"messages": messages}


@router.post("/{group_id}/messages")
async def send_group_message(group_id: int, body: GroupMessageRequest, user_id: int = Depends(get_current_user)):
    success, msg = group_service.send_group_message(group_id, user_id, body.content, body.agent_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    try:
        from .ws_routes import broadcast_to_group
        from ..db import db_cursor
        with db_cursor() as cur:
            cur.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
            _r = cur.fetchone()
        if _r and _r['global_group_id']:
            await broadcast_to_group(_r['global_group_id'], {
                'type': 'message',
                'content': body.content,
                'sender_id': user_id,
                'sender_agent_id': body.agent_id,
            })
    except Exception as _e:
        print('[ws] push failed:', _e)
    return {"status": "sent"}


@router.get("/{group_id}/members")
async def get_group_members(group_id: int, user_id: int = Depends(get_current_user)):
    members = group_service.list_group_members(group_id)
    return {"members": members}


@router.get("/{group_id}/credits")
async def get_group_credits(group_id: int, user_id: int = Depends(get_current_user)):
    credits = group_service.get_group_credits(group_id)
    return {"credits": credits}


@router.post("/{group_id}/remove-member")
async def remove_member(group_id: int, body: GroupRemoveMemberRequest, user_id: int = Depends(get_current_user)):
    success, msg = group_service.remove_member_from_group(group_id, user_id, body.username_or_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "removed"}


@router.post("/{group_id}/pin")
async def toggle_pin(group_id: int, body: dict, user_id: int = Depends(get_current_user)):
    pinned = bool(body.get('pinned'))
    ok = group_service.toggle_group_pin(group_id, user_id, pinned)
    if not ok:
        raise HTTPException(status_code=403, detail='not a member')
    return {'group_id': group_id, 'pinned': pinned}



@router.post("/{group_id}/read")
async def mark_read(group_id: int, user_id: int = Depends(get_current_user)):
    ok = group_service.mark_group_read(group_id, user_id)
    return {'group_id': group_id, 'read': ok}



@router.post("/{group_id}/mode")
async def set_group_mode(group_id: int, body: GroupModeRequest, user_id: int = Depends(get_current_user)):
    if body.mode not in ("normal", "swarm"):
        raise HTTPException(status_code=400, detail="模式只能是 normal 或 swarm")
    success, msg = group_service.set_group_mode(group_id, body.mode, user_id)
    if not success:
        raise HTTPException(status_code=403, detail=msg)
    return {"status": "updated", "mode": body.mode}



class TaskPublishRequest(BaseModel):
    title: str
    description: str = ''
    category: str = 'text'
    reward: float = 0


class TaskSubmitRequest(BaseModel):
    content: str
    content_type: str = 'text'
    agent_id: Optional[str] = None


class TaskSelectRequest(BaseModel):
    submission_id: int


class TaskRejectRequest(BaseModel):
    reason: str = ''


@router.post("/{group_id}/tasks/publish")
async def api_publish_task(group_id: int, body: TaskPublishRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    ok, res = group_task_service.publish_task(group_id, user_id, body.title, body.description, body.category, body.reward)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/{group_id}/tasks")
async def api_list_tasks(group_id: int, status: Optional[str] = None, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    return {"tasks": group_task_service.list_tasks(group_id, status)}


@router.get("/tasks/{task_id}")
async def api_get_task(task_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    task = group_task_service.get_task_detail(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.post("/tasks/{task_id}/submit")
async def api_submit_task(task_id: int, body: TaskSubmitRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    ok, res = group_task_service.submit_solution(task_id, user_id, body.agent_id, body.content, body.content_type)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/tasks/{task_id}/select")
async def api_select_task(task_id: int, body: TaskSelectRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    ok, res = group_task_service.select_winner(task_id, user_id, body.submission_id)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/tasks/{task_id}/reject")
async def api_reject_task(task_id: int, body: TaskRejectRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    ok, res = group_task_service.reject_all(task_id, user_id, body.reason)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


class StakeRequest(BaseModel):
    amount: float


class RedPacketConfigRequest(BaseModel):
    hour: int
    audience: str = 'all'


@router.post("/{group_id}/stake")
async def api_stake(group_id: int, body: StakeRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.stake_credits(group_id, user_id, body.amount)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/{group_id}/stake/withdraw")
async def api_withdraw_stake(group_id: int, user_id: int = Depends(get_current_user)):
    ok, res = group_service.withdraw_stake(group_id, user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/{group_id}/stakes")
async def api_list_stakes(group_id: int, user_id: int = Depends(get_current_user)):
    return {"stakes": group_service.list_active_stakes(group_id)}


@router.get("/{group_id}/pool")
async def api_group_pool(group_id: int, user_id: int = Depends(get_current_user)):
    detail = group_service.get_group_pool_detail(group_id)
    if not detail:
        raise HTTPException(status_code=404, detail="group not found")
    return detail


@router.post("/{group_id}/red-packet/config")
async def api_config_red_packet(group_id: int, body: RedPacketConfigRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.configure_red_packet(group_id, user_id, body.hour, body.audience)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/{group_id}/red-packet/send")
async def api_send_red_packet(group_id: int, user_id: int = Depends(get_current_user)):
    ok, res = group_service.distribute_group_red_packet(group_id, user_id)
class GroupRedPacketCreateRequest(BaseModel):
    total_amount: float
    total_count: int
    message: str = ''
    source_type: str = 'user'
    packet_type: str = 'lucky'


@router.post("/{group_id}/red-packets/create")
async def api_create_group_red_packet(group_id: int, body: GroupRedPacketCreateRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_red_packet_service
    ok, res = group_red_packet_service.create_packet(group_id, user_id, body.total_amount, body.total_count, body.message, body.source_type, getattr(body, "packet_type", "lucky"))
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/red-packets/{packet_id}/claim")
async def api_claim_group_red_packet(packet_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_red_packet_service
    ok, res = group_red_packet_service.claim_packet(packet_id, user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/red-packets/{packet_id}")
async def api_get_group_red_packet(packet_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_red_packet_service
    detail = group_red_packet_service.get_packet_detail(packet_id, user_id)
    if not detail:
        raise HTTPException(status_code=404, detail="红包不存在")
    return detail


@router.post("/red-packets/expire")
async def api_expire_group_red_packets(user_id: int = Depends(get_current_user)):
    from ..services import group_red_packet_service
    expired = group_red_packet_service.expire_packets()
    return {"expired": expired, "count": len(expired)}



    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


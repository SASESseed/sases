# core/api_routes/group_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import group_service

router = APIRouter(prefix="/group", tags=["group"])
security = HTTPBearer()


class GroupCreateRequest(BaseModel):
    name: str


class GroupInviteRequest(BaseModel):
    group_id: int
    username_or_id: str


class GroupMessageRequest(BaseModel):
    group_id: int
    content: str
    agent_id: Optional[str] = None


class GroupRemoveMemberRequest(BaseModel):
    username_or_id: str


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
    success = group_service.send_group_message(group_id, user_id, body.content, body.agent_id)
    if not success:
        raise HTTPException(status_code=403, detail="发送失败")
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

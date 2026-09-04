# core/api_routes/agent_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])
security = HTTPBearer()

class FriendRequest(BaseModel):
    agent_id: str

class CallAgentRequest(BaseModel):
    agent_id: str
    query: str

class AcceptRequest(BaseModel):
    request_id: int

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@router.get("/list")
async def list_my_agents(user_id: int = Depends(get_current_user)):
    agents = agent_service.list_my_agents(user_id)
    return {"agents": agents}

@router.get("/friends")
async def list_friend_agents(user_id: int = Depends(get_current_user)):
    friends = agent_service.list_friend_agents(user_id)
    return {"friends": friends}

@router.get("/search")
async def search_agents(q: str, user_id: int = Depends(get_current_user)):
    results = agent_service.search_agents(user_id, q)
    return {"results": results}

@router.post("/friend-request")
async def send_friend_request(body: FriendRequest, user_id: int = Depends(get_current_user)):
    try:
        agent_service.send_friend_request(user_id, body.agent_id)
        return {"status": "request_sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/friend-requests")
async def get_received_friend_requests(user_id: int = Depends(get_current_user)):
    requests = agent_service.get_received_friend_requests(user_id)
    return {"requests": requests}

@router.post("/friend-requests/accept")
async def accept_friend_request(body: AcceptRequest, user_id: int = Depends(get_current_user)):
    try:
        agent_service.accept_friend_request(user_id, body.request_id)
        return {"status": "accepted"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/friend-requests/reject")
async def reject_friend_request(body: AcceptRequest, user_id: int = Depends(get_current_user)):
    try:
        agent_service.reject_friend_request(user_id, body.request_id)
        return {"status": "rejected"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/call")
async def call_agent(body: CallAgentRequest, user_id: int = Depends(get_current_user)):
    try:
        result = agent_service.call_agent(user_id, body.agent_id, body.query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

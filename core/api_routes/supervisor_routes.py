# core/api_routes/supervisor_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import supervisor_service

router = APIRouter(prefix="/supervisor", tags=["supervisor"])
security = HTTPBearer()


class ConfirmBody(BaseModel):
    run_id: int


class ProposeBody(BaseModel):
    conversation_id: int
    supervisor_id: str
    goal: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/propose")
async def propose(body: ProposeBody, user_id: int = Depends(get_current_user)):
    rid = supervisor_service.create_proposed_run(user_id, body.conversation_id, body.supervisor_id, body.goal)
    return {'run_id': rid, 'status': 'proposed'}


@router.post("/confirm")
async def confirm(body: ConfirmBody, user_id: int = Depends(get_current_user)):
    ok = supervisor_service.confirm_run(body.run_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='run not found or not proposed')
    return {'run_id': body.run_id, 'status': 'running'}


@router.post("/reject")
async def reject(body: ConfirmBody, user_id: int = Depends(get_current_user)):
    ok = supervisor_service.reject_run(body.run_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='run not found or not proposed')
    return {'run_id': body.run_id, 'status': 'rejected'}


@router.post("/cancel")
async def cancel(body: ConfirmBody, user_id: int = Depends(get_current_user)):
    ok = supervisor_service.cancel_run(body.run_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='run not found or not cancellable')
    return {'run_id': body.run_id, 'status': 'cancelled'}



@router.get("/proposed")
async def get_proposed(conversation_id: int = None, user_id: int = Depends(get_current_user)):
    run = supervisor_service.get_proposed_run(user_id, conversation_id)
    return {'run': run}
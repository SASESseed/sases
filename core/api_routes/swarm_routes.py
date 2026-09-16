# core/api_routes/swarm_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import swarm_service

router = APIRouter(prefix="/swarm", tags=["swarm"])
security = HTTPBearer()


class SwarmPlanRequest(BaseModel):
    conversation_id: int
    user_input: str
    commander_id: Optional[str] = None
    executor_id: Optional[str] = None
    timeout: int = 30


class SwarmCancelRequest(BaseModel):
    task_id: str


class SwarmFeedbackRequest(BaseModel):
    task_id: Optional[str] = None
    original_input: Optional[str] = ""
    feedback_type: Optional[str] = "false_positive"
    note: Optional[str] = ""


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/plan")
async def plan(body: SwarmPlanRequest, user_id: int = Depends(get_current_user)):
    if not body.user_input.strip():
        raise HTTPException(status_code=400, detail="用户输入不能为空")
    result = await swarm_service.plan_task(
        user_id=user_id,
        conversation_id=body.conversation_id,
        user_input=body.user_input.strip(),
        commander_id=body.commander_id,
        executor_id=body.executor_id,
        timeout=body.timeout
    )
    return result


@router.post("/cancel")
async def cancel(body: SwarmCancelRequest, user_id: int = Depends(get_current_user)):
    result = swarm_service.cancel_task(body.task_id, user_id)
    return result


@router.post("/feedback")
async def feedback(body: SwarmFeedbackRequest, user_id: int = Depends(get_current_user)):
    result = swarm_service.submit_feedback(
        user_id=user_id,
        task_id=body.task_id,
        original_input=body.original_input or "",
        feedback_type=body.feedback_type or "false_positive",
        note=body.note or ""
    )
    return result

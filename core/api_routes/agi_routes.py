from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any

from core import agi_coordinator
from core.api_routes.auth_routes import get_current_user

router = APIRouter()

class AGIExecuteRequest(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = {}

class AGIExecuteResponse(BaseModel):
    success: bool
    message: str
    module_id: Optional[str] = None
    result: Any = None

@router.post("/agi/execute", response_model=AGIExecuteResponse)
async def agi_execute(req: AGIExecuteRequest, current_user=Depends(get_current_user)):
    result = agi_coordinator.execute_task(req.query, req.params)
    return result

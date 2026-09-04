# core/api_routes/knowledge_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/list")
async def list_knowledge(user_id: int = Depends(get_current_user)):
    knowledge = knowledge_service.get_user_knowledge(user_id)
    return {"knowledge": knowledge}

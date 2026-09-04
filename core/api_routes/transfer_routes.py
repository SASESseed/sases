# core/api_routes/transfer_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import transfer_service

router = APIRouter(prefix="/transfer", tags=["transfer"])
security = HTTPBearer()


class TransferRequest(BaseModel):
    receiver_id: int
    amount: float
    message: Optional[str] = ""


class RedPacketRequest(BaseModel):
    receiver_id: int
    amount: float
    message: Optional[str] = ""


class TxRequest(BaseModel):
    tx_id: int


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/transfer")
async def create_transfer(body: TransferRequest, user_id: int = Depends(get_current_user)):
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    if body.receiver_id == user_id:
        raise HTTPException(status_code=400, detail="不能转账给自己")
    tx_id = transfer_service.create_transfer(user_id, body.receiver_id, body.amount, 'transfer', body.message)
    success = transfer_service.complete_transfer(tx_id)
    if not success:
        raise HTTPException(status_code=400, detail="积分不足")
    return {"tx_id": tx_id, "status": "completed"}


@router.post("/red-packet")
async def create_red_packet(body: RedPacketRequest, user_id: int = Depends(get_current_user)):
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    if body.receiver_id == user_id:
        raise HTTPException(status_code=400, detail="不能发给自己")
    tx_id = transfer_service.create_transfer(user_id, body.receiver_id, body.amount, 'red_packet', body.message)
    return {"tx_id": tx_id, "status": "pending"}


@router.get("/pending")
async def get_pending_red_packets(user_id: int = Depends(get_current_user)):
    packets = transfer_service.get_pending_transfers(user_id)
    return {"packets": packets}


@router.post("/claim")
async def claim_red_packet(body: TxRequest, user_id: int = Depends(get_current_user)):
    tx = transfer_service.get_transaction(body.tx_id)
    if not tx or tx["receiver_id"] != user_id or tx["status"] != "pending":
        raise HTTPException(status_code=400, detail="无法领取")
    success = transfer_service.complete_transfer(body.tx_id)
    if not success:
        raise HTTPException(status_code=400, detail="领取失败，可能发送方积分不足")
    return {"status": "claimed"}

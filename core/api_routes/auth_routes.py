# core/api_routes/auth_routes.py
import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

from ..db import db_cursor
from ..auth_service import SECRET_KEY

router = APIRouter(tags=["auth"])
security = HTTPBearer()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterRequest(BaseModel):
    username: str
    password: str

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: int, expires_minutes: int = 60 * 24 * 30) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def generate_sases_id() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "sases_" + ''.join(secrets.choice(alphabet) for _ in range(8))

def ensure_sases_id(user_id: int, cur) -> str:
    """确保用户拥有 sases_id，若没有则生成并更新"""
    cur.execute("SELECT sases_id FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    sases_id = row["sases_id"] if row else None
    if not sases_id:
        sases_id = generate_sases_id()
        cur.execute("UPDATE users SET sases_id=? WHERE id=?", (sases_id, user_id))
    return sases_id

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """返回用户字典，包含 id、username、sases_id"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id, username, sases_id FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        sases_id = ensure_sases_id(user_id, cur)

    return {
        "id": user["id"],
        "username": user["username"],
        "sases_id": sases_id
    }

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """返回纯用户ID（整数），供其他模块使用"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@router.post("/token")
async def login_for_access_token(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if not username or not password:
        raise HTTPException(status_code=422, detail="用户名和密码不能为空")
    return await _login(username, password)

@router.post("/auth/login")
async def login_json(body: dict):
    username = body.get("username")
    password = body.get("password")
    if not username or not password:
        raise HTTPException(status_code=422, detail="用户名和密码不能为空")
    return await _login(username, password)

async def _login(username: str, password: str):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id, username, password_hash FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="密码错误")

        # 确保 sases_id 存在
        sases_id = ensure_sases_id(user["id"], cur)

    token = create_access_token(user["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "username": user["username"],
        "sases_id": sases_id
    }

@router.post("/auth/register")
async def register(body: RegisterRequest):
    username = body.username.strip()
    password = body.password
    if not username or not password:
        raise HTTPException(status_code=422, detail="用户名和密码不能为空")
    if len(username) < 2 or len(username) > 32:
        raise HTTPException(status_code=422, detail="用户名长度需在2-32个字符之间")
    if len(password) < 4:
        raise HTTPException(status_code=422, detail="密码长度至少4个字符")

    password_hash = hash_password(password)
    sases_id = generate_sases_id()
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, sases_id) VALUES (?, ?, ?)",
                (username, password_hash, sases_id)
            )
            user_id = cur.lastrowid
    except Exception:
        raise HTTPException(status_code=409, detail="用户名已存在")

    token = create_access_token(user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": username,
        "sases_id": sases_id
    }

@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["id"],
        "username": user["username"],
        "sases_id": user["sases_id"]
    }

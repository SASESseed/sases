from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt

import auth

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = auth.get_user_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    return user

@router.post("/register")
async def register(req: RegisterRequest):
    success, msg = auth.create_user(req.username, req.email, req.password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    user = auth.authenticate_user(req.username, req.password)
    if user:
        auth.add_system_message(user["id"], "欢迎加入SASES！配置你的AI模型，开始积累知识库吧。", "SASES助手")
    return {"message": msg}

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = auth.create_access_token(data={"sub": str(user["id"])})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user=Depends(get_current_user)):
    return {"id": current_user["id"], "username": current_user["username"], "credits": current_user["credits"]}

# 导出 get_current_user 供其他路由使用

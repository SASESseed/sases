import json, os, time, re
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from rank_bm25 import BM25Okapi

import auth

app = FastAPI(title="SASES Web API with Auth", version="0.2.1")

KB_FILE = "success_kb.json"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ---------- 工具函数 ----------
def load_kb():
    if not os.path.exists(KB_FILE):
        return []
    with open(KB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def tokenize(text):
    return re.findall(r"\w+", text.lower())

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = auth.get_user_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    return user

# ---------- 请求模型 ----------
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    source: str

class AwardRequest(BaseModel):
    user_id: int
    amount: int
    reason: str = ""

# ---------- 认证路由 ----------
@app.post("/register")
async def register(req: RegisterRequest):
    success, msg = auth.create_user(req.username, req.email, req.password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = auth.create_access_token(data={"sub": str(user["id"])})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
async def read_users_me(current_user=Depends(get_current_user)):
    return {"id": current_user["id"], "username": current_user["username"], "credits": current_user["credits"]}

# ---------- 排行榜 ----------
@app.get("/leaderboard")
async def leaderboard(top_n: int = 10):
    return auth.get_leaderboard(top_n)

# ---------- 聊天（需认证） ----------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, current_user=Depends(get_current_user)):
    kb = load_kb()
    query = req.query
    if not kb:
        answer = "知识库为空，请先运行种子迭代积累知识库。"
        source = "none"
    else:
        tasks = [item.get("task", "") for item in kb]
        tokenized_tasks = [tokenize(t) for t in tasks]
        bm25 = BM25Okapi(tokenized_tasks)
        scores = bm25.get_scores(tokenize(query))
        best_idx = scores.argmax()
        if scores[best_idx] > 0:
            best = kb[best_idx]
            answer = f"找到相似任务：{best['task']}\n解决方案：\n{best['solution'][:500]}"
            source = "local_kb"
        else:
            answer = "未找到相似任务。"
            source = "none"
    return ChatResponse(answer=answer, source=source)

# ---------- 统计（公开） ----------
@app.get("/stats")
async def stats():
    kb = load_kb()
    model_counts = {}
    for item in kb:
        model = item.get("model_id", "unknown")
        model_counts[model] = model_counts.get(model, 0) + 1
    return {
        "total_success": len(kb),
        "model_distribution": model_counts
    }

# ---------- 积分发放 ----------
@app.post("/award_credits")
async def award_credits(req: AwardRequest, current_user=Depends(get_current_user)):
    # 简单权限：当前版本允许登录用户调用
    # 后续可改为仅管理员或高信誉用户可调用
    auth.add_credits(req.user_id, req.amount, req.reason)
    return {"message": f"已为用户 {req.user_id} 增加 {req.amount} 积分"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

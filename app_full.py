import json, os, time, re, uuid
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jose import JWTError, jwt
from rank_bm25 import BM25Okapi

import auth

app = FastAPI(title="SASES Full Web Service", version="0.3.2")

KB_FILE = "success_kb.json"
SEED_POOL_FILE = "seed_tasks_external.jsonl"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

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
        user_id = payload.get("sub")
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

class AwardRequest(BaseModel):
    user_id: int
    amount: int
    reason: str = ""

class SeedSubmitRequest(BaseModel):
    description: str
    test_cases: list = []

class SettingsUpdateRequest(BaseModel):
    auto_pollinate_enabled: bool

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

# ---------- 授粉设置 ----------
@app.get("/me/settings")
async def get_my_settings(current_user=Depends(get_current_user)):
    settings = auth.get_user_settings(current_user["id"])
    if settings is None:
        raise HTTPException(status_code=404, detail="用户设置不存在")
    return settings

@app.patch("/me/settings")
async def update_my_settings(req: SettingsUpdateRequest, current_user=Depends(get_current_user)):
    auth.update_user_settings(current_user["id"], req.auto_pollinate_enabled)
    return {"message": "设置已更新", "auto_pollinate_enabled": req.auto_pollinate_enabled}

# ---------- 排行榜 ----------
@app.get("/leaderboard")
async def leaderboard(top_n: int = 10):
    return auth.get_leaderboard(top_n)

# ---------- 积分流水 ----------
@app.get("/my_ledger")
async def my_ledger(current_user=Depends(get_current_user)):
    ledger = auth.get_credit_ledger(current_user["id"])
    return {"ledger": ledger}

# ---------- 聊天（需认证） ----------
@app.post("/chat")
async def chat(req: ChatRequest, current_user=Depends(get_current_user)):
    # 获取用户自动授粉设置
    settings = auth.get_user_settings(current_user["id"])
    auto_pollinate = settings.get("auto_pollinate_enabled", True) if settings else True

    if not auto_pollinate:
        # 自动授粉已关闭，仅查询需要扣除积分
        success, msg = auth.deduct_credits(current_user["id"], 2, "仅查询不回流")
        if not success:
            raise HTTPException(status_code=402, detail=msg)

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

    result = {"answer": answer, "source": source}
    if not auto_pollinate:
        result["deducted"] = 2
    return result

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
    auth.add_credits(req.user_id, req.amount, req.reason)
    return {"message": f"已为用户 {req.user_id} 增加 {req.amount} 积分"}

# ---------- 种子提交 ----------
@app.post("/submit_seed")
async def submit_seed(req: SeedSubmitRequest, current_user=Depends(get_current_user)):
    if not req.description or len(req.description) < 10:
        raise HTTPException(status_code=400, detail="任务描述过短")
    seed = {
        "id": str(uuid.uuid4()),
        "description": req.description,
        "test_cases": req.test_cases if req.test_cases else [],
        "source": "external_api",
        "user_id": current_user["id"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(SEED_POOL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(seed, ensure_ascii=False) + "\n")
    return {"message": "种子已提交，等待处理", "seed": seed}

# ---------- 防篡改锚点（预留） ----------
@app.get("/protocol_version")
async def protocol_version():
    return {"version": "1.0.0"}

@app.post("/sync_state")
async def sync_state(current_user=Depends(get_current_user)):
    return {
        "user_id": current_user["id"],
        "credits": current_user["credits"],
        "tampered": False,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# ---------- 根路由 ----------
@app.get("/")
async def root():
    return {"message": "SASES Full Web Service is running. Visit /static/index.html for UI."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

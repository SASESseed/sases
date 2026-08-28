import json, os, time, re, uuid
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jose import JWTError, jwt
from rank_bm25 import BM25Okapi

import auth
import safety_scan
import sandbox
from core import contribution_log
from core import knowledge_base
from core import config

app = FastAPI(title="SASES Full Web Service", version="0.4.8")

KB_FILE = config.KB_FILE
SEED_POOL_FILE = config.SEED_POOL_FILE
SHARED_LOG_FILE = config.SHARED_LOG_FILE
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- 工具函数 ----------
def tokenize(text):
    """文本分词（用于 BM25）"""
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
    user = auth.authenticate_user(req.username, req.password)
    if user:
        auth.add_system_message(user["id"], "欢迎加入SASES！配置你的AI模型，开始积累知识库吧。", "SASES助手")
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

# ---------- 系统消息（SASES助手） ----------
@app.get("/assistant/messages")
async def assistant_messages(current_user=Depends(get_current_user)):
    messages, unread = auth.get_system_messages(current_user["id"])
    return {"messages": messages, "unread": unread}

@app.post("/assistant/read")
async def assistant_read(current_user=Depends(get_current_user)):
    auth.mark_messages_read(current_user["id"])
    return {"message": "已全部标记为已读"}

# ---------- 聊天（需认证） ----------
@app.post("/chat")
async def chat(req: ChatRequest, current_user=Depends(get_current_user)):
    settings = auth.get_user_settings(current_user["id"])
    auto_pollinate = settings.get("auto_pollinate_enabled", True) if settings else True

    kb = knowledge_base.load_kb()
    query = req.query
    source = "none"
    answer = ""

    if not kb:
        answer = "知识库为空，请先运行种子迭代积累知识库。"
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
            contribution_log.log_event(
                user_id=current_user["id"],
                event_type="chat_retrieval",
                target_id=best.get("id", ""),
                metadata={"query": query[:100]}
            )
        else:
            answer = "未找到相似任务。"

    if source == "local_kb" and not auto_pollinate:
        success, msg = auth.deduct_credits(current_user["id"], config.QUERY_DEDUCTION, "仅查询不回流")
        if success:
            auth.add_system_message(current_user["id"], f"本次查询已扣除{config.QUERY_DEDUCTION}积分（自动授粉关闭）。", "SASES助手")

    result = {"answer": answer, "source": source}
    if source == "local_kb" and not auto_pollinate:
        result["deducted"] = config.QUERY_DEDUCTION
    return result

# ---------- 统计（公开） ----------
@app.get("/stats")
async def stats():
    kb = knowledge_base.load_kb()
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
    auth.add_system_message(req.user_id, f"你获得了 {req.amount} 积分：{req.reason}", "SASES助手")
    contribution_log.log_event(
        user_id=req.user_id,
        event_type="credit_award",
        metadata={"amount": req.amount, "reason": req.reason}
    )
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
    auth.add_system_message(current_user["id"], f"种子已收到，等待处理：{req.description[:100]}...", "SASES助手")
    contribution_log.log_event(
        user_id=current_user["id"],
        event_type="seed_submit",
        target_id=seed["id"],
        metadata={"description": req.description[:100]}
    )
    return {"message": "种子已提交，等待处理", "seed": seed}

# ---------- 待授粉内容（仅管理员） ----------
@app.get("/pollinate/pending")
async def pollinate_pending(current_user=Depends(get_current_user)):
    if not auth.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="仅管理员可用")
    entry = knowledge_base.find_pending_pollinate(current_user["id"])
    if not entry:
        return {"has_pending": False}
    return {
        "has_pending": True,
        "kb_id": entry["id"],
        "task_preview": entry["task"][:100],
        "solution_preview": entry["solution"][:200],
        "test_cases_count": len(entry.get("test_cases", []))
    }

@app.post("/pollinate/confirm")
async def pollinate_confirm(current_user=Depends(get_current_user)):
    if not auth.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="仅管理员可用")

    entry = knowledge_base.find_pending_pollinate(current_user["id"])
    if not entry:
        raise HTTPException(status_code=404, detail="没有待授粉的内容")

    test_cases = entry.get("test_cases", [])
    task = entry.get("task", "")
    solution = entry.get("solution", "")

    cond1 = len(test_cases) >= 3
    cond2 = len(solution.split('\n')) >= 4
    cond3 = len(task) >= 15

    if cond1 and cond2 and cond3:
        reward = config.MANUAL_POLLINATE_EXPERT_REWARD
        reason = "手动授粉（专业领域价值）"
    else:
        reward = config.MANUAL_POLLINATE_BASIC_REWARD
        reason = "手动授粉（基础）"

    knowledge_base.add_shared_id(entry["id"])

    auth.add_credits(current_user["id"], reward, reason)
    auth.add_system_message(current_user["id"], f"你的知识成果已成功分享，获得 {reward} 积分。", "SASES助手")
    contribution_log.log_event(
        user_id=current_user["id"],
        event_type="manual_pollinate",
        target_id=entry["id"],
        metadata={"task": task[:100], "reward": reward, "test_cases_count": len(test_cases), "solution_lines": len(solution.split('\n'))}
    )

    return {"message": f"授粉成功，获得 {reward} 积分", "reward": reward, "reason": reason}


@app.get("/admin/contribution_logs")
async def admin_contribution_logs(limit: int = 50, current_user=Depends(get_current_user)):
    if not auth.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="仅管理员可用")
    logs = contribution_log.get_all_logs(limit)
    return {"logs": logs}

# ---------- 防篡改校验 ----------
@app.post("/sync_state")
async def sync_state(current_user=Depends(get_current_user)):
    is_valid = auth.verify_user_integrity(current_user["id"])
    if not is_valid:
        auth.log_tamper_event(current_user["id"], "state hash mismatch during sync")
    return {
        "user_id": current_user["id"],
        "credits": current_user["credits"],
        "tampered": not is_valid,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/admin/check_integrity")
async def admin_check_integrity(current_user=Depends(get_current_user)):
    if not auth.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="仅管理员可用")
    tampered_ids = auth.check_all_users_integrity()
    return {"tampered_user_ids": tampered_ids}

# ---------- 根路由 ----------
@app.get("/")
async def root():
    return {"message": "SASES Full Web Service is running. Visit /static/index.html for UI."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

import json, os, time, re, uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from rank_bm25 import BM25Okapi

import auth
from core import safety_scan
from core import knowledge_base
from core import config
import contribution_log
from core.api_routes.auth_routes import get_current_user

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

class SeedSubmitRequest(BaseModel):
    description: str
    test_cases: list = []

def tokenize(text):
    return re.findall(r"\w+", text.lower())

@router.post("/chat")
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

@router.post("/submit_seed")
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
    with open(config.SEED_POOL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(seed, ensure_ascii=False) + "\n")
    auth.add_system_message(current_user["id"], f"种子已收到，等待处理：{req.description[:100]}...", "SASES助手")
    contribution_log.log_event(
        user_id=current_user["id"],
        event_type="seed_submit",
        target_id=seed["id"],
        metadata={"description": req.description[:100]}
    )
    return {"message": "种子已提交，等待处理", "seed": seed}

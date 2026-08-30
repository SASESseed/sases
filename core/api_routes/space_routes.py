import json, os, time, re, uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from rank_bm25 import BM25Okapi

import auth
from core import safety_scan
from core import knowledge_base
from core import config
from core import contribution_log
from core import agi_coordinator
from core import seed_store
from core.api_routes.auth_routes import get_current_user

router = APIRouter()

def tokenize(text):
    return re.findall(r"\w+", text.lower())

@router.post("/chat")
async def chat(request: Request, current_user=Depends(get_current_user)):
    try:
        data = await request.json()
    except Exception:
        data = {}

    query = str(data.get("query", "")).strip()
    image_base64 = data.get("image")
    audio_base64 = data.get("audio")
    video_base64 = data.get("video")

    settings = auth.get_user_settings(current_user["id"])
    auto_pollinate = settings.get("auto_pollinate_enabled", True) if settings else True

    if audio_base64:
        return {"answer": "音频识别功能尚未接入，请使用文本或图片输入。", "source": "audio", "module_id": None, "result": None}
    if video_base64:
        return {"answer": "视频理解功能尚未接入，请使用文本或图片输入。", "source": "video", "module_id": None, "result": None}

    if image_base64:
        result = agi_coordinator.execute_task_with_image(query, image_base64, user_id=current_user["id"])
        if result["success"]:
            return {"answer": result["result"]["answer"], "source": "multimodal", "module_id": None, "result": result["result"]}
        else:
            return {"answer": f"多模态处理失败：{result['message']}", "source": "multimodal_error", "module_id": None, "result": None}

    agi_result = agi_coordinator.quick_execute(query)
    if agi_result and agi_result["success"]:
        return {"answer": f"🧠 工具执行成功：{agi_result['result']}", "source": "agi", "module_id": agi_result.get("module_id"), "result": agi_result["result"]}

    kb = knowledge_base.load_kb()
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
        if current_user["credits"] < config.QUERY_DEDUCTION:
            raise HTTPException(status_code=402, detail="积分不足，无法查询")
        success, msg = auth.deduct_credits(current_user["id"], config.QUERY_DEDUCTION, "仅查询不回流")
        if not success:
            raise HTTPException(status_code=402, detail=msg or "积分不足，无法查询")
        auth.add_system_message(current_user["id"], f"本次查询已扣除{config.QUERY_DEDUCTION}积分（自动授粉关闭）。", "SASES助手")

    result = {"answer": answer, "source": source}
    if source == "local_kb" and not auto_pollinate:
        result["deducted"] = config.QUERY_DEDUCTION
    return result

@router.post("/submit_seed")
async def submit_seed(request: Request, current_user=Depends(get_current_user)):
    try:
        data = await request.json()
    except Exception:
        data = {}
    description = data.get("description", "")
    test_cases = data.get("test_cases", [])

    if not description or len(description) < 10:
        raise HTTPException(status_code=400, detail="任务描述过短")

    seed = seed_store.add_external_seed(
        description=description,
        test_cases=test_cases,
        user_id=str(current_user["id"])
    )
    auth.add_system_message(current_user["id"], f"种子已收到，等待处理：{description[:100]}...", "SASES助手")
    contribution_log.log_event(
        user_id=current_user["id"],
        event_type="seed_submit",
        target_id=seed["id"],
        metadata={"description": description[:100]}
    )
    return {"message": "种子已提交，等待处理", "seed": seed}

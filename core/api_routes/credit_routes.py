import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List

import auth
from core import contribution_log
from core import knowledge_base
from core import config
from core.api_routes.auth_routes import get_current_user

router = APIRouter()

class AwardRequest(BaseModel):
    user_id: int
    amount: int
    reason: str = ""

class SettingsUpdateRequest(BaseModel):
    auto_pollinate_enabled: bool

class AllSettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]

class ApiKeyCreateRequest(BaseModel):
    provider: str
    key: str
    priority: int = 0

class ApiKeyUpdatePriorityRequest(BaseModel):
    key_id: int
    priority: int

# ---------- 授粉设置（兼容旧接口） ----------
@router.get("/me/settings")
async def get_my_settings(current_user=Depends(get_current_user)):
    settings = auth.get_user_settings(current_user["id"])
    if settings is None:
        raise HTTPException(status_code=404, detail="用户设置不存在")
    return settings

@router.patch("/me/settings")
async def update_my_settings(req: SettingsUpdateRequest, current_user=Depends(get_current_user)):
    auth.update_user_settings(current_user["id"], req.auto_pollinate_enabled)
    return {"message": "设置已更新", "auto_pollinate_enabled": req.auto_pollinate_enabled}

# ---------- 通用设置 ----------
@router.get("/me/settings/all")
async def get_all_my_settings(current_user=Depends(get_current_user)):
    return auth.get_all_user_settings(current_user["id"])

@router.patch("/me/settings/all")
async def update_all_my_settings(req: AllSettingsUpdateRequest, current_user=Depends(get_current_user)):
    updated = auth.update_all_user_settings(current_user["id"], req.settings)
    return {"message": "设置已更新", "settings": updated}

# ---------- API Key 管理 ----------
@router.post("/api_keys")
async def add_api_key(req: ApiKeyCreateRequest, current_user=Depends(get_current_user)):
    auth.add_api_key(current_user["id"], req.provider, req.key, req.priority)
    return {"message": "API Key 已添加"}

@router.get("/api_keys")
async def list_api_keys(current_user=Depends(get_current_user)):
    return auth.list_api_keys(current_user["id"])

@router.delete("/api_keys/{key_id}")
async def delete_api_key(key_id: int, current_user=Depends(get_current_user)):
    auth.delete_api_key(current_user["id"], key_id)
    return {"message": "API Key 已删除"}

@router.patch("/api_keys/priority")
async def update_api_key_priority(req: ApiKeyUpdatePriorityRequest, current_user=Depends(get_current_user)):
    auth.set_api_key_priority(current_user["id"], req.key_id, req.priority)
    return {"message": "优先级已更新"}

# ---------- 排行榜 ----------
@router.get("/leaderboard")
async def leaderboard(top_n: int = 10):
    return auth.get_leaderboard(top_n)

@router.get("/contrib_leaderboard")
async def contrib_leaderboard(top_n: int = 10):
    ranking = contribution_log.get_contrib_leaderboard(top_n)
    result = []
    for item in ranking:
        user = auth.get_user_by_id(item["user_id"])
        username = user["username"] if user else f"user_{item['user_id']}"
        result.append({
            "user_id": item["user_id"],
            "username": username,
            "score": item["score"]
        })
    return result

# ---------- 积分流水 ----------
@router.get("/my_ledger")
async def my_ledger(current_user=Depends(get_current_user)):
    ledger = auth.get_credit_ledger(current_user["id"])
    return {"ledger": ledger}

# ---------- 系统消息 ----------
@router.get("/assistant/messages")
async def assistant_messages(current_user=Depends(get_current_user)):
    messages, unread = auth.get_system_messages(current_user["id"])
    return {"messages": messages, "unread": unread}

@router.post("/assistant/read")
async def assistant_read(current_user=Depends(get_current_user)):
    auth.mark_messages_read(current_user["id"])
    return {"message": "已全部标记为已读"}

# ---------- 积分发放（仅管理员） ----------
@router.post("/award_credits")
async def award_credits(req: AwardRequest, current_user=Depends(get_current_user)):
    if not auth.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="仅管理员可发放积分")
    auth.add_credits(req.user_id, req.amount, req.reason)
    auth.add_system_message(req.user_id, f"你获得了 {req.amount} 积分：{req.reason}", "SASES助手")
    contribution_log.log_event(
        user_id=req.user_id,
        event_type="credit_award",
        metadata={"amount": req.amount, "reason": req.reason}
    )
    return {"message": f"已为用户 {req.user_id} 增加 {req.amount} 积分"}

# ---------- 知识库导出 ----------
@router.get("/kb/export")
async def export_kb(current_user=Depends(get_current_user)):
    kb = auth.export_kb()
    return kb

# ---------- 待授粉内容（仅管理员） ----------
@router.get("/pollinate/pending")
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

@router.post("/pollinate/confirm")
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

# ---------- 防篡改校验 ----------
@router.post("/sync_state")
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

@router.get("/admin/check_integrity")
async def admin_check_integrity(current_user=Depends(get_current_user)):
    if not auth.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="仅管理员可用")
    tampered_ids = auth.check_all_users_integrity()
    return {"tampered_user_ids": tampered_ids}

@router.get("/admin/contribution_logs")
async def admin_contribution_logs(limit: int = 50, current_user=Depends(get_current_user)):
    if not auth.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="仅管理员可用")
    logs = contribution_log.get_all_logs(limit)
    return {"logs": logs}

# ---------- 统计（公开） ----------
@router.get("/stats")
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

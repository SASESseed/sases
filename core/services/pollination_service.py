# core/services/pollination_service.py
from datetime import datetime
from ..db import db_cursor
from .. import safety_scan
from . import credit_service

# 授粉积分规则
POLLINATION_REWARD_BASIC = 1
POLLINATION_REWARD_PROFESSIONAL = 2
POLLINATION_REWARD_EXTREME = 3
POLLINATION_DAILY_LIMIT = 100

# 挑坏果子积分规则
FALSIFY_REWARD = 5
FALSIFY_DAILY_LIMIT = 50


def get_today_pollination_points(user_id: int) -> int:
    """获取用户今日已获得的授粉积分总量"""
    today_start = datetime.combine(datetime.today(), datetime.min.time()).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(points), 0) as total FROM contribution_log
            WHERE user_id=? AND event_type='pollination' AND created_at >= ?
        """, (user_id, today_start))
        row = cur.fetchone()
        return row["total"] if row else 0


def get_today_falsify_points(user_id: int) -> int:
    """获取用户今日已获得的挑坏果子积分总量"""
    today_start = datetime.combine(datetime.today(), datetime.min.time()).isoformat()
    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(points), 0) as total FROM contribution_log
            WHERE user_id=? AND event_type='falsify' AND created_at >= ?
        """, (user_id, today_start))
        row = cur.fetchone()
        return row["total"] if row else 0


def submit_pollination(user_id: int, task_description: str, solution: str, source: str = "manual") -> dict:
    """
    用户提交授粉回流数据。
    流程：
    1. 风险分级检查
    2. 基础价值评估
    3. 写入知识库（示例为打印/返回，正式可扩展）
    4. 发放积分（受每日上限限制）
    """
    # 1. 风险检查
    risk = safety_scan.analyze_risk(solution)
    if risk["level"] == "high":
        return {"accepted": False, "message": risk["message"]}

    # 2. 价值评估（基础价值，后续可接入 LLM 判断）
    value_level = "basic"
    reward = POLLINATION_REWARD_BASIC

    # 3. 简单去重（示例：不真正入库，只返回积分）
    # 实际应写入知识库，此处以日志记录代替
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail)
            VALUES (?, ?, 'pollination', ?, ?)
        """, (user_id, "授粉回流", reward, f"任务：{task_description}"))

    # 4. 发放积分
    today_points = get_today_pollination_points(user_id) + reward
    if today_points > POLLINATION_DAILY_LIMIT:
        actual_reward = max(0, POLLINATION_DAILY_LIMIT - (today_points - reward))
        reward = actual_reward
        if reward <= 0:
            return {"accepted": True, "message": "今日授粉积分已达上限", "reward": 0}

    credit_service.add_credit(user_id, reward, "授粉回流", f"任务：{task_description}", "pollination")

    return {"accepted": True, "message": "授粉成功", "reward": reward}


def submit_falsify(user_id: int, result_id: str, evidence: str) -> dict:
    """
    用户提交证伪反馈。
    流程：
    1. 风险检查证据
    2. 模拟验证（实际应沙箱验证）
    3. 标记污染（示例：写入日志）
    4. 发放积分（受每日上限限制）
    """
    # 1. 风险检查
    risk = safety_scan.analyze_risk(evidence)
    if risk["level"] == "high":
        return {"accepted": False, "message": risk["message"]}

    # 2. 写入污染标记
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO contribution_log (user_id, action, event_type, points, detail)
            VALUES (?, ?, 'falsify', ?, ?)
        """, (user_id, "证伪反馈", FALSIFY_REWARD, f"结果ID：{result_id}，证据：{evidence}"))

    # 3. 发放积分
    today_points = get_today_falsify_points(user_id) + FALSIFY_REWARD
    if today_points > FALSIFY_DAILY_LIMIT:
        actual_reward = max(0, FALSIFY_DAILY_LIMIT - (today_points - FALSIFY_REWARD))
        reward = actual_reward
        if reward <= 0:
            return {"accepted": True, "message": "今日证伪积分已达上限", "reward": 0}
    else:
        reward = FALSIFY_REWARD

    credit_service.add_credit(user_id, reward, "挑坏果子", f"结果ID：{result_id}", "falsify")

    return {"accepted": True, "message": "证伪反馈已记录", "reward": reward}

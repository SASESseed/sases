import re
from typing import Dict, Any, Optional

from core.harness_runtime import harness_runtime
from core import seed_utils

def _keyword_match_tool(query: str):
    """简单关键词匹配，返回匹配到的模块ID或None"""
    tools = harness_runtime.list_tools()
    query_lower = query.lower()

    for tool in tools:
        for cap in tool.capabilities:
            if cap.lower() in query_lower:
                return tool.module_id
        if tool.name.lower() in query_lower:
            return tool.module_id
        if tool.description.lower() in query_lower:
            return tool.module_id

    if "摄氏" in query and ("华氏" in query or "fahrenheit" in query_lower):
        return "unit-converter"
    if "华氏" in query and ("摄氏" in query or "celsius" in query_lower):
        return "unit-converter"
    if "温度" in query and "转换" in query:
        return "unit-converter"

    return None

def _llm_select_tool(query: str) -> Optional[str]:
    tools = harness_runtime.list_tools()
    if not tools:
        return None

    tool_descriptions = []
    for tool in tools:
        tool_descriptions.append(f"- {tool.module_id}: {tool.name} - {tool.description} (能力: {', '.join(tool.capabilities)})")
    tools_text = "\n".join(tool_descriptions)

    prompt = f"""你是 SASES 的工具选择器。根据用户任务，从下面的工具列表中选择最合适的一个工具来完成任务。
如果都不合适，返回 "none"。

工具列表：
{tools_text}

用户任务：
{query}

请只回复工具 ID，不要附加其他文字。"""
    try:
        response = seed_utils.call_chat(prompt, temperature=0.0)
        selected = response.strip().lower()
        if selected == "none":
            return None
        for tool in tools:
            if tool.module_id == selected:
                return selected
        return None
    except Exception as e:
        print(f"LLM 工具选择失败: {e}")
        return None

def _extract_params_for_tool(query: str, module_id: str) -> Optional[Dict[str, Any]]:
    """根据工具类型从自然语言查询中提取参数"""
    if module_id == "unit-converter":
        match = re.search(r'[-+]?\d+(?:\.\d+)?', query)
        if not match:
            return None
        value = float(match.group())

        if "摄氏" in query and "华氏" in query:
            if query.index("摄氏") < query.index("华氏"):
                return {"celsius": value}
            else:
                return {"fahrenheit": value}
        elif "摄氏" in query:
            return {"celsius": value}
        elif "华氏" in query:
            return {"fahrenheit": value}
        else:
            return None
    else:
        # 通用工具：传递整个查询作为 query 参数，由模块自行处理
        return {"query": query}

def execute_task(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    AGI 协调器入口：根据用户输入执行任务。
    返回统一格式的结果。
    """
    if params is None:
        params = {}

    # 第一步：关键词匹配
    module_id = _keyword_match_tool(query)
    if module_id is None:
        # 第二步：LLM 选择工具
        module_id = _llm_select_tool(query)

    if module_id is None:
        return {
            "success": False,
            "message": "没有找到合适的工具来处理这个任务。",
            "module_id": None,
            "result": None
        }

    # 如果没有提供参数，尝试从查询中提取
    if not params:
        extracted = _extract_params_for_tool(query, module_id)
        if extracted is None:
            return {
                "success": False,
                "message": "无法从任务描述中提取参数，请提供更明确的信息。",
                "module_id": module_id,
                "result": None
            }
        params = extracted

    # 调用工具
    response = harness_runtime.invoke_tool(module_id, params)
    if response.success:
        return {
            "success": True,
            "message": "任务执行成功",
            "module_id": module_id,
            "result": response.result
        }
    else:
        return {
            "success": False,
            "message": response.error or "工具执行失败",
            "module_id": module_id,
            "result": None
        }

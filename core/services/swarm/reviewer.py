from typing import Dict, Any, Tuple

ERROR_KEYWORDS = [
    "FINDSTR: 无法打开",
    "FINDSTR: Cannot open",
    "系统找不到指定的路径",
    "系统找不到指定的文件",
    "The system cannot find",
    "No such file",
    "拒绝访问",
    "Access is denied",
    "Access denied",
    "不是内部或外部命令",
    "is not recognized as an internal",
    "无法将",
    "cannot be found",
]

COMMANDS_THAT_SHOULD_OUTPUT = ("dir", "ls", "type", "cat", "findstr", "grep", "find", "where")

UNRECOVERABLE_KEYWORDS = ["找不到文件", "系统找不到", "文件不存在", "拒绝访问", "Access is denied"]


def review_step(step: Dict[str, Any], status: str, output: str) -> Tuple[str, str]:
    # 查询类命令"没找到"属于正常结果，不算失败
    cmd = (step.get("command") or "").strip()
    cmd_first = cmd.split()[0].lower() if cmd.split() else ""
    if cmd_first in ("findstr", "find", "grep", "where") and status == "failed":
        _out = (output or "").lower()
        if "cannot open" in _out or "无法打开" in _out or "系统找不到" in _out or "cannot find" in _out:
            return "retry", "目标文件不存在，路径可能有误"
        return "pass", "查询无结果（正常）"

    if status in ("failed", "timeout", "error", "format_error"):
        detail = (output or "").strip()[:200]
        return "retry", f"命令状态: {status} | {detail}"

    if status == "blocked":
        return "retry", "命令被安全策略拒绝"

    if status == "skipped":
        return "retry", "跳过：依赖步骤失败"

    output_str = output or ""
    output_lower = output_str.lower()
    for kw in ERROR_KEYWORDS:
        if kw.lower() in output_lower:
            return "retry", f"输出含错误: {kw}"

    if cmd_first in COMMANDS_THAT_SHOULD_OUTPUT and not output_str.strip():
        return "retry", "命令应有输出但为空"

    return "pass", ""

# -*- coding: utf-8 -*-
import requests, time, json, sys, subprocess, datetime, re

BASE_URL = "http://127.0.0.1:8001"

# ========== 安全配置 ==========

ALLOWED_COMMANDS = {
    # 目录
    "dir", "ls", "tree",
    # 文件内容
    "type", "cat", "head", "tail",
    # 搜索
    "findstr", "find", "grep", "where",
    # 系统信息
    "echo", "pwd", "cd", "whoami", "hostname",
    # 统计
    "wc",
}

DANGEROUS_CHARS = ['&', '<', '>', '^', '%', ';', '`', '$', '\n', '\r']

MAX_OUTPUT_LENGTH = 2000
DEFAULT_TIMEOUT = 30


def is_command_safe(cmd):
    """检查命令是否安全，返回 (is_safe, reason)"""
    if not cmd or not cmd.strip():
        return False, "命令为空"

    # 1. 危险字符检查
    for ch in DANGEROUS_CHARS:
        if ch in cmd:
            return False, f"包含禁止字符: {repr(ch)}"

    # 2. 按管道符拆分，逐段检查
    parts = [p.strip() for p in cmd.split('|')]
    if any(not p for p in parts):
        return False, "存在空的管道段"

    for part in parts:
        tokens = part.split()
        if not tokens:
            continue

        base = tokens[0].lower()

        # 去掉路径前缀（拒绝带路径的命令）
        if '\\' in base or '/' in base:
            return False, f"命令含路径: {base}"

        # 去掉 .exe/.bat/.cmd 后缀
        if base.endswith('.exe') or base.endswith('.bat') or base.endswith('.cmd'):
            base = base.rsplit('.', 1)[0]

        if base not in ALLOWED_COMMANDS:
            return False, f"命令不在白名单: {base}"

    return True, ""


def smart_decode(raw_bytes):
    """智能解码：依次尝试 utf-8、gbk、latin-1"""
    if not raw_bytes:
        return ""
    for enc in ["utf-8", "gbk", "latin-1"]:
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def login(username, password):
    resp = requests.post(f"{BASE_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_new_messages(token, conv_id, after_id):
    resp = requests.get(f"{BASE_URL}/messages/conversations/{conv_id}/messages",
        params={"after_id": after_id},
        headers={"Authorization": f"Bearer {token}"})
    return resp.json().get("messages", []) if resp.status_code == 200 else []


def send_message(token, conv_id, content, agent_id):
    requests.post(f"{BASE_URL}/messages/send",
        json={"conversation_id": conv_id, "content": content, "sender_agent_id": agent_id},
        headers={"Authorization": f"Bearer {token}"})


def execute_command(cmd, timeout=DEFAULT_TIMEOUT):
    start = datetime.datetime.now()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            timeout=timeout
        )
        output = smart_decode(result.stdout or b"") + smart_decode(result.stderr or b"")
        status = "success" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        output, status = f"命令执行超时（>{timeout}秒）", "timeout"
    except Exception as e:
        output, status = f"命令执行异常: {e}", "error"

    # 输出长度限制
    if len(output) > MAX_OUTPUT_LENGTH:
        output = output[:MAX_OUTPUT_LENGTH] + f"\n... (已截断，原长 {len(output)} 字符)"

    dur = int((datetime.datetime.now() - start).total_seconds() * 1000)
    return output, status, dur


def substitute_placeholders(cmd, previous_outputs):
    if not previous_outputs:
        return cmd

    def replace_match(match):
        step_num = int(match.group(1))
        if step_num in previous_outputs:
            output = previous_outputs[step_num]
            for line in output.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.count("�") > 2:
                    continue
                if any(c in line for c in ["\\", "/", ":"]) and len(line) > 3:
                    return line
                return line
        return match.group(0)

    cmd = re.sub(r'\{\{step(\d+)\}\}', replace_match, cmd)
    cmd = re.sub(r'\{step(\d+)\}', replace_match, cmd)
    return cmd


def handle_task(token, conv_id, executor_id, task):
    task_id = task.get("task_id")
    steps = task.get("steps", [])
    print(f"\n[执行者] 收到任务 {task_id}，共 {len(steps)} 步")

    previous_outputs = {}

    for step in steps:
        step_id = step.get("step")
        desc = step.get("description", "")
        cmd_raw = step.get("command", "")

        cmd = substitute_placeholders(cmd_raw, previous_outputs)

        print(f"  步骤 {step_id}: {desc}")
        if cmd != cmd_raw:
            print(f"    原命令: {cmd_raw}")
            print(f"    替换后: {cmd}")

        # ========== 安全检查 ==========
        is_safe, reason = is_command_safe(cmd)
        if not is_safe:
            print(f"    ⛔ 命令被拒绝: {reason}")
            output = f"命令被安全策略拒绝: {reason}"
            status = "blocked"
            dur = 0
        else:
            print(f"    命令: {cmd}")
            output, status, dur = execute_command(cmd)
            print(f"    结果: {status} ({dur}ms)")
            print(f"    输出: {output[:200]}")

        # 只有执行成功才记录输出（供后续步骤引用）
        if status == "success":
            previous_outputs[step_id] = output

        step_done = {
            "task_id": task_id,
            "step": step_id,
            "description": desc,
            "status": status,
            "output": output[:500],
            "duration_ms": dur
        }
        send_message(token, conv_id,
            "[STEP_DONE]:" + json.dumps(step_done, ensure_ascii=False),
            executor_id)

    print(f"[执行者] 任务 {task_id} 全部步骤完成")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("用法: python executor_v2.py 用户名 密码 会话ID 指挥官智能体ID 执行者智能体ID")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    conv_id = int(sys.argv[3])
    commander_id, executor_id = sys.argv[4], sys.argv[5]

    token = login(username, password)
    print("执行者已登录，等待任务...")
    print(f"安全策略: 白名单 {len(ALLOWED_COMMANDS)} 条命令，禁止字符 {len(DANGEROUS_CHARS)} 个")

    last_id = 0
    msgs = get_new_messages(token, conv_id, 0)
    if msgs:
        last_id = max(m["id"] for m in msgs)
    print(f"当前最新消息ID: {last_id}")

    while True:
        new_msgs = get_new_messages(token, conv_id, last_id)
        for msg in new_msgs:
            last_id = max(last_id, msg["id"])
            content = msg.get("content", "")
            if msg.get("sender_agent_id") != commander_id:
                continue

            if content.startswith("[TASK]:"):
                try:
                    task = json.loads(content[len("[TASK]:"):])
                except json.JSONDecodeError:
                    print("任务格式解析失败，跳过")
                    continue
                handle_task(token, conv_id, executor_id, task)

            elif content.startswith("[RETRY_TASK]:"):
                try:
                    task = json.loads(content[len("[RETRY_TASK]:"):])
                except json.JSONDecodeError:
                    print("重试任务格式解析失败，跳过")
                    continue
                print("\n[执行者] 收到重试任务")
                handle_task(token, conv_id, executor_id, task)

        time.sleep(3)

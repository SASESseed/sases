import json
import re
import uuid
import datetime

from core.db import get_db

KB_FILE = "success_kb.json"  # 保留常量，可能在其他地方引用，但已不使用文件

def _row_to_dict(row):
    if not row:
        return None
    d = dict(row)
    # 解析 test_cases 字段
    if d.get("test_cases"):
        try:
            d["test_cases"] = json.loads(d["test_cases"])
        except:
            d["test_cases"] = []
    else:
        d["test_cases"] = []
    return d

def load_kb():
    """加载知识库列表，按时间戳升序"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM kb_entries ORDER BY timestamp ASC").fetchall()
        return [_row_to_dict(row) for row in rows]

def save_kb(entries):
    """全量保存（用于兼容，但实际不使用；保留空实现避免其他代码报错）"""
    # 迁移后不再支持全量覆盖，可以忽略或记录警告
    print("警告：save_kb 已弃用，请使用 add_to_kb 逐个添加")
    pass

def add_to_kb(task, branch_a, branch_b, synthesis, model_id="unknown", user_id="system", backtrack_count=0, test_cases=None):
    """向知识库添加一条记录"""
    entry_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO kb_entries (id, task, branch_a, branch_b, solution, verified, model_id, user_id, timestamp, backtrack_count, test_cases)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
        """, (
            entry_id, task, branch_a, branch_b, synthesis, model_id, user_id, timestamp, backtrack_count,
            json.dumps(test_cases) if test_cases is not None else None
        ))

def tokenize(text):
    return re.findall(r"\w+", text.lower())

def load_shared_ids():
    # 分享日志仍为 jsonl 文件，暂时保留原实现；后续可迁移到 SQLite
    import os
    if not os.path.exists("shared_pollinate_log.jsonl"):
        return set()
    with open("shared_pollinate_log.jsonl", "r", encoding="utf-8") as f:
        ids = set()
        for line in f:
            try:
                data = json.loads(line)
                ids.add(data.get("kb_id"))
            except:
                pass
        return ids

def add_shared_id(kb_id):
    import os, time
    with open("shared_pollinate_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"kb_id": kb_id, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")

def find_pending_pollinate(user_id):
    kb = load_kb()
    shared_ids = load_shared_ids()
    for entry in reversed(kb):
        if entry.get("model_id") != "manual_pollinate":
            continue
        if entry.get("id") not in shared_ids and entry.get("user_id") == user_id:
            return entry
    return None

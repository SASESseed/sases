import json
import os
import re
import time

KB_FILE = "success_kb.json"
SHARED_LOG_FILE = "shared_pollinate_log.jsonl"

def load_kb():
    """加载知识库，返回条目列表。"""
    if not os.path.exists(KB_FILE):
        return []
    with open(KB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_kb(entries):
    """保存知识库。"""
    with open(KB_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

def tokenize(text):
    """文本分词（用于 BM25）。"""
    return re.findall(r"\w+", text.lower())

def load_shared_ids():
    """加载已分享的知识库条目ID集合。"""
    if not os.path.exists(SHARED_LOG_FILE):
        return set()
    with open(SHARED_LOG_FILE, "r", encoding="utf-8") as f:
        ids = set()
        for line in f:
            try:
                data = json.loads(line)
                ids.add(data.get("kb_id"))
            except:
                pass
        return ids

def add_shared_id(kb_id):
    """记录一个已分享的知识库条目ID。"""
    with open(SHARED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"kb_id": kb_id, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")

def find_pending_pollinate(user_id):
    """查找指定用户最近一条可分享但尚未分享的手动授粉记录。"""
    kb = load_kb()
    shared_ids = load_shared_ids()
    for entry in reversed(kb):
        # 只允许手动授粉的记录进入待分享流程
        if entry.get("model_id") != "manual_pollinate":
            continue
        if entry.get("id") not in shared_ids and entry.get("user_id") == user_id:
            return entry
    return None

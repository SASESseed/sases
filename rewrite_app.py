app_content = '''import json, os, re
from fastapi import FastAPI
from pydantic import BaseModel
from rank_bm25 import BM25Okapi

app = FastAPI(title="SASES Minimal Web API", version="0.2.0")

KB_FILE = "success_kb.json"

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    source: str

def load_kb():
    if not os.path.exists(KB_FILE):
        return []
    with open(KB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def tokenize(text):
    return re.findall(r"\\w+", text.lower())

@app.get("/stats")
async def stats():
    kb = load_kb()
    model_counts = {}
    for item in kb:
        model = item.get("model_id", "unknown")
        model_counts[model] = model_counts.get(model, 0) + 1
    return {
        "total_success": len(kb),
        "model_distribution": model_counts,
        "recent_tasks": kb[-5:]
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    kb = load_kb()
    query = req.query
    if not kb:
        return ChatResponse(answer="知识库为空，请先运行种子迭代积累知识库。", source="none")
    tasks = [item.get("task", "") for item in kb]
    tokenized_tasks = [tokenize(t) for t in tasks]
    bm25 = BM25Okapi(tokenized_tasks)
    scores = bm25.get_scores(tokenize(query))
    best_idx = scores.argmax()
    if scores[best_idx] > 0:
        best = kb[best_idx]
        answer = f"找到相似任务：{best['task']}\\n解决方案：\\n{best['solution'][:500]}"
        source = "local_kb"
    else:
        answer = "未找到相似任务，请先运行种子迭代积累知识库。"
        source = "none"
    return ChatResponse(answer=answer, source=source)
'''

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_content)

print("app.py 已完整替换为 BM25 版本。")

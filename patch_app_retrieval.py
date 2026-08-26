import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 在文件开头添加 rank_bm25 导入
if "from rank_bm25 import BM25Okapi" not in content:
    content = content.replace(
        "import json, os, time",
        "import json, os, time\nfrom rank_bm25 import BM25Okapi"
    )

# 替换 chat 函数中的检索部分
old_block = '''    # 极简检索：线性扫描最近20条
    kb = load_kb()
    query = req.query
    # 检索最相似的一条（简单包含匹配）
    best = None
    for item in kb[-200:]:
        if query in item.get("task", "") or item.get("task", "") in query:
            best = item
            break
    if best:
        answer = f"找到相似任务：{best['task']}\\n解决方案：\\n{best['solution'][:500]}"
        source = "local_kb"
    else:
        answer = "未找到相似任务，请先运行种子迭代积累知识库。"
        source = "none"
    return ChatResponse(answer=answer, source=source)'''

new_block = '''    # 使用 BM25 进行关键词检索
    kb = load_kb()
    query = req.query

    def tokenize(text):
        return re.findall(r"\\w+", text.lower())

    if not kb:
        answer = "知识库为空，请先运行种子迭代积累知识库。"
        source = "none"
    else:
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
    return ChatResponse(answer=answer, source=source)'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("检索逻辑已替换为 BM25。")
else:
    print("警告：未找到原检索代码块，可能需要手动修改。")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("补丁完成！")

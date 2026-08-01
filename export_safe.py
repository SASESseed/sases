import chromadb, json

db = chromadb.PersistentClient(path="./kb")
coll = db.get_collection("successes")
data = coll.get()

with open("fine_tune_data.jsonl", "w", encoding="utf-8") as f:
    for i, (doc, meta) in enumerate(zip(data["documents"], data["metadatas"])):
        # 清洗 doc：移除多余的空白和不可见字符
        doc_clean = doc.strip()
        record = {
            "messages": [
                {"role": "user", "content": f"任务：{meta['task']}\n请写出一个完整可运行的Python函数。只需输出代码。"},
                {"role": "assistant", "content": doc_clean}
            ]
        }
        line = json.dumps(record, ensure_ascii=False)
        f.write(line + "\n")

print(f"已导出 {len(data['documents'])} 条数据")

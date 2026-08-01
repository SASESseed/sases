import chromadb, json

db = chromadb.PersistentClient(path="./kb")
coll = db.get_collection("successes")
data = coll.get()  # 获取全部

with open("fine_tune_data.jsonl", "w", encoding="utf-8") as f:
    for i, (doc, meta) in enumerate(zip(data["documents"], data["metadatas"])):
        # 构造指令微调格式：system+user+assistant
        record = {
            "messages": [
                {"role": "user", "content": f"任务：{meta['task']}\n请写出一个完整可运行的Python函数。只需输出代码。"},
                {"role": "assistant", "content": doc}
            ]
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"已导出 {len(data['documents'])} 条数据到 fine_tune_data.jsonl")

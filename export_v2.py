import json

with open("success_kb.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

with open("finetune_data_v2.jsonl", "w", encoding="utf-8") as out:
    for entry in kb:
        record = {
            "messages": [
                {"role": "user", "content": f"任务：{entry['task']}\n请写出一个完整可运行的解决方案。"},
                {"role": "assistant", "content": entry["solution"]}
            ]
        }
        out.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"已导出 {len(kb)} 条训练数据 → finetune_data_v2.jsonl")

import json, chromadb, uuid

db = chromadb.PersistentClient(path="./kb")
seed_col = db.get_or_create_collection("seeds")

with open("seed_tasks.jsonl", "r", encoding="utf-8") as f:
    count = 0
    for line in f:
        seed = json.loads(line)
        desc = seed.get("description") or seed.get("task") or seed.get("prompt") or ""
        seed_col.add(
            documents=[desc],
            metadatas=[{
                "task_id": seed.get("task_id", ""),
                "category": seed.get("category", ""),
                "difficulty": seed.get("difficulty", "")
            }],
            ids=[str(uuid.uuid4())]
        )
        count += 1
print(f"已导入 {count} 个种子到种子库。")

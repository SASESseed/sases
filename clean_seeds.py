import json

valid = []
with open("seed_tasks.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        try:
            obj = json.loads(line)
            if "description" in obj:
                valid.append(obj)
            else:
                # 尝试从 instruction/input 拼接为 description
                desc = obj.get("instruction","") + " " + obj.get("input","")
                if desc.strip():
                    valid.append({"description": desc.strip(), "test_cases": []})
        except:
            pass

with open("seed_tasks_clean.jsonl", "w", encoding="utf-8") as f:
    for v in valid:
        f.write(json.dumps(v, ensure_ascii=False) + "\n")
print(f"清洗完成，有效种子数：{len(valid)}")

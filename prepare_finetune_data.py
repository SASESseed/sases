import json

with open("success_trajectories.jsonl", "r", encoding="utf-8") as f:
    lines = f.readlines()

with open("finetune_data.jsonl", "w", encoding="utf-8") as out:
    for line in lines:
        t = json.loads(line)
        # 自动寻找字段
        task = t.get("task") or t.get("description") or t.get("prompt") or t.get("question") or ""
        synthesis = t.get("synthesis") or t.get("final_code") or t.get("output") or t.get("result") or t.get("solution") or ""
        record = {
            "messages": [
                {"role": "user", "content": f"任务：{task}\n请综合不同思路，给出一个完整可运行的解决方案。"},
                {"role": "assistant", "content": synthesis}
            ]
        }
        out.write(json.dumps(record, ensure_ascii=False) + "\n")
print("✅ finetune_data.jsonl 已生成")

import json

KB_FILE = "success_kb.json"
OUT_FILE = "finetune_data.jsonl"

def main():
    with open(KB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"知识库记录数: {len(data)}")
    
    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for item in data:
            task = item.get("task", "")
            solution = item.get("solution", "")
            # 生成指令微调格式：只使用任务描述和解决方案
            record = {
                "messages": [
                    {"role": "user", "content": f"任务：{task}\n请写出一个完整可运行的Python函数。只需输出代码。"},
                    {"role": "assistant", "content": solution}
                ]
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"已导出 {len(data)} 条微调数据到 {OUT_FILE}")

if __name__ == "__main__":
    main()

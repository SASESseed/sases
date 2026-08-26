import json, os

EXTERNAL_FILE = "seed_tasks_external.jsonl"
MAIN_FILE = "seed_tasks_new.jsonl"
MERGED_FILE = "seed_tasks_new_merged.jsonl"

def load_jsonl(path):
    if not os.path.exists(path):
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                items.append(json.loads(line))
            except:
                pass
    return items

def main():
    external = load_jsonl(EXTERNAL_FILE)
    existing = load_jsonl(MAIN_FILE)
    
    if not external:
        print("没有外部种子需要合并。")
        return
    
    # 去重：使用 description 作为去重键
    existing_descs = {item.get("description", "") for item in existing}
    new_items = []
    for seed in external:
        desc = seed.get("description", "")
        if desc and desc not in existing_descs:
            # 确保有 test_cases 字段
            if "test_cases" not in seed:
                seed["test_cases"] = []
            new_items.append(seed)
            existing_descs.add(desc)
    
    if not new_items:
        print("外部种子均已存在于主种子池，无需合并。")
        return
    
    # 合并写入新文件
    merged = existing + new_items
    with open(MERGED_FILE, "w", encoding="utf-8") as f:
        for item in merged:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"合并完成：原主池 {len(existing)} 条，外部新增 {len(new_items)} 条，合计 {len(merged)} 条。")
    print(f"已写入 {MERGED_FILE}")
    
    # 备份原主池
    if os.path.exists(MAIN_FILE):
        os.replace(MAIN_FILE, MAIN_FILE + ".bak")
        print(f"原主池已备份为 {MAIN_FILE}.bak")
    
    # 用合并后的文件替换原主池
    os.replace(MERGED_FILE, MAIN_FILE)
    print(f"主种子池已更新为合并后的 {MAIN_FILE}")
    
    # 清空外部种子池（已合并）
    with open(EXTERNAL_FILE, "w", encoding="utf-8") as f:
        pass
    print(f"外部种子池已清空，等待新提交。")

if __name__ == "__main__":
    main()

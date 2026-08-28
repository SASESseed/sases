import json, os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import auth
from core import config
from core import similarity

EXTERNAL_FILE = config.SEED_POOL_FILE          # seed_tasks_external.jsonl
MAIN_FILE = config.MAIN_SEED_FILE              # seed_tasks_new.jsonl
MERGED_FILE = config.MAIN_SEED_FILE + ".merged"
KB_FILE = config.KB_FILE

SIMILARITY_THRESHOLD = config.SIMILARITY_THRESHOLD

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

def load_kb_descriptions():
    """加载知识库中所有已存在的任务描述"""
    if not os.path.exists(KB_FILE):
        return []
    with open(KB_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except:
            return []
    return [item.get("task", "") for item in data]

def main():
    external = load_jsonl(EXTERNAL_FILE)
    existing = load_jsonl(MAIN_FILE)

    if not external:
        print("没有外部种子需要合并。")
        return

    # 加载知识库已有任务描述
    kb_descs = load_kb_descriptions()

    # 当前所有已存在描述（主池 + 知识库）
    existing_descs = [item.get("description", "") for item in existing] + kb_descs

    new_items = []
    skipped = 0
    for seed in external:
        desc = seed.get("description", "")
        if not desc:
            continue
        user_id = seed.get("user_id")

        # 先检查完全相同
        if desc in existing_descs:
            print(f"跳过重复任务（完全相同）：{desc[:50]}...")
            if user_id is not None:
                try:
                    auth.add_system_message(
                        int(user_id),
                        f"感谢你的贡献！你的种子已存在于知识库或待处理池中，无需重复提交：{desc[:100]}...",
                        "SASES助手"
                    )
                except Exception as e:
                    print(f"发送系统消息失败: {e}")
            skipped += 1
            continue

        # 再检查语义相似
        if similarity.is_similar(desc, existing_descs, threshold=SIMILARITY_THRESHOLD):
            print(f"跳过重复任务（语义相似）：{desc[:50]}...")
            if user_id is not None:
                try:
                    auth.add_system_message(
                        int(user_id),
                        f"感谢你的贡献！你的种子与已有任务语义相似，无需重复提交：{desc[:100]}...",
                        "SASES助手"
                    )
                except Exception as e:
                    print(f"发送系统消息失败: {e}")
            skipped += 1
            continue

        if "test_cases" not in seed:
            seed["test_cases"] = []
        new_items.append(seed)
        existing_descs.append(desc)

    if not new_items:
        print("所有外部种子均为重复任务，已全部跳过。")
        with open(EXTERNAL_FILE, "w", encoding="utf-8") as f:
            pass
        return

    # 合并写入新文件
    merged = existing + new_items
    with open(MERGED_FILE, "w", encoding="utf-8") as f:
        for item in merged:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"合并完成：原主池 {len(existing)} 条，外部新增 {len(new_items)} 条，跳过重复 {skipped} 条，合计 {len(merged)} 条。")

    if os.path.exists(MAIN_FILE):
        os.replace(MAIN_FILE, MAIN_FILE + ".bak")
        print(f"原主池已备份为 {MAIN_FILE}.bak")
    os.replace(MERGED_FILE, MAIN_FILE)
    print(f"主种子池已更新为 {MAIN_FILE}")

    # 不在此处奖励积分，积分奖励在 process_seeds.py 成功处理后发放

    with open(EXTERNAL_FILE, "w", encoding="utf-8") as f:
        pass
    print(f"外部种子池已清空。")

if __name__ == "__main__":
    main()

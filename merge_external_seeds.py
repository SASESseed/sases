import json, os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import auth

EXTERNAL_FILE = "seed_tasks_external.jsonl"
MAIN_FILE = "seed_tasks_new.jsonl"
MERGED_FILE = "seed_tasks_new_merged.jsonl"
KB_FILE = "success_kb.json"

SIMILARITY_THRESHOLD = 0.30  # 相似度超过此值视为重复

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

def is_similar(new_desc, existing_descs, threshold=SIMILARITY_THRESHOLD):
    """使用字符级 TF-IDF 余弦相似度判断是否重复"""
    if not existing_descs:
        return False
    corpus = existing_descs + [new_desc]
    vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3))
    try:
        existing_vecs = vectorizer.fit_transform(existing_descs)
        new_vec = vectorizer.transform([new_desc])
        sims = cosine_similarity(new_vec, existing_vecs).flatten()
        return bool((sims > threshold).any())
    except Exception as e:
        print(f"相似度计算异常: {e}")
        return False

def main():
    external = load_jsonl(EXTERNAL_FILE)
    existing = load_jsonl(MAIN_FILE)

    if not external:
        print("没有外部种子需要合并。")
        return

    kb_descs = load_kb_descriptions()
    existing_descs = [item.get("description", "") for item in existing] + kb_descs

    new_items = []
    skipped = 0
    for seed in external:
        desc = seed.get("description", "")
        if not desc:
            continue
        user_id = seed.get("user_id")

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

        if is_similar(desc, existing_descs):
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

    with open(EXTERNAL_FILE, "w", encoding="utf-8") as f:
        pass
    print(f"外部种子池已清空。")

if __name__ == "__main__":
    main()

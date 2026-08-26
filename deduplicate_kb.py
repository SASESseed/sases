import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

THRESHOLD = 0.85  # 相似度超过此值视为重复

# 加载
with open("success_kb.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

# 备份
with open("success_kb_backup.json", "w", encoding="utf-8") as f:
    json.dump(kb, f, ensure_ascii=False, indent=2)

tasks = [entry["task"] for entry in kb]
vectorizer = TfidfVectorizer().fit_transform(tasks)
sims = cosine_similarity(vectorizer)

keep = []
removed = 0
to_skip = set()

for i in range(len(kb)):
    if i in to_skip:
        continue
    keep.append(kb[i])
    for j in range(i+1, len(kb)):
        if sims[i][j] > THRESHOLD:
            to_skip.add(j)
            removed += 1

# 保存去重后的知识库
with open("success_kb.json", "w", encoding="utf-8") as f:
    json.dump(keep, f, ensure_ascii=False, indent=2)

print(f"去重完成：删除了 {removed} 条相似记录，保留 {len(keep)} 条（原 {len(kb)} 条）")
print("原文件备份为 success_kb_backup.json")

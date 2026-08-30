import os
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_FILE = "success_kb.json"

def load_kb_descriptions():
    if not os.path.exists(KB_FILE):
        return []
    with open(KB_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except:
            return []
    return [item.get("task", "") for item in data]

# 我们使用的两个测试描述
desc_a = "写一个Python函数，计算一个整数列表中所有元素的平均值"
desc_b = "写一个Python函数，返回给定数字列表的平均数"

corpus = [desc_a, desc_b]
vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3))
vecs = vectorizer.fit_transform(corpus)
sim = cosine_similarity(vecs[0], vecs[1])[0][0]
print(f"示例描述相似度：{sim:.4f}")

# 检查知识库中最近几条任务
print("\n知识库最近5条任务：")
kb_descs = load_kb_descriptions()
for i, desc in enumerate(kb_descs[-5:], 1):
    print(f"{i}. {desc}")

# 检查种子A是否在知识库中
if desc_a in kb_descs:
    print(f"\n种子A已存在于知识库，位置：{kb_descs.index(desc_a)}")
else:
    print(f"\n种子A不在知识库中。")

print(f"知识库总条数：{len(kb_descs)}")

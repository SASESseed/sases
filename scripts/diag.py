import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from core.services import project_service
from core.db import db_cursor
import numpy as np

q = "三者的命令白名单有哪些？"
qv = np.asarray(project_service._get_embedder().get_embedding(q), dtype=np.float32).flatten()

with db_cursor() as cur:
    cur.execute("SELECT section_path, embedding FROM project_docs WHERE status='active'")
    rows = cur.fetchall()

print(f"总 {len(rows)} 个分片")
scores = []
for r in rows:
    emb = project_service._blob_to_embed(r["embedding"])
    if emb is not None:
        sim = project_service._cosine_sim(qv, emb)
        scores.append((sim, r["section_path"]))

scores.sort(reverse=True)
for s, p in scores:
    print(round(s, 3), p)
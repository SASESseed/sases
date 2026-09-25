# core/services/project_service.py
"""SASES 项目库 - 分片检索"""
import hashlib
import re
import numpy as np
from datetime import datetime
from ..db import db_cursor
from .local_embedding import LocalEmbedding

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = LocalEmbedding()
    return _embedder


RETRIEVE_THRESHOLD = 0.48
MAX_CHUNKS_PER_QUERY = 3
FRESHNESS_NEW_DAYS = 30
FRESHNESS_MID_DAYS = 90


def _compute_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _embed_to_blob(emb):
    return np.asarray(emb, dtype=np.float32).flatten().tobytes()


def _blob_to_embed(blob):
    if not blob:
        return None
    try:
        return np.frombuffer(blob, dtype=np.float32)
    except Exception:
        return None


def _cosine_sim(a, b):
    if a is None or b is None:
        return 0.0
    a = np.asarray(a, dtype=np.float32).flatten()
    b = np.asarray(b, dtype=np.float32).flatten()
    if a.shape != b.shape:
        return 0.0
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _freshness_from_age(days):
    if days <= FRESHNESS_NEW_DAYS:
        return 1.0
    if days <= FRESHNESS_MID_DAYS:
        return 0.7
    return 0.4


def _split_markdown(text):
    """按 ## 二级标题分片，返回 [(section_title, section_path, content), ...]"""
    lines = text.split("\n")
    chunks = []
    current_title = ""
    current_path = ""
    current_lines = []
    parent_title = ""
    
    def flush():
        if current_lines and any(l.strip() for l in current_lines):
            content = "\n".join(current_lines).strip()
            if content:
                chunks.append((current_title, current_path, content))
    
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            flush()
            parent_title = line[2:].strip()
            current_title = ""
            current_path = parent_title
            current_lines = []
        elif line.startswith("## "):
            flush()
            current_title = line[3:].strip()
            current_path = f"{parent_title} > {current_title}" if parent_title else current_title
            current_lines = []
        else:
            current_lines.append(line)
    
    flush()
    return chunks


def import_document(source_file, source_version, raw_text, auto_replace=True, user_id=0):
    """导入一份文档。auto_replace=True 时先删除同 source_file 的旧分片"""
    now = datetime.now().isoformat()
    file_hash = _compute_hash(raw_text)
    
    with db_cursor() as cur:
        cur.execute("SELECT file_hash FROM project_docs_meta WHERE source_file=?", (source_file,))
        row = cur.fetchone()
        if row and row["file_hash"] == file_hash:
            print(f"[project] {source_file} 内容未变，跳过")
            return 0
    
    chunks = _split_markdown(raw_text)
    if not chunks:
        print(f"[project] {source_file} 未分片成功")
        return 0
    
    if auto_replace:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM project_docs WHERE source_file=?", (source_file,))
    
    count = 0
    for idx, (title, path, content) in enumerate(chunks):
        try:
            emb = _get_embedder().get_embedding(content)
            emb_blob = _embed_to_blob(emb)
        except Exception as e:
            print(f"[project] 分片 {idx} embedding 失败: {e}")
            emb_blob = None
        
        content_hash = _compute_hash(content)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO project_docs "
                "(source_file, section_title, section_path, section_level, chunk_index, "
                "content, embedding, content_hash, freshness_score, status, created_at, updated_at, user_id) "
                "VALUES (?, ?, ?, 2, ?, ?, ?, ?, 1.0, 'active', ?, ?, ?)",
                (source_file, title, path, idx, content, emb_blob, content_hash, now, now, user_id)
            )
            count += 1
    
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT OR REPLACE INTO project_docs_meta "
            "(source_file, source_version, chunk_count, file_hash, imported_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (source_file, source_version, count, file_hash, now, now)
        )
    
    print(f"[project] {source_file} 导入 {count} 个分片")
    return count


def retrieve_project_chunks(query, top_k=MAX_CHUNKS_PER_QUERY, threshold=None):
    """检索项目库分片，返回 [{section_path, content, score}, ...]"""
    rows = []
    with db_cursor() as cur:
        cur.execute("SELECT id, source_file, section_path, content, embedding, freshness_score, updated_at FROM project_docs WHERE status='active'")
        for r in cur.fetchall():
            d = dict(r)
            d['_origin'] = 'project'
            rows.append(d)
        cur.execute("SELECT id, task_id, user_input, summary, embedding, created_at FROM execution_notes WHERE status='active'")
        for r in cur.fetchall():
            d = dict(r)
            d['_origin'] = 'execution'
            d['content'] = (d.get('user_input') or '') + ' | ' + (d.get('summary') or '')
            d['section_path'] = '执行记录 ' + (d.get('task_id') or '')
            d['freshness_score'] = 0.8
            rows.append(d)

    if not rows:
        return []

    try:
        query_emb = np.asarray(_get_embedder().get_embedding(query), dtype=np.float32).flatten()
    except Exception as e:
        print(f"[project] 查询 embedding 失败: {e}")
        return []

    scored = []
    for row in rows:
        emb = _blob_to_embed(row.get("embedding"))
        if emb is None:
            continue
        sim = _cosine_sim(query_emb, emb)
        _eff = threshold if threshold is not None else RETRIEVE_THRESHOLD
        if sim < _eff:
            continue
        freshness = row.get("freshness_score") or 1.0
        final_score = sim * 0.7 + freshness * 0.3
        scored.append({
            "source_file": row.get("source_file") or "execution_notes",
            "section_path": row.get("section_path") or row.get("section_title") or "",
            "content": row["content"],
            "similarity": round(sim, 4),
            "freshness": freshness,
            "score": round(final_score, 4)
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def format_chunks_for_prompt(chunks, max_chars_per_chunk=600):
    """把检索到的分片格式化为可注入 prompt 的文本"""
    if not chunks:
        return ""
    lines = ["【项目资料】"]
    for c in chunks:
        title = c.get("section_path") or c.get("source_file")
        content = c["content"]
        if len(content) > max_chars_per_chunk:
            content = content[:max_chars_per_chunk] + "..."
        lines.append(f"\n▸ {title}\n{content}")
    return "\n".join(lines)


def import_execution_note(task_id, user_id, user_input, summary, steps_digest, outcome='success'):
    '把执行记录写入 execution_notes 表'
    if not user_input:
        return 0
    now = datetime.now().isoformat()
    content_for_hash = f'{user_input}|{summary}'
    content_hash = _compute_hash(content_for_hash)

    with db_cursor() as cur:
        cur.execute('SELECT id FROM execution_notes WHERE content_hash=?', (content_hash,))
        if cur.fetchone():
            return 0

    emb_blob = None
    try:
        emb = _get_embedder().get_embedding(user_input + ' ' + (summary or ''))
        emb_blob = _embed_to_blob(emb)
    except Exception as e:
        print(f'[exnote] embedding 失败: {e}')

    with db_cursor(commit=True) as cur:
        cur.execute(
            'INSERT INTO execution_notes (task_id, user_id, user_input, summary, outcome, steps_digest, embedding, content_hash, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (task_id, user_id, user_input, summary, outcome, steps_digest, emb_blob, content_hash, 'active', now)
        )
        print(f'[exnote] 已写入执行笔记 {task_id}')
        return cur.lastrowid



def get_project_stats():
    """返回项目库统计"""
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM project_docs WHERE status='active'")
        total = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(DISTINCT source_file) as cnt FROM project_docs WHERE status='active'")
        files = cur.fetchone()["cnt"]
        cur.execute("SELECT source_file, source_version, chunk_count, imported_at FROM project_docs_meta ORDER BY imported_at DESC")
        metas = [dict(r) for r in cur.fetchall()]
    return {"total_chunks": total, "total_files": files, "files": metas}
    return count
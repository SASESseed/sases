"""SASES 状态文档同步服务
- sync_state_doc: 把 docs/SASES_STATE.md 投喂到项目库（user_id=0）
- periodic_state_sync: 每 24 小时执行一次同步
"""
import asyncio
import os


def sync_state_doc() -> dict:
    fp = 'docs/SASES_STATE.md'
    if not os.path.exists(fp):
        return {'ok': False, 'chunks': 0, 'error': 'file not found'}
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            raw = f.read()
    except Exception as e:
        return {'ok': False, 'chunks': 0, 'error': 'read failed: ' + str(e)}
    if not raw:
        return {'ok': False, 'chunks': 0, 'error': 'empty file'}
    try:
        import sqlite3
        from .. import config
        from . import project_service
        try:
            _conn = sqlite3.connect(config.DB_FILE)
            _cur = _conn.cursor()
            _cur.execute("DELETE FROM project_docs WHERE source_file='SASES_STATE.md'")
            _cur.execute("DELETE FROM project_docs_meta WHERE source_file='SASES_STATE.md'")
            _conn.commit()
            _conn.close()
        except Exception as _e_del:
            print(f"[state] 删除旧分片失败: {_e_del}")
        n = project_service.import_document(
            source_file='SASES_STATE.md',
            source_version='v_auto',
            raw_text=raw,
            auto_replace=True,
            user_id=0,
            allow_system=True,
        )
        return {'ok': True, 'chunks': n, 'error': ''}
    except Exception as e:
        return {'ok': False, 'chunks': 0, 'error': 'import failed: ' + str(e)}


async def periodic_state_sync(interval_hours: int = 24):
    await asyncio.sleep(5 * 60)
    while True:
        try:
            r = await asyncio.to_thread(sync_state_doc)
            if r['ok']:
                print(f"[state] SASES_STATE.md 同步 {r['chunks']} 个分片")
            else:
                print(f"[state] 同步失败: {r['error']}")
        except Exception as e:
            print(f"[state] 周期任务异常: {e}")
        await asyncio.sleep(interval_hours * 3600)

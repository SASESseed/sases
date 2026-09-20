import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import traceback

print('=== 1. 检查 db_cursor 是否在 supervisor_service 里 ===')
try:
    import core.services.supervisor_service as s
    print('hasattr db_cursor:', hasattr(s, 'db_cursor'))
    print('db_cursor:', getattr(s, 'db_cursor', None))
except Exception as e:
    traceback.print_exc()

print('=== 2. 直接跑 build_context ===')
try:
    r = s.build_context(2, 30, '红包')
    print('返回类型:', type(r))
    print('返回长度:', len(r))
    print('返回内容:', repr(r[:300]))
except Exception as e:
    traceback.print_exc()

print('=== 3. 手动跑 build_context 内部 SQL ===')
try:
    from core.db import db_cursor
    with db_cursor() as cur:
        cur.execute('SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 3', (30,))
        rows = cur.fetchall()
    print('rows 长度:', len(rows))
    for row in reversed(rows):
        print('keys:', list(row.keys()))
        print('sender:', row['sender'])
        print('content 前50字:', (row['content'] or '')[:50])
except Exception as e:
    traceback.print_exc()
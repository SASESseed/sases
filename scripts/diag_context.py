import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import db_cursor

with db_cursor() as cur:
    cur.execute('SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 3', (30,))
    rows = cur.fetchall()
    print('长度:', len(rows))
    for r in rows:
        print('row 类型:', type(r))
        try:
            print('  sender:', r['sender'])
            print('  content:', (r['content'] or '')[:50])
        except Exception as e:
            print('  访问失败:', e)
import sqlite3

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

for tool in ['file_patch', 'run_python', 'file_read', 'verify_syntax']:
    print()
    print('=' * 70)
    print(f'{tool} 失败原因细分')
    print('=' * 70)
    cur.execute("""
        SELECT review_reason, COUNT(*) as cnt
        FROM swarm_reviews
        WHERE command=? AND exec_status IN ('failed','blocked')
        GROUP BY review_reason
        ORDER BY cnt DESC
        LIMIT 15
    """, (tool,))
    rows = cur.fetchall()
    if not rows:
        print('  (无失败记录)')
        continue
    for r in rows:
        reason = (r['review_reason'] or '')[:90]
        print(f"  [{r['cnt']:3d}] {reason}")

conn.close()

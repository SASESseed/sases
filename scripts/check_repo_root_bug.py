import sqlite3

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, task_id, command, review_reason, output_preview FROM swarm_reviews WHERE review_reason LIKE '%REPO_ROOT%' LIMIT 10")
rows = cur.fetchall()
print(f'找到 {len(rows)} 条 REPO_ROOT 报错')
for r in rows:
    print('---')
    print('task:', r['task_id'])
    print('cmd :', (r['command'] or '')[:80])
    print('why :', (r['review_reason'] or '')[:200])
    print('out :', (r['output_preview'] or '')[:300])

conn.close()

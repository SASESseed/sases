import sqlite3

conn = sqlite3.connect('users.db')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM swarm_reviews WHERE exec_status IN ('failed','blocked')")
total = cur.fetchone()[0]

cur.execute("SELECT command, COUNT(*) as cnt FROM swarm_reviews WHERE exec_status IN ('failed','blocked') GROUP BY command ORDER BY cnt DESC LIMIT 10")
rows = cur.fetchall()
top10_sum = sum(r[1] for r in rows)

print(f'总失败: {total}')
print(f'TOP 10 覆盖: {top10_sum}')
print(f'覆盖率: {top10_sum/total*100:.1f}%')
print()
print('TOP 10 命令:')
for cmd, cnt in rows:
    print(f'  [{cnt:4d}] {cmd[:60]}')

conn.close()

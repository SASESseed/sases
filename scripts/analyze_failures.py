import sqlite3

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('=' * 70)
print('file_patch 失败原因细分')
print('=' * 70)
cur.execute("""
    SELECT review_reason, COUNT(*) as cnt
    FROM swarm_reviews
    WHERE command='file_patch' AND exec_status IN ('failed','blocked')
    GROUP BY review_reason
    ORDER BY cnt DESC
    LIMIT 15
""")
for r in cur.fetchall():
    reason = (r['review_reason'] or '')[:80]
    print(f"  [{r['cnt']:3d}] {reason}")

print()
print('=' * 70)
print('run_python 失败原因细分')
print('=' * 70)
cur.execute("""
    SELECT review_reason, COUNT(*) as cnt
    FROM swarm_reviews
    WHERE command='run_python' AND exec_status IN ('failed','blocked')
    GROUP BY review_reason
    ORDER BY cnt DESC
    LIMIT 15
""")
for r in cur.fetchall():
    reason = (r['review_reason'] or '')[:80]
    print(f"  [{r['cnt']:3d}] {reason}")

print()
print('=' * 70)
print('file_read 失败原因细分')
print('=' * 70)
cur.execute("""
    SELECT review_reason, COUNT(*) as cnt
    FROM swarm_reviews
    WHERE command='file_read' AND exec_status IN ('failed','blocked')
    GROUP BY review_reason
    ORDER BY cnt DESC
    LIMIT 15
""")
for r in cur.fetchall():
    reason = (r['review_reason'] or '')[:80]
    print(f"  [{r['cnt']:3d}] {reason}")

conn.close()

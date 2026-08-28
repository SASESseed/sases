import sqlite3
import auth

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row

users = conn.execute('SELECT id FROM users').fetchall()

for u in users:
    uid = u['id']
    total = conn.execute('SELECT SUM(amount) FROM credit_ledger WHERE user_id = ?', (uid,)).fetchone()[0] or 0
    conn.execute('UPDATE users SET credits = ? WHERE id = ?', (total, uid))
    sig = auth.sign_state(uid, total)
    conn.execute('UPDATE users SET state_hash = ? WHERE id = ?', (sig, uid))
    print(f'用户 {uid} 积分已恢复为 {total}，签名已更新')

conn.commit()
conn.close()
print('所有用户积分和签名修复完成')

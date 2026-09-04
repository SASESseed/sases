# core/services/transfer_service.py
from datetime import datetime
from ..db import db_cursor


def create_transfer(sender_id: int, receiver_id: int, amount: float, tx_type: str = 'transfer', message: str = ''):
    """创建一条转账或红包记录，状态 pending"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, message)
            VALUES (?, ?, ?, ?, ?)
        """, (sender_id, receiver_id, amount, tx_type, message))
        return cur.lastrowid


def complete_transfer(tx_id: int):
    """完成交易，扣减发送方积分，增加接收方积分，更新状态为 completed"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM transactions WHERE id=? AND status='pending'", (tx_id,))
        tx = cur.fetchone()
        if not tx:
            return False

        # 检查发送方余额
        cur.execute("SELECT credits FROM users WHERE id=?", (tx["sender_id"],))
        sender = cur.fetchone()
        if not sender or sender["credits"] < tx["amount"]:
            return False

        # 执行转账：扣发送方，加接收方
        with db_cursor(commit=True) as cur2:
            cur2.execute("UPDATE users SET credits = credits - ? WHERE id=?", (tx["amount"], tx["sender_id"]))
            cur2.execute("UPDATE users SET credits = credits + ? WHERE id=?", (tx["amount"], tx["receiver_id"]))
            cur2.execute("UPDATE transactions SET status='completed', completed_at=? WHERE id=?", (datetime.now().isoformat(), tx_id))
            # 写入积分历史
            cur2.execute("""
                INSERT INTO contribution_log (user_id, action, event_type, points, detail)
                VALUES (?, '转账支出', 'transfer', ?, ?)
            """, (tx["sender_id"], -tx["amount"], f"向用户{tx['receiver_id']}转账"))
            cur2.execute("""
                INSERT INTO contribution_log (user_id, action, event_type, points, detail)
                VALUES (?, '转账收入', 'transfer', ?, ?)
            """, (tx["receiver_id"], tx["amount"], f"来自用户{tx['sender_id']}的转账"))
        return True


def refund_transfer(tx_id: int):
    """红包过期退回，将金额退回发送方，状态改为 refunded"""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM transactions WHERE id=? AND status='pending'", (tx_id,))
        tx = cur.fetchone()
        if not tx:
            return False
        with db_cursor(commit=True) as cur2:
            cur2.execute("UPDATE users SET credits = credits + ? WHERE id=?", (tx["amount"], tx["sender_id"]))
            cur2.execute("UPDATE transactions SET status='refunded' WHERE id=?", (tx_id,))
            cur2.execute("""
                INSERT INTO contribution_log (user_id, action, event_type, points, detail)
                VALUES (?, '红包退回', 'transfer', ?, ?)
            """, (tx["sender_id"], tx["amount"], f"红包未领取退回"))
        return True


def get_pending_transfers(user_id: int):
    """获取用户待领取的红包"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT t.id, t.sender_id, u.username as sender_name, t.amount, t.message, t.created_at
            FROM transactions t
            JOIN users u ON t.sender_id = u.id
            WHERE t.receiver_id=? AND t.tx_type='red_packet' AND t.status='pending'
        """, (user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_transaction(tx_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM transactions WHERE id=?", (tx_id,))
        row = cur.fetchone()
        return dict(row) if row else None

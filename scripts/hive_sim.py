"""SASES 蜂群积分模拟 - 单机多节点验证

用法:
    python scripts/hive_sim.py --node-id node-A --db D:/sases-hive/node-A.db --port 9001 --peers http://127.0.0.1:9002,http://127.0.0.1:9003
"""
import argparse
import asyncio
import hashlib
import json
import sqlite3
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = "hive.db"
NODE_ID = "node-0"
PEERS = []
ALERT_LOG = "D:/sases-hive/alerts.log"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS accounts (user_id TEXT PRIMARY KEY, username TEXT, credits INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS transfers (id INTEGER PRIMARY KEY AUTOINCREMENT, from_user TEXT, to_user TEXT, amount INTEGER, ts TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS anchors (id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, hash TEXT, ts TEXT DEFAULT CURRENT_TIMESTAMP)")
    for uid, name in [("u1", "alice"), ("u2", "bob"), ("u3", "carol")]:
        c.execute("INSERT OR IGNORE INTO accounts (user_id, username, credits) VALUES (?, ?, ?)", (uid, name, 1000))
    conn.commit()
    conn.close()


def compute_hash():
    conn = get_conn()
    rows = conn.execute("SELECT user_id, credits FROM accounts ORDER BY user_id").fetchall()
    conn.close()
    data = [[r["user_id"], r["credits"]] for r in rows]
    payload = json.dumps(data, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TransferReq(BaseModel):
    from_user: str
    to_user: str
    amount: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    t1 = asyncio.create_task(anchor_loop())
    t2 = asyncio.create_task(sync_loop())
    yield
    t1.cancel()
    t2.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/info")
def info():
    return {"node_id": NODE_ID, "peers": PEERS, "hash": compute_hash()}


@app.get("/balance/{user_id}")
def balance(user_id: str):
    conn = get_conn()
    row = conn.execute("SELECT user_id, username, credits FROM accounts WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return dict(row)


@app.post("/transfer")
def transfer(req: TransferReq):
    conn = get_conn()
    c = conn.cursor()
    sender = c.execute("SELECT credits FROM accounts WHERE user_id=?", (req.from_user,)).fetchone()
    receiver = c.execute("SELECT credits FROM accounts WHERE user_id=?", (req.to_user,)).fetchone()
    if sender is None or receiver is None:
        conn.close()
        raise HTTPException(status_code=404, detail="user not found")
    if sender["credits"] < req.amount:
        conn.close()
        raise HTTPException(status_code=400, detail="insufficient credits")
    c.execute("UPDATE accounts SET credits = credits - ? WHERE user_id=?", (req.amount, req.from_user))
    c.execute("UPDATE accounts SET credits = credits + ? WHERE user_id=?", (req.amount, req.to_user))
    c.execute("INSERT INTO transfers (from_user, to_user, amount) VALUES (?, ?, ?)", (req.from_user, req.to_user, req.amount))
    conn.commit()
    conn.close()
    return {"ok": True, "hash": compute_hash()}


@app.get("/hash")
def get_hash():
    return {"node_id": NODE_ID, "hash": compute_hash()}


@app.get("/anchors")
def get_anchors():
    conn = get_conn()
    rows = conn.execute("SELECT id, node_id, hash, ts FROM anchors ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return {"anchors": [dict(r) for r in rows]}


async def anchor_loop():
    while True:
        try:
            h = compute_hash()
            conn = get_conn()
            conn.execute("INSERT INTO anchors (node_id, hash) VALUES (?, ?)", (NODE_ID, h))
            conn.commit()
            conn.close()
        except Exception as e:
            print("anchor error:", e)
        await asyncio.sleep(30)


async def sync_loop():
    while True:
        await asyncio.sleep(15)
        try:
            local = compute_hash()
            async with httpx.AsyncClient(timeout=3) as client:
                for peer in PEERS:
                    try:
                        resp = await client.get(peer.rstrip("/") + "/hash")
                        remote = resp.json().get("hash")
                        if remote and remote != local:
                            line = "MISMATCH node=%s local=%s peer=%s remote=%s" % (NODE_ID, local, peer, remote)
                            with open(ALERT_LOG, "a", encoding="utf-8") as f:
                                f.write(line + chr(10))
                            print(line)
                    except Exception as e:
                        print("peer error", peer, e)
        except Exception as e:
            print("sync error:", e)


def main():
    global DB_PATH, NODE_ID, PEERS
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-id", default="node-0")
    parser.add_argument("--db", default="hive.db")
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--peers", default="")
    args = parser.parse_args()
    NODE_ID = args.node_id
    DB_PATH = args.db
    PEERS = [p.strip() for p in args.peers.split(",") if p.strip()]
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()

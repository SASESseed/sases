# Hive Credits Experiment Report

> Date: 2026-09-26
> Environment: Single machine (Windows), Python 3.12 + FastAPI + SQLite
> Nodes: 10 (node-A to node-J, ports 9001-9010)

---

## 1. Objective

Validate whether a single machine can simulate a multi-node "hive" and verify these mechanisms:

1. Data isolation (each node has its own database)
2. Hash anchoring (accurately reflects credit state)
3. Tamper detection (any node's change can be detected by others)
4. Alert deduplication (no log explosion)
5. Majority vote consensus (collectively identify abnormal nodes)

---

## 2. Implementation

### 2.1 Core Scripts

- `scripts/hive_sim.py`: single-node service, exposes 5 APIs
- `scripts/hive_batch.py`: batch launcher for N nodes

### 2.2 API List

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/info` | GET | Returns node ID and DB path |
| `/balance/{user_id}` | GET | Query a user's credits |
| `/transfer` | POST | Transfer credits (params: from_user, to_user, amount) |
| `/hash` | GET | Returns SHA256 of full credit state |
| `/anchors` | GET | Latest 20 anchor records |
| `/suspects` | GET | Peers this node considers abnormal |

### 2.3 Database Tables

Each node has an independent DB with 4 tables:

- `accounts`: user_id, username, credits
- `transfers`: transfer records
- `anchors`: hash anchor history
- `suspected_peers`: peers considered abnormal by this node

### 2.4 Background Tasks

- `periodic_anchor(30)`: writes anchor every 30 seconds
- `heartbeat_check(15)`: compares hashes with peers every 15 seconds (with dedup)
- `majority_vote_check(20)`: collects all peer hashes every 20 seconds, uses majority vote to identify anomalies

---

## 3. Experiment Steps and Results

### 3.1 Launch 10 Nodes

```cmd
python scripts/hive_batch.py --count 10 --port-base 9001

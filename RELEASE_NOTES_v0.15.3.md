\# SASES v0.15.3 Release Notes



\*\*Release Date:\*\* 2026-09-17

\*\*Previous Version:\*\* v0.15.2



\## Highlights



The executor is now \*\*integrated into the backend process\*\*. Users no longer need to start `executor\_v2.py` manually. Any conversation in `free` mode triggers automatic execution.



\## Architecture Change



\### Before



&#x20;   Backend (app\_full.py) → creates \[TASK] messages

&#x20;   External script (executor\_v2.py) → user must start manually with conversation\_id



\### After



&#x20;   Backend (app\_full.py)

&#x20;     ├── API routes

&#x20;     ├── Background executor (async task)

&#x20;     │     Scans swarm\_pending\_tasks table every 3 seconds

&#x20;     │     Executes commands or harness tools

&#x20;     │     Reports via swarm\_service.handle\_step\_done

&#x20;     └── Auto-recovers unfinished tasks on restart



\## New Features



\### 1. Task Persistence



New table `swarm\_pending\_tasks` stores all tasks. On backend restart, `restore\_pending\_tasks()` reloads them and continues execution.



\### 2. Global Concurrency Control



`MAX\_CONCURRENT\_TASKS = 3` via asyncio.Semaphore. Multiple conversations can execute in parallel but capped at 3.



\### 3. Auto Agent Matching



`pick\_swarm\_agents(user\_id)` selects commander/executor by:

1\. Name contains "指挥" / "commander" → commander

2\. Name contains "执行" / "executor" → executor

3\. Fallback: first agent = commander, second = executor



\### 4. Any Conversation Support



The background executor scans all conversations. No conversation\_id binding required.



\## Technical Details



\### New Files



| File | Purpose |

|------|---------|

| `core/services/executor\_service.py` | Background executor (250 lines) |

| `swarm\_pending\_tasks` table | Task persistence |



\### Modified Files



| File | Change |

|------|--------|

| `core/db.py` | + swarm\_pending\_tasks table |

| `core/services/swarm\_service.py` | + database sync, + restore\_pending\_tasks |

| `core/bootstrap.py` | + background executor task |



\### Executor Safety



| Check | Rule |

|-------|------|

| Whitelist | 17 read-only commands |

| Dangerous chars | `\& < > ^ % ; \\` $ \\n \\r` |

| Timeout | 30 seconds per command |

| Output limit | 2000 chars |

| Harness support | `type: "harness"` steps |



\## Testing Results



&#x20;   \[MSG\_DEBUG] content='列出 core 目录下的文件' | mode='free'

&#x20;   \[swarm] 检索到 2 条成功经验

&#x20;   \[MSG\_DEBUG] plan\_result={'status': 'planned', ...}

&#x20;   \[executor] ▶ 开始执行任务 t\_1789660577486

&#x20;   \[executor] task=t\_1789660577486 step=1 type=command

&#x20;   \[executor]   结果: success (64ms)

&#x20;   \[swarm] step 1 审核: pass |

&#x20;   \[swarm] 成功记忆已写入

&#x20;   \[executor] ✓ 任务 t\_1789660577486 处理完毕



\## Known Limitations



1\. \*\*Backend crash recovery\*\* — if backend crashes mid-command, task resumes from beginning, may re-execute

2\. \*\*No conversation-level lock yet\*\* — two tasks in same conversation may interleave

3\. \*\*`executor\_v2.py` deprecated\*\* — moved to `tools/executor\_v2\_debug.py`



\## Migration Notes



\- Users no longer need to run `python executor\_v2.py ...`

\- Backend automatically recovers unfinished tasks on restart

\- Any conversation in `free` mode will auto-execute tasks


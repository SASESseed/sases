# SASES 状态快照



> 最后更新：2026-09-26

> 维护方式：三者完成任务后自动追加"最近修复"；你手动整理其他章节



---



## 一、环境



- 虚拟环境：`venv312`

- 启动命令：`python scripts/run_forever.py`

- 端口：`8001`

- 测试账号：

&#x20; - `test / 123456`（管理员，ID=1）

&#x20; - `222222 / 123456`

&#x20; - `666666 / 123456`

- 数据库：`users.db`（SQLite）



---



## 二、已完成能力



- 种子架构闭环（发芽-生长-验证-回溯）

- 三角色体系：调度员 / 指挥官 / 执行员 / 审核员

- 续跑机制（`running_resumed`，重启后跳过 restart_pending 防死循环）

- wrapper 自动重启（端口清理 + 杀进程树）

- 知识库导入权限保护（`allow_system=True` 才能写 user_id=0）

- `execution_notes` 跨用户隔离

- cleanup 扫描器（测试残留检测，白名单跳过自身）

- 权限保护：仅 SASES 助手（`sases_assistant*` / `sases_api_*`）能触发知识库导入

- 执行笔记隔离（`_ISOLATE_EXECUTION_NOTE = True`，不污染个人项目库）



---



## 三、已知问题



- **续跑空转**：`resume` 时 task_summarizer 判断保守，导致已完成的 run 仍做无用探测（烧 4-8 积分，不紧急）

- **`task_summarizer` 假阴性**：日志出现"剩余/请继续"就判 goal_achieved=false，可能误判



---



## 四、待办



- [ ] `project_service.py` 加 `*1/*2/*3` 编号

- [ ] `chat_menu.js` 多选文件 + 粘贴截图

- [ ] `chat_ui.js` 多附件预览（微信样式平齐）

- [ ] `chat.css` 样式微调

- [ ] `docs/SASES_STATE.md` 后台自动同步任务

- [ ] 用户级状态接入 UI 知识库



---



## 五、关键文件路径



| 模块 | 路径 |

|------|------|

| 调度员 | `core/services/supervisor_service.py` |

| 指挥官 + 审核员 | `core/services/swarm_service.py` |

| 执行员 | `core/services/executor_service.py` |

| 消息分流 | `core/services/message_service.py` |

| 项目库 | `core/services/project_service.py` |

| 清理 | `core/services/cleanup_service.py` |

| wrapper | `scripts/run_forever.py` |

| 三角色 prompt | `core/services/swarm_service.py` 顶部 |

| 数据库表定义 | `core/db.py` |

| 路由注册 | `core/bootstrap.py` |

| Harness 工具 | `harness_modules/` |



---



## 六、常用调试命令



```bash

# 启动服务

python scripts/run_forever.py



# 查看积分

python -c "from core.services import credit_service; print(credit_service.get_balance(1))"



# 查看最近 run

python -c "import sqlite3; conn=sqlite3.connect('users.db'); conn.row_factory=sqlite3.Row; cur=conn.cursor(); cur.execute('SELECT id,status,current_round,goal FROM supervisor_runs ORDER BY id DESC LIMIT 5'); [print(dict(r)) for r in cur.fetchall()]"



# 查看测试残留

python -c "from core.services import cleanup_service; r=cleanup_service.scan_test_marks(); print('发现:', r['count'])"



# 手动触发 cleanup

python -c "from core.services import cleanup_service; print(cleanup_service.cleanup_all())"

## 七、最近修复

（下方由 state_service 每 24 小时自动追加）
- 2026-09-26: 给 state_service.py 加"自动追加最近修复"功能，1 处改动。file_patch 后必须紧接 verify_syntax。

在 core/s
- 2026-09-26: 在 core/bootstrap.py 注册 state_service 后台任务，共 2 处改动。每个 file_patch 后必须紧接 verify_syn
- 2026-09-26: 让 docs/SASES_STATE.md 自动同步到项目库，共 2 处改动。每个 file_patch 后必须紧接 verify_syntax。全部改完再触发
- 2026-09-26: 加 *1 统一导入功能（知识库/项目库），1 处改动。file_patch 后必须紧接 verify_syntax。

在 core/services/mess
- 2026-09-26: 让所有用户都有"虚拟 SASES 助手"，1 处改动。file_patch 后必须紧接 verify_syntax。

在 core/services/agen
- 2026-09-26: 修后端 SASES 助手判断，去掉 sases_api_ 前缀，1 处改动。file_patch 后必须紧接 verify_syntax。

在 core/se
- 2026-09-26: 修复用户发图片时被替换成文字描述的问题，1 处改动。file_patch 后必须紧接 verify_syntax。

在 core/services/messa
- 2026-09-26: 实现聊天窗口多附件支持，共 4 处改动。每个 file_patch 后必须紧接 verify_syntax。全部改完再触发 restart_pending。
- 2026-09-26: 给模型配置加能力字段（打地基，不改现有逻辑），共 3 处改动。每个 file_patch 后必须紧接 verify_syntax。全部改完再触发 restart
- 2026-09-26: 补修重拆分支的 supervisor_service 残留，1 处改动。file_patch 后必须紧接 verify_syntax。

在 core/serv
- 2026-09-26: 修复重拆分支 supervisor_service 未定义的 bug，1 处改动。file_patch 后必须紧接 verify_syntax。

在 core
- 2026-09-26: 创建 scripts/hive_batch.py，用 create_if_missing=true。内容如下（原样粘贴，不要改编）：

"""批量启动 hive
- 2026-09-26: 用 overwrite=true 覆盖 scripts/hive_sim.py，1 处改动。这个脚本是"积分节点模拟"不是"蜜蜂模拟"，请严格按给定内容覆盖，不
- 2026-09-26: 创建 scripts/hive_sim.py，用 create_if_missing=true。内容如下（约 100 行）：

蜂群积分模拟脚本，模拟 3 个独
- 2026-09-26: Create docs/HIVE_EXPERIMENT.md with create_if_missing=true. Content as below (pa
- 2026-09-26: 给 hive_sim.py 加多数决机制，共 3 处改动。每个 file_patch 后必须紧接 verify_syntax。

改动 A（core 脚本 sc
- 2026-09-27: 在 D:/sases1/scripts/run_forever.py 里做改动：把 `C = [sys.executable, "-m", "uvicorn",
- 2026-09-27: 改 D:/sases1/scripts/run_forever.py 的端口，1 处改动。file_patch 后必须紧接 verify_syntax。

ol
- 2026-09-27: 用 file_patch 改 **D 盘的绝对路径**文件。file_path 参数必须写完整路径 D:/sases1/scripts/run_forever.
- 2026-09-27: 用 file_patch 改 **D 盘的绝对路径**文件，目标文件：D:/sases1/scripts/run_forever.py

old_snippet
- 2026-09-27: 修 harness_modules/file_read/main.py 的重复代码和嵌套逻辑，2 处改动。每个 file_patch 后必须紧接 verify_
- 2026-09-27: 改 core/services/swarm_service.py 的 COMMANDER_SYSTEM_PROMPT，加跨盘路径规则，1 处改动。file_pa
- 2026-09-27: 从 D:/sases1/scripts/run_forever.py 删除 # cross-drive-test 注释，1 处改动。

old_snippet:
- 2026-09-27: 用 file_patch 改 **D 盘绝对路径**文件，测试跨盘功能。1 处改动。file_patch 后必须紧接 verify_syntax。

目标文件：
- 2026-09-27: 用 file_copy 工具复制文件到两份副本，共 4 次调用。

调用 1：
  module_id: file_copy
  params: {src: "
- 2026-09-27: 用 file_copy 复制 4 个文件，共 4 次调用。

调用 1：src="core/api_routes/hive_routes.py", dst="D
- 2026-09-27: 创建蜂群节点信息 API，共 3 处改动。每个 file_patch 后必须紧接 verify_syntax。全部改完再触发 restart_pending。
- 2026-09-27: 用 file_copy 复制 2 个文件到两份副本，共 4 次调用。

调用 1：src="core/services/group_service.py", d
- 2026-09-27: groups 表加跨实例字段，1 处改动。file_patch 后必须紧接 verify_syntax。

old_snippet:
        cur.e
- 2026-09-27: 用 file_copy 复制 swarm_service.py 到两份副本，共 2 次调用。

调用 1：src="core/services/swarm_se
- 2026-09-27: 改 core/services/swarm_service.py 的 COMMANDER_SYSTEM_PROMPT，加重启说明，1 处改动。

old_sni
- 2026-09-27: 用 file_copy 复制 db.py 到两份副本，共 2 次调用。

调用 1：src="core/db.py", dst="D:/sases1/core/
- 2026-09-27: 给 hive_routes.py 加 /sync/member 和 /sync/message 接收端点，共 2 处改动。每个 file_patch 后必须紧接
- 2026-09-27: 实现群成员和群消息的跨实例同步广播，共 2 处改动。每个 file_patch 后必须紧接 verify_syntax。全部改完再触发 restart_pend
- 2026-09-27: 把蜂群实验扩展到 docs/HIVE_EXPERIMENT.md，加跨实例群聊的成果。1 处改动。file_patch 后必须紧接 verify_syntax。
- 2026-09-27: 用 run_python 执行以下代码：

import sqlite3
L=[]
for n,p in [('A','C:/Users/xiaomai/sas
- 2026-09-27: 用 file_copy 复制 group_service.py 到两份副本，共 2 次调用。

调用 1：src="core/services/group_se
- 2026-09-27: 用 run_python 执行：

import sqlite3
for n, p in [('A','C:/Users/xiaomai/sases/users
- 2026-09-27: 用 file_copy 复制 2 个文件到两份副本，共 4 次调用。

调用 1：src="core/api_routes/hive_routes.py", d
- 2026-09-27: 给 remove_member_from_group 和 leave_group 加广播，共 2 处改动。每个 file_patch 后必须紧接 verify_
- 2026-09-27: 用 run_python 执行以下代码测试 WebSocket 连接：

import asyncio
import websockets

async def
- 2026-09-27: 创建后 verify_syntax 检查 core/api_routes/ws_routes.py。

改动 B：core/bootstrap.py 注册 ws
- 2026-09-27: 加 WebSocket 实时推送基础设施，共 2 处改动。每个 file_patch 后必须紧接 verify_syntax。全部改完再触发 restart_p
- 2026-09-27: 用 file_copy 复制 group_chat.js 到两份副本，共 2 次调用。

调用 1：src="static/modules/group_chat
- 2026-09-27: 用 file_copy 复制 executor_service.py 到两份副本，共 2 次调用。

调用 1：src="core/services/execu
- 2026-09-27: 补做 get_group_info 的 global_group_id 改动，1 处改动。file_patch 后必须紧接 verify_syntax。

ol
- 2026-09-27: 用 file_copy 复制 2 个文件到两份副本，共 4 次调用。

调用 1：src="core/services/executor_service.py"
- 2026-09-27: 用 run_python 执行：

import sqlite3
L = []
for n, p in [('A','C:/Users/xiaomai/sase
- 2026-09-27: 用 file_copy 复制 4 个文件到两份副本，共 8 次调用。

调用 1：src="static/modules/ws_client.js", dst=
- 2026-09-27: 前端挂用户级 WS 实现单聊实时刷新，共 4 处改动。每个 file_patch 后必须紧接 verify_syntax。全部改完再触发 restart_pen
- 2026-09-27: 用 run_python 执行：

import asyncio
import websockets
import httpx
import json

asy
- 2026-09-28: 用 file_copy 复制 ws_routes.py 到两份副本，共 2 次调用。

调用 1：src="core/api_routes/ws_routes.
- 2026-09-28: 修复移除成员只支持用户名的问题，1 处改动。file_patch 后必须紧接 verify_syntax。全部改完再触发 restart_pending。

o
- 2026-09-28: 修复 supervisor_runs 的 interrupted 标记逻辑。要求：
  1. 不再无差别标记所有 running 为 interrupted
 
- 2026-09-28: 把 docs/DEVELOPER_NOTES.md 投喂到项目库，1 处改动。

用 run_python 执行：

from core.services im
- 2026-09-28: 修复 _log_review 函数，支持 step_type 参数。共 3 处改动，全部在 core/services/swarm_service.py。每处 
- 2026-09-28: 给 swarm_service.py 加 steps 格式校验。共 3 处改动。

改动 1：在 _parse_plan 函数之后（约 830 行）加新函数
o
- 2026-09-28: 探测 harness 工具的标准接口。读以下文件，总结接口约定，不要改任何代码：

1. file_read 读 harness_modules/file_re
- 2026-09-28: 修复 scripts/diagnose_libs.py 的预测判断逻辑。共 3 处改动，按顺序执行，每处 file_patch 后必须 verify_synta
- 2026-09-28: 修复单聊附件 UI 问题。共 3 处改动，全部用 file_replace_range，每处后必须 verify_syntax。全部改完再触发 restart_
- 2026-09-29: UI 合规巡检。

第 1 轮：用 file_read 的 grep 模式读 static/css/chat.css 中含"border-radius"和"pa
- 2026-09-29: 定位"当前允许的命令：dir, ls, type, cat, echo, pwd, whoami, hostname"这段提示文字所在的源文件，把它改为引用 e
- 2026-09-29: 把 api_call 的 MAX_BODY 从 20000 改成 15000
- 2026-09-29: 把 api_call 的 TIMEOUT 改成 60
- 2026-09-29: UI 合规巡检（static/css/chat.css）。

第 1 轮：用 read_file 的 grep 模式读出 chat.css 中所有 border
- 2026-09-30: 列出 scripts 目录下的文件名
- 2026-09-30: 统计 core/services 目录下有多少个 .py 文件
- 2026-09-30: 统计 core/services 目录下 .py 文件的数量




\# SASES 架构总览



\## 一、三架构分层

┌────────────────────────────────────────────┐

│ 根脉络架构（Root-Vein） │

│ 多模型协作 · 控制库 · 外部 IO · 设备接口 │

├────────────────────────────────────────────┤

│ 种子架构（Seed） │

│ 发芽 → 生长 → 验证 → 回溯 → 知识库入库 │

├────────────────────────────────────────────┤

│ 阿波罗架构（Apollo） │

│ 天时节律 · 逐日安全 · 除虫 · 挑坏果子 │

└────────────────────────────────────────────┘



text



\## 二、三角色协同

用户输入

↓

意图识别（intent\_service）

↓ is\_task?

调度员（supervisor\_service）

↓ 生成 run

指挥官（swarm/commander.py）→ 拆解为步骤 JSON

↓ 写 pending 表

执行员（executor\_service.py）→ 每 3 秒扫描执行

↓ \[STEP\_DONE]

审核员（swarm/reviewer.py）→ pass / retry

↓

汇总 → 写记忆 → 更新知识库



text



\## 三、核心目录结构

sases/

├── app\_full.py # FastAPI 入口

├── core/

│ ├── bootstrap.py # 应用创建、路由注册、后台任务

│ ├── db.py # 数据库初始化与迁移

│ ├── config.py # 配置加载

│ ├── security.py # JWT/加密/签名

│ ├── auth\_service.py # 用户认证

│ ├── harness\_\*.py # Harness 工具运行时

│ ├── services/ # 业务逻辑层

│ │ ├── swarm/ # 指挥官 + 审核员（已拆分）

│ │ ├── supervisor/ # 调度员（已拆分）

│ │ ├── message/ # 消息处理（已拆分）

│ │ ├── group\_service.py # 群聊核心

│ │ ├── group\_task\_service.py # 群任务

│ │ ├── group\_red\_packet\_service.py # 群红包

│ │ ├── airdrop\_service.py # 空投

│ │ ├── credit\_service.py # 积分

│ │ ├── memory\_service.py # 记忆库

│ │ └── ... # 其他业务

│ └── api\_routes/ # HTTP 路由层（39 个文件，190 接口）

├── harness\_modules/ # Harness 工具实现

├── static/

│ ├── index.html # 单页应用入口

│ ├── css/ # 拆分后的样式

│ └── modules/ # 前端 JS 模块

├── scripts/ # 运维/诊断脚本

├── docs/ # 架构/API/数据库文档

├── tests/ # 测试

└── users.db # SQLite 主库



text



\## 四、数据库分层



| 层 | 表 | 说明 |

|----|----|----|

| \*\*用户层\*\* | users, api\_keys, model\_configs | 账户与配置 |

| \*\*会话层\*\* | conversations, messages | 单聊 |

| \*\*群聊层\*\* | groups, group\_members, group\_messages | 群基础 |

| \*\*群业务层\*\* | group\_tasks, group\_red\_packets, group\_stakes, group\_airdrop\_log | 蜂群模式 |

| \*\*知识层\*\* | knowledge\_base, project\_docs, execution\_notes, safety\_memory, interaction\_patterns | 认知资产 |

| \*\*调度层\*\* | swarm\_pending\_tasks, swarm\_reviews, supervisor\_runs | 三者执行 |

| \*\*工作层\*\* | work\_logs, quality\_issues, rescue\_tasks | 指令模式 |

| \*\*游戏层\*\* | pets, base\_facilities, game\_resources, yunchong\_tasks | 云宠战役 |

| \*\*交易层\*\* | transactions, credit\_pool, contribution\_log | 积分经济 |



\## 五、关键数据流



\### 5.1 任务执行流

用户 → /messages/send → intent\_service 判 is\_task

→ 是 → swarm.plan\_task → LLM 拆解 → pending 表

→ executor 扫描 → 执行 harness → \[STEP\_DONE]

→ reviewer 审核 → pass / retry

→ 全 pass → 写记忆 → 写知识库 → 汇总返回



text



\### 5.2 群任务流

群成员 → /group/{id}/tasks/publish → 扣质押 + 插 \[TASK\_CARD] 消息

→ 群成员提交 → /group/tasks/{id}/submit

→ 发布者选择 → /group/tasks/{id}/select

→ 95% 给提交者 + 5% 进群池



text



\### 5.3 群红包流

用户 → /group/{id}/red-packets/create

→ 扣个人积分（或群池）→ 插 \[RED\_PACKET] 消息

→ 群成员抢 → claim\_packet → 二倍均值法随机分配

→ 24h 过期 → expire\_packets → 退款



text



\## 六、后台定时任务



| 任务 | 频率 | 说明 |

|------|------|------|

| periodic\_summary\_task | 6 小时 | 总结工作日志 |

| periodic\_git\_push | 1 小时 | 推送代码 |

| periodic\_pattern\_finalize | 1 小时 | 经验固化 |

| periodic\_syntax\_check | 1 分钟 | 语法扫描 |

| periodic\_rescue\_maintenance | 5 分钟 | 超时任务回收 |

| periodic\_airdrop | 每天 0:30 | 空投 |

| periodic\_group\_red\_packet | 1 分钟 | 群福利定时发 |

| periodic\_red\_packet\_expire | 1 小时 | 红包过期退款 |

| periodic\_cleanup | 24 小时 | 数据清理 |

| periodic\_state\_sync | 24 小时 | 状态快照 |



\## 七、文档索引



| 文档 | 说明 |

|------|------|

| `docs/ARCHITECTURE.md` | 本文件 |

| `docs/DATABASE.md` | 数据库表结构（脚本生成） |

| `docs/API\_INDEX.md` | API 接口清单（脚本生成） |

| `docs/EXECUTION\_HEALTH.md` | 执行质量诊断（脚本生成） |

| `docs/DEVELOPER\_NOTES.md` | 开发者操作手册 |

| `docs/SASES\_STATE.md` | 系统状态快照 |



\## 八、文档维护



| 场景 | 动作 |

|------|------|

| 加新表 | 跑 `python scripts/gen\_db\_doc.py` |

| 加新接口 | 跑 `python scripts/gen\_api\_doc.py` |

| 每次功能上线 | 跑 `python scripts/gen\_health\_doc.py` |

| 重大架构变更 | 手动更新本文件 |


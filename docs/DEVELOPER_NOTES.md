# SASES 开发者笔记



> 最后更新：2026-09-28

> 用途：多实例协作经验、指令模板、bug 规避

> 每次新会话先读此文，避免重复踩坑



\---



## 一、角色分工铁律



| 任务类型 | 执行者 | 说明 |

|---------|-------|------|

| 读代码 | 你手动 | AI 只告诉读哪一行 |

| 单步改动 | 三者 | 1 个 file\_patch |

| 多步改动 | 调度员 | 2-5 个 file\_patch |

| 跨副本复制 | 调度员（file\_copy） | 用工具，不用手敲 |

| 重启服务 | 你手动 | 改 core/ 后 Ctrl+C 重启 |

| 长文档/整文件写 | 你手动 | 调度员会丢内容 |



核心：AI 设计 → 你决策 → 三者/调度员执行 → 你验证。



\---



## 二、指令模板



### T1：改一行/加一个函数（给三者）



调用 harness 工具（type=harness, module\_id=file\_patch），参数如下：



params：

&#x20; file\_path: "<文件路径>"

&#x20; old\_snippet: "<原片段>"

&#x20; new\_snippet: "<新片段>"

&#x20; expected\_count: 1



执行完直接结束，不要生成 findstr 验证命令。



### T2：多处改动（给调度员）



#4: <一句话目标>，共 N 处改动。每个 file\_patch 后必须紧接 verify\_syntax。全部改完再触发 restart\_pending。



改动 A：<文件>

old\_snippet: ...

new\_snippet: ...

expected\_count: 1

然后 verify\_syntax。



改动 B：...

（同上）



约束：N 处按顺序执行，全部改完再触发 restart\_pending。



### T3：跨副本复制（给调度员）



#4: 用 file\_copy 复制文件到两份副本，共 N 次调用。



调用 1：src="<相对路径>", dst="D:/sases1/<相对路径>", overwrite=true

调用 2：src="<相对路径>", dst="D:/sases2/<相对路径>", overwrite=true



### T4：执行 Python（给三者）



调用 harness 工具（type=harness, module\_id=run\_python），参数如下：



params：

&#x20; code: "<Python 代码>"



执行完直接结束。



### T5：读文件（给三者）



调用 harness 工具（type=harness, module\_id=file\_read），参数如下：



params：

&#x20; file\_path: "<文件>"

&#x20; max\_lines: 200



执行完直接结束。



\---



## 三、分批改动的铁律



每次改动最多 2-3 处，超过容易：

\- 调度员重拆跑偏

\- 一次崩多处，难以定位

\- 反复重试烧积分



正确节奏：

1\. 改 1-2 处 → 重启 → 验证

2\. 复制到副本 → 重启副本 → 验证

3\. 再做下一批



\---



## 四、常见 bug 与规避



| Bug | 原因 | 规避 |

|-----|------|------|

| 重复插入 | 重拆时同段代码被加两次 | 改前 file\_read 确认现状 |

| 锚点不唯一 | old\_snippet 太短 | 用更长片段（含前后行） |

| 验证器不支持 D 盘 | 忘了改 verify\_syntax | 每次加新工具都同步改 |

| 副本不同步 | 忘复制 | 改完 core/ 立即 file\_copy |

| 未定义变量 | 分支作用域 | 函数头统一初始化 |

| 调度员跑偏 | prompt 规则不清 | 加"D 盘路径原样传"规则 |

| 重启不触发 | 重拆提前 return | 分支前写 review |



\---



## 五、调度员/三者的能力边界



### 能做好的



\- 读文件、定位片段

\- 精确 file\_patch（1-3 处）

\- file\_copy 跨盘复制

\- run\_python 执行脚本

\- 加新函数、新端点

\- 改 SQL、加字段



### 做不好的



\- 长文档一次性写（>200 行）→ 丢内容

\- "重写整个文件" → 只写一部分

\- 模糊指令（如"优化一下"）→ 探测死循环

\- 多文件交叉引用 → 容易漏改

\- 改 file\_patch 自己 → 被自保护

\- 改 users.db 等敏感文件 → 被禁



\---



## 六、文件复制验证模板



改完 core/ 文件后，验证是否同步：



python -c "import hashlib; files=\['<路径1>','<路径2>']; \[print(f, '主:', hashlib.md5(open('C:/Users/xiaomai/sases/'+f,'rb').read()).hexdigest()\[:8], '副1:', hashlib.md5(open('D:/sases1/'+f,'rb').read()).hexdigest()\[:8], '副2:', hashlib.md5(open('D:/sases2/'+f,'rb').read()).hexdigest()\[:8]) for f in files]"



每行 3 个 hash 相同 = 同步成功。



\---



## 七、服务重启检查清单



改 core/ 后：

1\. 主 SASES：自动触发 restart\_pending

2\. 副本 1：手动 Ctrl+C → 重启

3\. 副本 2：手动 Ctrl+C → 重启



### 重启命令模板



主 SASES（8001）：



&#x20;   cd C:\\Users\\xiaomai\\sases

&#x20;   venv312\\Scripts\\activate

&#x20;   set SASES\_PORT=8001

&#x20;   set SASES\_HIVE\_NODE\_ID=node-A

&#x20;   set SASES\_HIVE\_PEERS=http://127.0.0.1:8002,http://127.0.0.1:8003

&#x20;   set SASES\_HIVE\_MODE=alert

&#x20;   python scripts/run\_forever.py



副本 1（8002）：



&#x20;   cd D:\\sases1

&#x20;   C:\\Users\\xiaomai\\sases\\venv312\\Scripts\\activate

&#x20;   set SASES\_PORT=8002

&#x20;   set SASES\_HIVE\_NODE\_ID=node-B

&#x20;   set SASES\_HIVE\_PEERS=http://127.0.0.1:8001,http://127.0.0.1:8003

&#x20;   set SASES\_HIVE\_MODE=alert

&#x20;   python scripts/run\_forever.py



副本 2（8003）：



&#x20;   cd D:\\sases2

&#x20;   C:\\Users\\xiaomai\\sases\\venv312\\Scripts\\activate

&#x20;   set SASES\_PORT=8003

&#x20;   set SASES\_HIVE\_NODE\_ID=node-C

&#x20;   set SASES\_HIVE\_PEERS=http://127.0.0.1:8001,http://127.0.0.1:8002

&#x20;   set SASES\_HIVE\_MODE=alert

&#x20;   python scripts/run\_forever.py



\---



## 八、跨实例调试检查表



| 检查项 | 命令 |

|--------|------|

| 三实例在线 | python -c "import httpx; \[print(p, httpx.get(f'http://127.0.0.1:{p}/hive/info', timeout=3).json()\['node\_id']) for p in (8001,8002,8003)]" |

| 群数据一致 | 查三实例 groups 表 |

| 成员一致 | 查三实例 group\_members 表 |

| 消息一致 | 查三实例 group\_messages 表 |

| WS 端点可用 | python test\_ws5.py |

| Hive 端点可用 | curl http://127.0.0.1:8002/hive/info |



\---



## 九、当前可用 Harness 工具



| 工具 | 用途 |

|------|------|

| file\_patch | 改文件（支持 C/D 盘） |

| file\_read | 读文件（支持 C/D 盘） |

| file\_copy | 复制文件（跨盘） |

| verify\_syntax | 语法检查（支持 C/D 盘） |

| run\_python | 执行 Python（限 5 目录） |

| grep\_code | 搜索关键词 |

| dir\_tree | 列目录 |

| api\_call | HTTP 调用（禁内网） |

| web\_fetch | 抓网页 |

| harness\_reload | 重载工具 |

| git\_ops | git 操作 |



\---



## 十、元建议



1\. 每次改动只做一件事：改完验证，再做下一件

2\. 每个批次结束后 copy 到副本：避免"主改副本没改"

3\. 硬刷新浏览器（Ctrl+Shift+R）—— 经常是缓存问题

4\. 调度员说"已完成"也要验证：它常误判

5\. 长文档不要给调度员：你手动粘贴

6\. 所有改动都要 MD5 对比确认：不要"相信"日志



\---



## 十一、当前未完成 / 待办



### P0（稳定当前系统）

\- 好友通讯（A↔B 用户级推送）

\- 会话列表未读红点实时刷新

\- 新消息 Toast 通知



### P1（微信细节）

\- 消息状态（已读回执）

\- 引用、@提及

\- 撤回、转发



### P2（系统完善）

\- Hive 广播可靠性（失败重试）

\- 断线重连（WS 自动恢复）



### P3（长期）

\- 群公告、群文件

\- 语音/视频

\- 端到端加密


# SASES 项目概览

本文档为 SASES 项目的核心索引，供智能体检索使用。

## 一、项目定位

> 版本: v0.17.0 · 最后更新: 2026-09-19


SASES 是一个本地优先、隐私优先的自进化 AI 生态。后端 FastAPI + SQLite，前端原生 ES Modules，微信风格单页界面。核心特色是三角色（指挥官、执行员、审核员）自动化执行，加上种子架构、安全架构、根脉络架构三套认知系统。

## 二、三角色架构

### 指挥官（Commander）
职责：读会话历史 + 记忆 + 项目库，把用户任务拆解为命令序列。文件位置 core/services/swarm_service.py 的 plan_task 函数。调用 DeepSeek API，输出 JSON 数组格式的步骤列表。支持两种步骤类型：命令行（command 字段）和 Harness 工具（type=harness + module_id + params）。

### 执行员（Executor）
命令白名单 17 条：dir / ls / tree / type / cat / head / tail / findstr / find / grep / where / echo / pwd / cd / whoami / hostname / wc。危险字符 10 个：& < > ^ % ; ` $ 换行。管道符 | 允许但会拆分逐段检查。超时 30 秒，输出上限 2000 字符，UTF-8 smart_decode。步骤类型有两种：command（命令行）和 harness（type=harness + module_id + params）。

### 审核员（Reviewer）
职责：逐步判定 pass 或 retry，触发重拆。位于 core/services/swarm_service.py 的 review_step 函数。错误关键字 13 个，应有输出命令 8 个，不可恢复关键字 5 个。重拆上限 2 次。

## 三、三套认知系统

### 种子架构
认知核心，负责发芽（生成分支）、生长（综合方案）、验证、回溯、学习。当前以知识库 success_kb.json 为基础，自动迭代。

### 安全架构（原阿波罗）
负责内容安全扫描、风险分级、除虫机制、挑坏果子反馈。当前已实现基础安全扫描和命令白名单。

## 四、核心数据表

### 用户与认证
users 表：id、username、password_hash、sases_id、credits、gender、region、signature、onboarding_day、onboarding_completed。

### 消息与会话
conversations 表：id、user_id、agent_id、title、mode、unread_count、is_pinned、updated_at。messages 表：id、conversation_id、sender、content、sender_agent_id、created_at。

### 模型与智能体
model_configs 表：id、user_id、model_type、name、provider、api_key_encrypted、node_url、model_name、capabilities、is_shared、visibility、price。

### 知识库与记忆
knowledge_base 表：id、task、branch_a、branch_b、solution、verified、contributor_id、hit_count、quality_score。safety_memory 表：id、memory_type、content、user_id、group_id、importance、tags、task_id、embedding、content_hash。

### 三角色相关
swarm_pending_tasks 表：task_id、conversation_id、user_id、steps、results、done_steps、retry_count、is_draft、cancelled、no_plan、status。swarm_reviews 表：task_id、step_id、command、exec_status、review_result、review_reason、output_preview。intent_feedback 表：user_id、task_id、original_input、feedback_type。

### 经验库（v0.17.0）
interaction_patterns 表：id、domain、pattern_key、pattern_type、context_signature、role、evidence、confidence、hit_count、success_count、fail_count、status、source_task_id。domains 表：domain、pattern_count、active、activated_at。

### 项目库（v0.17.0）
project_docs 表：id、source_file、section_title、section_path、section_level、chunk_index、content、embedding、content_hash、freshness_score、status。project_docs_meta 表：source_file、source_version、chunk_count、file_hash、imported_at。

## 五、主要 API 路由

### 认证
POST /token 登录。POST /auth/register 注册。GET /auth/me 获取当前用户。

### 消息
GET /messages/conversations 会话列表。GET /messages/conversations/{id}/messages 拉取消息。POST /messages/send 发送消息，自动触发意图识别与 swarm 分流。

### 三角色
POST /swarm/plan 拆解任务。POST /swarm/confirm 确认草稿。POST /swarm/reject 拒绝草稿。POST /swarm/cancel 取消任务。POST /swarm/feedback 误判反馈。GET /swarm/reviews 查询审核日志。

### Harness
POST /harness/execute 调用工具。GET /harness/modules 列出模块。

### 记忆
POST /memory/remember 写入。POST /memory/recall 检索。GET /memory/type/{type} 按类型获取。DELETE /memory/{id} 删除。

### 其他
GET /user/profile 用户资料。GET /credits/balance 积分余额。GET /stats/leaderboard 排行榜。


## 六、Harness 工具清单

### 内置工具
web_fetch：抓取网页文本。限制：仅公网 HTTP(S)，禁内网 IP，10 秒超时，100 KB 上限，输出截断 2000 字。

calculator：四则运算。

unit_converter：单位换算。

text_stats：文本统计。

json_formatter：JSON 格式化。

base64_codec：Base64 编解码。

string_utils：字符串工具。

file_patch：修改项目文件。允许目录 static/ / core/ / scripts/ / docs/。支持三种模式：精确片段替换（old_snippet + new_snippet + expected_count）、锚点定位（anchor_pattern + position + new_content）、创建/覆写文件（create_if_missing=true + new_content）。禁止修改 users.db / .env / *.key / *.bin / file_patch 自身 / executor_service.py。每次写入自动备份到 .backups/。

### file_patch 使用要点
锚点必须唯一匹配一行。若匹配多行会报错并给出所有匹配行号，需要换更精确的锚点。修改 core/ 下的文件后用户需要重启服务才能生效。

## 七、常用调试命令

启动服务：python -m uvicorn app_full:app --reload --port 8001

初始化数据库：python core/db.py

查看经验库统计：python -c "from core.services import pattern_service; print(pattern_service.get_stats())"

查看项目库统计：python -c "from core.services import project_service; print(project_service.get_project_stats())"

投喂项目文档：python scripts/import_project_docs.py docs/xxx.md v0.17.0

查 swarm 任务：SELECT * FROM swarm_pending_tasks ORDER BY created_at DESC LIMIT 5

查 pattern：SELECT domain, pattern_key, confidence, hit_count, status FROM interaction_patterns ORDER BY hit_count DESC LIMIT 10

## 八、常见故障排查

服务起不来：看终端最后的 Traceback，通常是语法错误。用 .backups/ 下的备份还原，或 git checkout。

命令被拦截：检查是否在白名单内（dir / ls / tree / type / cat / head / tail / findstr / find / grep / where / echo / pwd / cd / whoami / hostname / wc），是否含危险字符（& < > ^ % ; ` $ 换行）。

Harness 工具拒绝执行：检查 manifest.json 的 permissions 是否合法。目前只允许 restricted_file_write。

锚点匹配多行：换更长的锚点。例如 "MODEL_NAME = os.environ.get(" 会匹配 VISION_MODEL_NAME，改用 "VISION_MODEL_NAME = os.environ.get("。

project_docs 检索不到：确认 domains 表有对应领域，且 project_docs 表 status='active'。




### 根脉络架构
多模型协作与 IO 核心，负责模型路由、Harness 运行时、工具调用。当前实现 Harness 模块动态加载与执行。
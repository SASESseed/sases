"""预置工具手册到 knowledge_docs（scope='manual'）"""
import sqlite3

MANUALS = [
    {
        "title": "file_patch 用法",
        "category": "tool",
        "tags": "file_patch,改文件,锚点",
        "content": "【用途】精确改文件\n【参数】\n- file_path: 文件路径（相对项目根）\n- 三选一模式：\n  · old_snippet + new_snippet + expected_count（片段替换）\n  · anchor_pattern + position + new_content（锚点插入，position=before/after/replace_line）\n  · create_if_missing + new_content（新建文件）\n【坑】\n- 锚点必须唯一，否则报'匹配到 N 行'\n- 锚点不要用正则符号 ^ $ \\d \\s\n- Windows 换行 \\r\\n 会影响多行锚点匹配，优先用单行锚点"
    },
    {
        "title": "file_read 用法",
        "category": "tool",
        "tags": "file_read,读文件",
        "content": "【用途】读文件\n【参数】\n- file_path: 文件路径\n- offset: 起始行（可选）\n- max_lines: 读多少行（可选）\n- lines: 指定行号列表（可选）\n- grep: 搜索关键词（可选）\n【坑】\n- 读大文件用 offset + max_lines 分段读\n- 用 lines 参数读特定行比 offset 更精确"
    },
    {
        "title": "run_python 用法",
        "category": "tool",
        "tags": "run_python,执行代码",
        "content": "【用途】受限 Python 执行\n【可用函数】read_file(path) / write_file(path, content) / list_dir(path)\n【限制】\n- 禁止 import os/sys/subprocess/socket/ctypes/multiprocessing/signal\n- 禁止 exec/eval\n- 代码长度 ≤ 50000\n- 超时 120 秒\n【常见用途】\n- 批量改文件\n- 数据统计\n- 复杂的字符串替换（避免 CMD 转义问题）"
    },
    {
        "title": "grep_code 用法",
        "category": "tool",
        "tags": "grep_code,搜索",
        "content": "【用途】代码搜索\n【参数】\n- pattern: 必填，搜索词\n- path: 目录或文件\n- file_ext: 文件扩展名过滤\n- max_results: 最大结果数\n【坑】\n- 参数名是 pattern，不是 keyword/query"
    },
    {
        "title": "dir_tree 用法",
        "category": "tool",
        "tags": "dir_tree,列目录",
        "content": "【用途】列目录树\n【参数】\n- path: 目录\n- max_depth: 深度限制\n【用途】当不知道文件路径时，先 dir_tree 看结构"
    },
    {
        "title": "verify_syntax 用法",
        "category": "tool",
        "tags": "verify_syntax,语法检查",
        "content": "【用途】检查 .py/.js 语法 + 未定义调用\n【参数】\n- file_path: 必填\n- auto_rollback: true 时，语法错自动从备份恢复\n- check_undefined: true 时检测未定义调用\n【关键】\n每次 file_patch 改 .py/.js 后，必须跑一次 verify_syntax(auto_rollback=true)"
    },
    {
        "title": "api_call 用法",
        "category": "tool",
        "tags": "api_call,HTTP",
        "content": "【用途】HTTP 请求\n【参数】url / method / headers / body\n【限制】\n- 禁止内网 IP（127.0.0.1 / 192.168 / 10.x）\n- 超时 60 秒\n- body ≤ 20000"
    },
    {
        "title": "web_fetch 用法",
        "category": "tool",
        "tags": "web_fetch,抓网页",
        "content": "【用途】抓网页文本\n【参数】url\n【限制】\n- 禁止内网 IP\n- 超时 30 秒\n- 响应 ≤ 100KB\n- 输出 ≤ 2000 字\n- 只支持 http/https"
    },
    {
        "title": "git_ops 用法",
        "category": "tool",
        "tags": "git_ops,git",
        "content": "【用途】git 操作\n【action 选项】\n- status / diff / log\n- add / commit（message 必填）\n- push / pull\n- rollback（steps=N）\n- snapshot（快速提交快照）\n【坑】\n- commit 时如果工作区干净会失败，先 status 确认"
    },
    {
        "title": "锚点选择技巧",
        "category": "trick",
        "tags": "锚点,file_patch",
        "content": "【锚点必须唯一】\n- 短锚点容易匹配多行，报错\n- 长锚点含换行在 Windows 上匹配不稳\n【推荐做法】\n1. 先用 file_read 看上下文\n2. 选一段\"首行到末行都独特\"的 3-5 行\n3. 或用单行锚点（position=before/after）\n4. 单行锚点要在文件里只出现一次"
    },
    {
        "title": "换行符问题",
        "category": "trick",
        "tags": "换行,Windows,CRLF",
        "content": "【问题】Windows 文件是 \\r\\n，Linux 是 \\n\n【影响】多行锚点在 file_patch 里匹配可能失败\n【解决】\n- 尽量用单行锚点\n- 或先用 run_python 做字符串替换\n- 避免在 old_snippet 里包含 \\n 作为分隔"
    },
    {
        "title": "空行处理",
        "category": "trick",
        "tags": "空行,锚点",
        "content": "【问题】锚点包含连续空行时匹配困难\n【原因】\\n\\n\\n 在不同系统下表现不一致\n【解决】\n- 用单行锚点 + position 插入\n- 例如在函数定义前插入：anchor='async function foo() {'  position='before'"
    },
    {
        "title": "参数名字写对",
        "category": "trick",
        "tags": "参数,调试",
        "content": "【常见错误】\n- grep_code 用 keyword → 错，应该用 pattern\n- file_patch 用 content → 错，应该用 new_content 或 new_snippet\n- api_call 用 data → 错，应该用 body\n【习惯】不确定参数名时先 file_read harness_modules/<工具>/manifest.json"
    },
    {
        "title": "禁止修改受保护文件",
        "category": "trick",
        "tags": "安全,保护",
        "content": "【受保护】\n- file_patch 自身（harness_modules/file_patch/main.py）\n- executor_service.py\n- users.db / .env / *.key / *.bin\n【原因】安全设计，防止三者改自己规则\n【解决】需人工改"
    },
    {
        "title": "restart_pending 信号",
        "category": "trick",
        "tags": "restart,重启",
        "content": "【何时需要重启】\n- 改了 core/ 下的 .py 文件 → 需要重启服务\n- 改了 static/ 下的 .js/.html/.css → 前端刷新即可\n【如何触发】\n三者改完 core/ 后写 restart_signal.txt\n【注意】不要手动删除 restart_signal.txt 前让服务先读取"
    },
]

conn = sqlite3.connect('users.db')
cur = conn.cursor()

inserted = 0
for m in MANUALS:
    # 去重：同 title 跳过
    cur.execute("SELECT id FROM knowledge_docs WHERE scope='manual' AND title=?", (m['title'],))
    if cur.fetchone():
        continue
    cur.execute(
        "INSERT INTO knowledge_docs (scope, group_id, title, content, category, tags, source_type, visibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('manual', None, m['title'], m['content'], m['category'], m['tags'], 'preset', 'system')
    )
    inserted += 1

conn.commit()
conn.close()
print(f'inserted {inserted} manuals, total {len(MANUALS)}')
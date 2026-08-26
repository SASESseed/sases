import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import deque, defaultdict

# ========== 安全执行模块 ==========
def safe_run_tests(code, test_cases, timeout=5):
    if not test_cases:
        return False, "无测试用例", False
    if not is_python_code(code):
        return False, "非代码答案", False

    code = re.sub(r"if __name__\s*==\s*['\"]__main__['\"]:\s*\n.*", "", code, flags=re.DOTALL)
    code = re.sub(r"\n\s*\w+\(\)", "", code)

    func_match = re.search(r"def (\w+)", code)
    if not func_match:
        return False, "无函数定义", False
    func_name = func_match.group(1)
    code_renamed = re.sub(r'def\s+' + func_name + r'\b', 'def __test_func__', code, count=1)

    for case in test_cases:
        inp = case.get("input", [])
        expected = case.get("expected_output")
        expected_repr = repr(expected)

        full_test = f"""
{code_renamed}
import json, sys, inspect
try:
    func = __test_func__
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if isinstance({json.dumps(inp)}, list):
        if len(params) == 1:
            result = func({json.dumps(inp)})
        elif len(params) == len({json.dumps(inp)}):
            result = func(*{json.dumps(inp)})
        else:
            result = func({json.dumps(inp)})
    else:
        result = func({json.dumps(inp)})
    passed = (result == {expected_repr})
    print(json.dumps({{"passed": passed, "output": str(result)}}))
except Exception as e:
    print(json.dumps({{"passed": False, "error": str(e)}}))
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(full_test)
            tmp_path = f.name
        try:
            proc = subprocess.run(["python", tmp_path], capture_output=True, text=True, timeout=timeout)
            if proc.returncode != 0:
                return False, f"执行出错: {proc.stderr.strip()}", False
            result = json.loads(proc.stdout.strip())
            if not result.get("passed", False):
                return False, f"测试失败: {result}", False
        except subprocess.TimeoutExpired:
            return False, "执行超时", False
        finally:
            os.unlink(tmp_path)
    return True, "全部测试通过", True

# ========== 配置 ==========
client = openai.OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/v1",
    timeout=40,
    max_retries=3
)
MODEL = "deepseek-v4-flash"
KB_FILE = "success_kb.json"
TARGET_SUCCESS = 600
SEEDS_PER_ROUND = 10
SIMILARITY_THRESHOLD = 0.85

# ========== 领域库 ==========
DOMAIN_KEYWORDS = {
    "算法与数据结构": ["排序", "搜索", "图", "树", "动态规划", "递归", "链表", "栈", "队列", "哈希"],
    "数据处理与分析": ["JSON", "CSV", "清洗", "解析", "转换", "过滤", "聚合", "统计"],
    "人工智能/机器学习": ["分类", "预测", "回归", "聚类", "神经网络", "推荐"],
    "网络安全/代码审查": ["注入", "验证", "SQL", "XSS", "加密", "防火墙", "权限"],
    "系统设计与工具": ["缓存", "日志", "配置", "调度", "监控", "文件系统"],
    "自动化脚本": ["批量", "重命名", "定时", "文件操作", "备份", "同步"],
    "自然语言处理": ["分词", "关键词", "摘要", "情感", "文本相似", "TF-IDF"],
    "金融": ["利率", "贷款", "股票", "保险", "汇率", "投资", "复利"],
    "医疗健康": ["诊断", "药物", "BMI", "剂量", "疫苗", "病历"],
    "教育学习": ["成绩", "考试", "题库", "GPA", "课程表", "排名", "学习路径"],
    "艺术设计": ["色彩", "排版", "画布", "滤镜", "音乐", "和弦", "绘画"],
    "游戏开发": ["碰撞检测", "AI", "寻路", "技能冷却", "积分板", "排行榜"],
    "日常工具": ["计算器", "倒计时", "闹钟", "单位换算", "邮政编码", "日历"],
    "办公效率": ["邮件合并", "表格处理", "PPT生成", "文档格式", "会议安排"],
    "物流运输": ["路径规划", "装箱", "调度", "运费", "仓储"],
    "航空航天": ["轨道", "火箭", "卫星", "燃料", "太空"],
    "农业": ["灌溉", "施肥", "病虫害", "产量预测", "温室"],
    "能源": ["电力", "石油", "太阳能", "风能", "储能", "电网"],
    "法律": ["合同", "法条", "判例", "知识产权", "版权"],
    "通信": ["5G", "信号", "频谱", "路由", "协议"],
    "制造": ["加工", "装配", "质检", "模具", "数控", "3D打印"],
    "环境科学": ["污染", "监测", "排放", "回收", "生态"],
    "心理学": ["情绪", "行为", "问卷", "量表"],
}

def guess_single_domain(description):
    desc_lower = description.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return domain
    return "综合/跨领域"

def parse_domains(task):
    raw_domain = task.get("domain")
    if raw_domain is None:
        return [guess_single_domain(task["description"])]
    if isinstance(raw_domain, list):
        return list(set(raw_domain)) or [guess_single_domain(task["description"])]
    if isinstance(raw_domain, str):
        parts = re.split(r'[,;，；]\s*', raw_domain)
        if len(parts) > 1:
            return list(set(parts))
        return [raw_domain]
    return [guess_single_domain(task["description"])]

# ========== 知识库管理 ==========
def load_kb():
    if not os.path.exists(KB_FILE):
        return []
    with open(KB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_kb(entries):
    with open(KB_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

knowledge_base = load_kb()

def add_to_kb(task, branch_a, branch_b, synthesis, model_id=MODEL, user_id="system", backtrack_count=0):
    knowledge_base.append({
        "task": task,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "solution": synthesis,
        "verified": True,
        "id": str(uuid.uuid4()),
        "model_id": model_id,
        "user_id": user_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "backtrack_count": backtrack_count
    })
    save_kb(knowledge_base)

# ========== 工具函数 ==========
def is_python_code(text):
    return bool(re.search(r'\bdef\s+\w+\s*\(', text)) or bool(re.search(r'\bclass\s+\w+', text))

def clean_code(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split('\n')
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text

def check_syntax(code):
    if not is_python_code(code):
        return True, ""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, str(e)

def parse_two_branches(text):
    a, b = "", ""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if "思路A" in line or "思路 A" in line:
            if ":" in line:
                a = line.split(":", 1)[1].strip()
            else:
                for j in range(i+1, len(lines)):
                    if "思路B" in lines[j] or "思路 B" in lines[j]:
                        break
                    if lines[j].strip():
                        a += lines[j].strip() + " "
                a = a.strip()
        if "思路B" in line or "思路 B" in line:
            if ":" in line:
                b = line.split(":", 1)[1].strip()
            else:
                for j in range(i+1, len(lines)):
                    if lines[j].strip():
                        b += lines[j].strip() + " "
                b = b.strip()
    return (a or "默认算法A"), (b or "默认算法B")

def load_tasks(path):
    tasks = []
    if not os.path.exists(path):
        return tasks
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                task = json.loads(line)
                if "description" in task and task.get("test_cases"):
                    tasks.append(task)
            except:
                pass
    return tasks

def balance_tasks_by_difficulty(tasks):
    """将任务列表按难度分组并交错排列，让 easy/medium/hard 均匀分布"""
    buckets = defaultdict(list)
    for t in tasks:
        diff = t.get("difficulty", "medium").lower()
        if diff not in ("easy", "medium", "hard"):
            diff = "medium"
        buckets[diff].append(t)
    # 随机打乱每组内部，避免顺序偏差
    for diff in buckets:
        random.shuffle(buckets[diff])
    # 交错取出：每次从拥有最多剩余任务的组取一个，保证均匀
    result = []
    while any(buckets.values()):
        # 选择当前剩余数量最多的组
        next_diff = max(buckets, key=lambda k: len(buckets[k]))
        result.append(buckets[next_diff].pop())
        if not buckets[next_diff]:
            del buckets[next_diff]
    return result

def retrieve_similar(desc, top_k=2):
    if not knowledge_base:
        return []
    tasks = [entry["task"] for entry in knowledge_base]
    vectorizer = TfidfVectorizer().fit(tasks + [desc])
    task_vectors = vectorizer.transform(tasks)
    query_vector = vectorizer.transform([desc])
    sims = cosine_similarity(query_vector, task_vectors).flatten()
    top_indices = sims.argsort()[-top_k:][::-1]
    examples = []
    for idx in top_indices:
        if sims[idx] > 0:
            examples.append({
                "task": knowledge_base[idx]["task"],
                "solution": knowledge_base[idx]["solution"]
            })
    return examples

# ========== 全局去重与领域轮转 ==========
def load_all_seed_descriptions():
    descriptions = set()
    for fname in ["seed_tasks.jsonl", "seed_tasks_new.jsonl"]:
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if "description" in data:
                            descriptions.add(data["description"])
                    except:
                        pass
    for entry in knowledge_base:
        descriptions.add(entry["task"])
    return list(descriptions)

existing_descriptions = load_all_seed_descriptions()

def is_duplicate(new_desc, existing_descs, threshold=SIMILARITY_THRESHOLD):
    if not existing_descs:
        return False
    vectorizer = TfidfVectorizer().fit(existing_descs + [new_desc])
    existing_vecs = vectorizer.transform(existing_descs)
    new_vec = vectorizer.transform([new_desc])
    sims = cosine_similarity(new_vec, existing_vecs).flatten()
    return any(s > threshold for s in sims)

recent_constrained_domain_sets = deque(maxlen=7)

def is_domain_allowed(domains):
    if len(domains) >= 3:
        return True
    domain_set = frozenset(domains)
    for past_set in recent_constrained_domain_sets:
        if not domain_set.isdisjoint(past_set):
            return False
    return True

def update_domain_queue(domains):
    if len(domains) <= 2:
        recent_constrained_domain_sets.append(frozenset(domains))

# ========== 种子生成 ==========
def generate_single_seed(existing_descs):
    example = {
        "description": "如何判断一个信用卡号是否有效（Luhn算法）？",
        "difficulty": "easy",
        "domain": ["金融", "算法"],
        "test_cases": [
            {"input": "4532015112830366", "expected_output": True},
            {"input": "6011514433546201", "expected_output": False}
        ]
    }
    prompt = f"""生成一个编程任务，任务描述必须是**自然语言提问**，不能使用任何人称，不能出现“编写一个Python函数”等机械开头，也不能使用角色扮演。描述应该像现实世界中一个人向同伴求助的编程问题。

示例：
{json.dumps(example, ensure_ascii=False)}

要求：
- 任务背景可以涉及任何领域或生活场景。
- domain 是一个字符串数组，表示涉及的一个或多个领域。
- test_cases 至少包含2个用例，input 和 expected_output 使用纯Python字面量。
- 只输出JSON对象，不要其他文字。"""
    for _ in range(8):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"user","content":prompt}],
                temperature=1.0,
                max_tokens=1000
            )
            raw = resp.choices[0].message.content.strip()
            task = None
            try:
                task = json.loads(raw)
            except:
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    try:
                        task = json.loads(match.group())
                    except:
                        pass
            if task and "description" in task and task.get("test_cases"):
                desc = task["description"]
                if any(word in desc for word in ["你", "我", "他", "编写一个"]):
                    continue
                if is_duplicate(desc, existing_descs):
                    continue
                domains = parse_domains(task)
                task["domain"] = domains
                if not is_domain_allowed(domains):
                    continue
                return task
        except Exception as e:
            print(f"  种子请求异常: {e}")
            time.sleep(2)
    return None

def generate_new_seeds(num=10):
    global existing_descriptions
    seeds = []
    for i in range(num):
        seed = generate_single_seed(existing_descriptions)
        if seed:
            seeds.append(seed)
            domains = seed.get("domain", ["综合"])
            update_domain_queue(domains)
            domain_str = "+".join(domains) if len(domains) > 1 else domains[0]
            print(f"  [{len(seeds)}] {seed['description'][:70]}... (领域: {domain_str})")
            existing_descriptions.append(seed["description"])
        else:
            print(f"  第{i+1}个种子生成失败（已重试多次），等待后继续...")
            time.sleep(5)
        time.sleep(0.5)
    return seeds

# ========== 主循环 ==========
print("正在生成首批自然语言种子（难度均衡 + 领域轮转 + 去重）...")
new_seeds = generate_new_seeds(SEEDS_PER_ROUND)
if not new_seeds:
    print("首批种子生成失败，程序退出。请检查API密钥和网络。")
    exit()
with open("seed_tasks_new.jsonl", "w", encoding="utf-8") as f:
    for s in new_seeds:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")
seed_file = "seed_tasks_new.jsonl"

round_num = 1
while len(knowledge_base) < TARGET_SUCCESS:
    tasks = load_tasks(seed_file)
    if not tasks:
        print("无有效种子，重新生成...")
        new_seeds = generate_new_seeds(SEEDS_PER_ROUND)
        if new_seeds:
            with open("seed_tasks_new.jsonl", "w", encoding="utf-8") as f:
                for s in new_seeds:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
            seed_file = "seed_tasks_new.jsonl"
            continue
        else:
            print("连续生成失败，可能API限制，暂停5分钟后重试...")
            time.sleep(300)
            new_seeds = generate_new_seeds(SEEDS_PER_ROUND)
            if not new_seeds:
                print("最终失败，退出。")
                break
            else:
                with open("seed_tasks_new.jsonl", "w", encoding="utf-8") as f:
                    for s in new_seeds:
                        f.write(json.dumps(s, ensure_ascii=False) + "\n")
                seed_file = "seed_tasks_new.jsonl"
                continue

    # 难度均衡处理
    tasks = balance_tasks_by_difficulty(tasks)
    print(f"\n第 {round_num} 轮，成功总数：{len(knowledge_base)}，目标：{TARGET_SUCCESS}，有效种子数：{len(tasks)}（难度已均衡）")
    for i, task in enumerate(tasks):
        if len(knowledge_base) >= TARGET_SUCCESS:
            break
        desc = task["description"]
        diff = task.get("difficulty", "medium")
        print(f"\n[{i+1}/{len(tasks)}] [{diff}] {desc}")

        similar = retrieve_similar(desc)
        few_shot = ""
        if similar:
            few_shot = "\n".join([f"参考：{s['task']}\n{s['solution'][:200]}..." for s in similar])

        try:
            branch_prompt = f"任务：{desc}\n{few_shot}\n请提出两种截然不同的思路，用`思路A：`和`思路B：`标明。"
            resp = client.chat.completions.create(model=MODEL, messages=[{"role":"user", "content": branch_prompt}])
            branch_a, branch_b = parse_two_branches(resp.choices[0].message.content)

            synthesis = ""
            syntax_error = ""
            for attempt in range(2):
                gen_prompt = f"任务：{desc}\n思路A：{branch_a}\n思路B：{branch_b}\n请**只输出纯Python函数定义**，不要包含函数调用或`if __name__ == '__main__'`。"
                if attempt == 1 and syntax_error:
                    gen_prompt = f"之前代码有语法错误：{syntax_error}\n请修正并重新输出纯函数。"
                resp = client.chat.completions.create(model=MODEL, messages=[{"role":"user", "content": gen_prompt}])
                synthesis = clean_code(resp.choices[0].message.content)
                ok, err = check_syntax(synthesis)
                if ok:
                    break
                syntax_error = err
            else:
                print("  申诉失败，跳过。")
                continue

            passed, msg, _ = safe_run_tests(synthesis, task["test_cases"])
            if passed:
                print("  ✓ 通过，入库。")
                backtrack_count = 0
                add_to_kb(desc, branch_a, branch_b, synthesis, model_id=MODEL, user_id="system", backtrack_count=backtrack_count)
            else:
                print(f"  ✗ 失败：{msg}")
        except Exception as e:
            print(f"  处理异常：{e}")
            continue

        time.sleep(0.3)

    print("\n生成新种子...")
    new_seeds = generate_new_seeds(SEEDS_PER_ROUND)
    if new_seeds:
        with open("seed_tasks_new.jsonl", "w", encoding="utf-8") as f:
            for s in new_seeds:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        seed_file = "seed_tasks_new.jsonl"
        print(f"已生成 {len(new_seeds)} 个新种子。")
    else:
        print("种子生成失败，但将尝试下一轮...")

    round_num += 1

print(f"\n🎉 达成目标！最终成功记录数：{len(knowledge_base)}")

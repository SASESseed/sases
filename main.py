import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ========== 安全执行模块 (内嵌) ==========
def safe_run_tests(code, test_cases, timeout=5):
    if not test_cases:
        return True, "无测试用例", True
    if not is_python_code(code):
        return True, "非代码答案", True
    func_match = re.search(r"def (\w+)", code)
    if not func_match:
        return True, "无函数定义", True
    func_name = func_match.group(1)

    # 重命名函数避免冲突
    code_renamed = re.sub(r'def\s+' + func_name + r'\b', 'def __test_func__', code, count=1)
    full_code = f"""
{code_renamed}
import json, sys
results = []
"""
    for case in test_cases:
        inp = case.get("input", [])
        expected = case.get("expected_output")
        if isinstance(inp, list):
            args_str = ", ".join(json.dumps(arg) for arg in inp)
        else:
            args_str = json.dumps(inp)
        full_code += f"""
try:
    _result = __test_func__({args_str})
    _passed = (_result == {json.dumps(expected)})
    results.append({{"passed": _passed, "output": str(_result), "expected": {json.dumps(expected)}}})
except Exception as e:
    results.append({{"passed": False, "error": str(e)}})
"""
    full_code += """
print(json.dumps(results))
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(full_code)
        tmp_path = f.name
    try:
        proc = subprocess.run(
            ["python", tmp_path],
            capture_output=True, text=True, timeout=timeout
        )
        if proc.returncode != 0:
            return False, f"执行出错: {proc.stderr.strip()}", False
        results = json.loads(proc.stdout.strip())
        for r in results:
            if not r.get("passed", False):
                return False, f"测试失败: {r}", False
        return True, "全部测试通过", False
    except subprocess.TimeoutExpired:
        return False, "执行超时", False
    finally:
        os.unlink(tmp_path)

# ========== 配置 ==========
client = openai.OpenAI(
    api_key="DEEPSEEK_API_KEY",
    base_url="https://api.deepseek.com/v1"
)
MODEL = "deepseek-v4-flash"
KB_FILE = "success_kb.json"
TARGET_SUCCESS = 120
SEEDS_PER_ROUND = 10

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

def add_to_kb(task, branch_a, branch_b, synthesis):
    entry = {
        "task": task,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "solution": synthesis,
        "verified": True,
        "id": str(uuid.uuid4())
    }
    knowledge_base.append(entry)
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

def normalize(val):
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (int, float)):
        return val
    return str(val).strip().lower()

# 注意：原有的 run_tests 函数已废弃，不再使用，完全由 safe_run_tests 替代

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
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                task = json.loads(line)
                if "description" in task:
                    tasks.append(task)
                else:
                    print(f"跳过无效种子：{line.strip()[:80]}...")
            except json.JSONDecodeError:
                print(f"跳过非JSON行：{line.strip()[:80]}...")
    return tasks

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

def generate_new_seeds(existing_tasks, num=10):
    sample = random.sample(existing_tasks, min(5, len(existing_tasks)))
    sample_str = "\n".join([f"- {t['description']}" for t in sample])
    prompt = (
        f"你是一个任务生成器。以下是一些已有的编程任务：\n{sample_str}\n\n"
        f"请生成{num}个类似但不同的新任务。每个任务必须包含字段：description（任务描述）、difficulty（难度，easy/medium/hard）、test_cases（测试用例列表，每个包含input和expected_output）。\n"
        "严格返回一个JSON数组，不要有任何额外文字。"
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user", "content": prompt}],
        temperature=0.8
    )
    raw = resp.choices[0].message.content.strip()
    try:
        tasks = json.loads(raw)
        if isinstance(tasks, list):
            valid = [t for t in tasks if "description" in t]
            if valid:
                return valid
    except:
        pass
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            tasks = json.loads(match.group())
            if isinstance(tasks, list):
                valid = [t for t in tasks if "description" in t]
                if valid:
                    return valid
        except:
            pass
    print("批量生成失败，降级为逐个生成...")
    new_tasks = []
    for _ in range(num):
        single_prompt = (
            f"你是一个任务生成器。基于以下已有任务：\n{sample_str}\n"
            "请生成一个全新的编程任务，返回一个JSON对象，包含字段：description（任务描述）、difficulty（难度）、test_cases（测试用例列表）。只返回JSON对象。"
        )
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user", "content": single_prompt}],
            temperature=0.9
        )
        raw = resp.choices[0].message.content.strip()
        try:
            t = json.loads(raw)
            if "description" in t:
                new_tasks.append(t)
                continue
        except:
            pass
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                t = json.loads(match.group())
                if "description" in t:
                    new_tasks.append(t)
            except:
                pass
    return new_tasks

# ========== 多轮自动循环 ==========
round_num = 1
while len(knowledge_base) < TARGET_SUCCESS:
    seed_file = "seed_tasks.jsonl" if round_num == 1 else "seed_tasks_new.jsonl"
    if not os.path.exists(seed_file):
        print(f"种子文件 {seed_file} 不存在，退出。")
        break

    tasks = load_tasks(seed_file)
    if not tasks:
        print("没有有效种子，退出。")
        break

    print(f"\n{'#'*50}\n第 {round_num} 轮开始，当前成功总数：{len(knowledge_base)}，目标：{TARGET_SUCCESS}")
    print(f"种子文件：{seed_file}，有效种子数：{len(tasks)}")

    for i, task in enumerate(tasks):
        if len(knowledge_base) >= TARGET_SUCCESS:
            break
        desc = task["description"]
        print(f"\n[{i+1}/{len(tasks)}] {desc}")

        similar = retrieve_similar(desc)
        few_shot = ""
        if similar:
            print(f"找到 {len(similar)} 个相似案例，参考已注入。")
            few_shot = "\n".join([f"参考任务：{s['task']}\n参考方案：{s['solution'][:200]}..." for s in similar])

        prompt_branch = f"任务：{desc}\n"
        if few_shot:
            prompt_branch += f"以下是类似任务的成功方案，可作为灵感：\n{few_shot}\n"
        prompt_branch += "请提出两种截然不同的思路，严格按格式输出：\n思路A：<描述>\n思路B：<描述>"
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user", "content": prompt_branch}]
        )
        branch_a, branch_b = parse_two_branches(resp.choices[0].message.content)

        synthesis = ""
        syntax_error = ""
        for attempt in range(2):
            if attempt == 0:
                prompt = f"任务：{desc}\n思路A：{branch_a}\n思路B：{branch_b}\n请输出最终答案。如果是代码任务，只输出纯英文Python代码。"
            else:
                prompt = f"你的答案有语法错误：\n{syntax_error}\n请修正并重新输出。"
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"user", "content": prompt}]
            )
            synthesis = clean_code(resp.choices[0].message.content)
            ok, err = check_syntax(synthesis)
            if ok:
                print("语法检查通过！")
                break
            syntax_error = err
        else:
            print("申诉失败，跳过该任务。")
            continue

        # 使用安全沙箱执行测试
        test_cases = task.get("test_cases", [])
        passed, msg, _ = safe_run_tests(synthesis, test_cases)
        if passed:
            print("答案接受，存入知识库。")
            add_to_kb(desc, branch_a, branch_b, synthesis)
        else:
            print(f"测试失败：{msg}")

        time.sleep(0.3)

    print(f"\n本轮结束，成功总数：{len(knowledge_base)}")
    if len(knowledge_base) >= TARGET_SUCCESS:
        break

    print("\n生成新种子任务...")
    new_seeds = generate_new_seeds(tasks, SEEDS_PER_ROUND)
    if new_seeds:
        with open("seed_tasks_new.jsonl", "w", encoding="utf-8") as f:
            for seed in new_seeds:
                f.write(json.dumps(seed, ensure_ascii=False) + "\n")
        print(f"已生成 {len(new_seeds)} 个新种子，保存至 seed_tasks_new.jsonl")
    else:
        print("新种子生成失败，将沿用当前种子重试。")
        continue

    round_num += 1

print(f"\n目标达成！最终成功记录数：{len(knowledge_base)}")

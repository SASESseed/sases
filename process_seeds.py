import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

# ========== 配置 ==========
client = openai.OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/v1",
    timeout=40,
    max_retries=3
)
MODEL = "deepseek-v4-flash"
KB_FILE = "success_kb.json"
SEED_FILE = "seed_tasks_new.jsonl"

# ========== 知识库 ==========
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
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
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

# ========== 处理单个种子 ==========
def process_seed(task):
    desc = task["description"]
    test_cases = task.get("test_cases", [])
    print(f"\n处理种子: {desc}")

    # 发芽
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user", "content": f"任务：{desc}\n请提出两种截然不同的思路，用`思路A：`和`思路B：`标明。"}]
    )
    branch_a, branch_b = parse_two_branches(resp.choices[0].message.content)

    # 生长 + 申诉
    synthesis = ""
    syntax_error = ""
    for attempt in range(2):
        if attempt == 0:
            prompt = f"任务：{desc}\n思路A：{branch_a}\n思路B：{branch_b}\n请**只输出纯Python函数定义**，不要包含函数调用或`if __name__ == '__main__'`。"
        else:
            prompt = f"之前代码有语法错误：{syntax_error}\n请修正并重新输出纯函数。"
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user", "content": prompt}]
        )
        synthesis = clean_code(resp.choices[0].message.content)
        ok, err = check_syntax(synthesis)
        if ok:
            break
        syntax_error = err
    else:
        print("  申诉失败，跳过。")
        return False

    passed, msg, _ = safe_run_tests(synthesis, test_cases)
    if passed:
        print("  ✓ 通过，入库。")
        add_to_kb(desc, branch_a, branch_b, synthesis)
        return True
    else:
        print(f"  ✗ 失败：{msg}")
        return False

# ========== 主流程 ==========
def main():
    if not os.path.exists(SEED_FILE):
        print(f"种子文件 {SEED_FILE} 不存在。")
        return

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    if not tasks:
        print("种子池为空，无任务可处理。")
        return

    success = 0
    for i, task in enumerate(tasks):
        print(f"\n[{i+1}/{len(tasks)}]")
        if process_seed(task):
            success += 1
        time.sleep(0.3)

    print(f"\n处理完成：成功 {success}/{len(tasks)}")

if __name__ == "__main__":
    main()

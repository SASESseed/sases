import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

import auth  # 新增：用于发放积分

# ========== 配置 ==========
client = openai.OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/v1",
    timeout=120,
    max_retries=2
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

def add_to_kb(task, branch_a, branch_b, synthesis, model_id=MODEL, user_id="system", backtrack_count=0, test_cases=None):
    entry = {
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
    }
    if test_cases is not None:
        entry["test_cases"] = test_cases
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

# ========== API 调用重试包装 ==========
def call_chat(prompt, max_retries=2, temperature=0.7):
    """调用 DeepSeek API，带重试"""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"user", "content":prompt}],
                temperature=temperature
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_error = e
            print(f"  API调用失败（尝试 {attempt+1}/{max_retries+1}）：{e}")
            if attempt < max_retries:
                time.sleep(5)
    raise last_error

# ========== 处理单个种子 ==========
def process_seed(task):
    desc = task["description"]
    test_cases = task.get("test_cases", [])
    seed_user_id = task.get("user_id", "system")
    print(f"\n处理种子: {desc} (提交者ID: {seed_user_id})")

    try:
        # 发芽
        branches_text = call_chat(
            f"任务：{desc}\n请提出两种截然不同的思路，用`思路A：`和`思路B：`标明。",
            temperature=0.7
        )
        branch_a, branch_b = parse_two_branches(branches_text)

        # 生长 + 申诉
        synthesis = ""
        syntax_error = ""
        for attempt in range(2):
            if attempt == 0:
                prompt = f"任务：{desc}\n思路A：{branch_a}\n思路B：{branch_b}\n请**只输出纯Python函数定义**，不要包含函数调用或`if __name__ == '__main__'`。"
            else:
                prompt = f"之前代码有语法错误：{syntax_error}\n请修正并重新输出纯函数。"
            synthesis = clean_code(call_chat(prompt, temperature=0.2))
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
            add_to_kb(desc, branch_a, branch_b, synthesis, model_id=MODEL, user_id=seed_user_id, test_cases=test_cases)

            # 发放积分：仅对真实用户，且不是 system
            if seed_user_id != "system":
                try:
                    uid = int(seed_user_id)
                    auth.add_credits(uid, 5, "外部种子被采纳")
                    auth.add_system_message(
                        uid,
                        f"感谢你的贡献！你提交的种子已成功处理并加入知识库，获得 5 积分。任务：{desc[:100]}...",
                        "SASES助手"
                    )
                    print(f"  已为用户 {uid} 发放 5 积分。")
                except Exception as e:
                    print(f"  发放积分失败: {e}")

            return True
        else:
            print(f"  ✗ 失败：{msg}")
            return False
    except Exception as e:
        print(f"  处理异常：{e}")
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

    # 处理完成后清空种子池，防止下次重复处理
    with open(SEED_FILE, "w", encoding="utf-8") as f:
        pass
    print(f"种子池 {SEED_FILE} 已清空，避免重复处理。")

if __name__ == "__main__":
    main()

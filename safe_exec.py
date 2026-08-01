import subprocess, tempfile, os, json, re

def safe_run_tests(code, test_cases, timeout=5):
    # 提取函数名
    func_match = re.search(r"def (\w+)", code)
    if not func_match:
        return True, "无函数定义", True  # 非代码任务直接通过

    func_name = func_match.group(1)

    # 构建在子进程中运行的完整代码
    # 将用户代码中的函数改名为 __test_func__ 避免冲突
    code_renamed = re.sub(r'def\s+' + func_name + r'\b', 'def __test_func__', code, count=1)
    
    full_code = f"""
{code_renamed}
import json, sys
results = []
"""
    for case in test_cases:
        inp = case.get("input", [])
        expected = case.get("expected_output")
        # 将输入参数格式化为 Python 字面量
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
    # 写入临时文件
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

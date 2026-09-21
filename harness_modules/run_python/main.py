import ast
import subprocess
import tempfile
import os
import sys

MAX_CODE_LEN = 3000
TIMEOUT = 5

FORBIDDEN_MODULES = {'subprocess', 'shutil', 'socket', 'requests', 'urllib', 'ftplib', 'smtplib', 'pickle', 'ctypes'}
FORBIDDEN_NAMES = {'exec', 'eval', 'compile', '__import__', 'open', 'input', 'globals', 'locals', 'vars'}
FORBIDDEN_OS_ATTRS = {'system', 'remove', 'rmdir', 'rename', 'unlink', 'popen', 'spawn', 'execv', 'execve', 'kill', 'chmod', 'chown'}


def _check_ast(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return 'syntax error: ' + str(e)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name.split('.')[0] in FORBIDDEN_MODULES:
                    return 'forbidden import: ' + n.name
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] in FORBIDDEN_MODULES:
                return 'forbidden from: ' + node.module
        if isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                return 'forbidden name: ' + node.id
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute):
                if isinstance(f.value, ast.Name) and f.value.id == 'os' and f.attr in FORBIDDEN_OS_ATTRS:
                    return 'forbidden os.' + f.attr
    return None


def run(params):
    code = params.get('code', '')
    if not code:
        return {'success': False, 'error': 'missing code'}
    if len(code) > MAX_CODE_LEN:
        return {'success': False, 'error': 'code too long (max ' + str(MAX_CODE_LEN) + ')'}
    err = _check_ast(code)
    if err:
        return {'success': False, 'error': err}
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            tmp = f.name
        r = subprocess.run([sys.executable, tmp], capture_output=True, text=True, timeout=TIMEOUT)
        return {
            'success': r.returncode == 0,
            'stdout': (r.stdout or '')[:3000],
            'stderr': (r.stderr or '')[:1000],
            'returncode': r.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'timeout (' + str(TIMEOUT) + 's)'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass
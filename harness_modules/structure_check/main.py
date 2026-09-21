import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)


def _safe_path(p):
    if not p:
        return None
    p = p.replace(BACKSLASH, '/').strip()
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        return None
    if '..' in p.split('/'):
        return None
    return p


def run(params):
    file_path = params.get('file_path', '')
    safe = _safe_path(file_path)
    if not safe:
        return {'success': False, 'error': 'file_path 不合法'}
    abs_path = os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_path):
        return {'success': False, 'error': '文件不存在: ' + safe}
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return {'success': False, 'error': str(e)}

    func_defs = []
    warnings = []
    for i, line in enumerate(lines):
        m = re.match(r'^(\s*)def\s+(\w+)\s*\(', line)
        if not m:
            m = re.match(r'^(\s*)class\s+(\w+)\s*[:(]', line)
            if m:
                func_defs.append({'kind': 'class', 'name': m.group(2), 'line': i+1, 'indent': len(m.group(1))})
            continue
        func_defs.append({'kind': 'def', 'name': m.group(2), 'line': i+1, 'indent': len(m.group(1))})

    seen = {}
    for d in func_defs:
        key = d['name']
        if key in seen:
            warnings.append('同名定义: ' + key + ' 第 ' + str(seen[key]) + ' 行与 ' + str(d['line']) + ' 行')
        else:
            seen[key] = d['line']

    for idx in range(len(func_defs) - 1):
        cur = func_defs[idx]
        nxt = func_defs[idx+1]
        if cur['indent'] == nxt['indent'] and nxt['line'] - cur['line'] <= 2:
            warnings.append('函数截断: ' + cur['name'] + ' 第 ' + str(cur['line']) + ' 行')

    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if (s.startswith(chr(39)*3) or s.startswith(chr(34)*3) or s.startswith(chr(39)) or s.startswith(chr(34))) and '=' not in s:
            warnings.append('疑似孤立字符串: 第 ' + str(i+1) + ' 行: ' + s[:60])

    return {
        'success': True,
        'file_path': safe,
        'total_lines': len(lines),
        'function_count': len(func_defs),
        'functions': func_defs,
        'warnings': warnings,
        'warning_count': len(warnings)
    }

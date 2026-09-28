import sys
sys.path.insert(0, '.')


def _precheck_steps(steps):
    warnings = []
    for s in steps:
        mid = s.get('module_id', '')
        p = s.get('params', {}) or {}
        n = s.get('step', '?')
        if mid == 'file_patch':
            fp = p.get('file_path', '')
            if not p.get('anchor_pattern') and not p.get('old_snippet') and not p.get('new_content'):
                warnings.append(f'step {n}: file_patch 缺参数')
            pos = p.get('position')
            if pos and pos not in ('before', 'after', 'replace_line'):
                warnings.append(f'step {n}: position 非法 {pos}')
            if 'file_patch/main.py' in fp or 'executor_service.py' in fp:
                warnings.append(f'step {n}: 受保护文件')
        if mid == 'file_read':
            fp = p.get('file_path', '')
            if '{{step' in fp or '{step' in fp:
                warnings.append(f'step {n}: 占位符未替换')
        if mid == 'run_python':
            code = p.get('code', '')
            for b in ('import os', 'import sys', 'import subprocess', 'import pathlib'):
                if b in code:
                    warnings.append(f'step {n}: 含 {b}')
                    break
    return warnings


tests = [
    ({'step': 1, 'module_id': 'file_patch', 'params': {'file_path': 'core/config.py'}}, '缺参数'),
    ({'step': 2, 'module_id': 'file_patch', 'params': {'file_path': 'core/x.py', 'anchor_pattern': 'abc', 'position': 'replace'}}, 'position非法'),
    ({'step': 3, 'module_id': 'file_patch', 'params': {'file_path': 'harness_modules/file_patch/main.py', 'anchor_pattern': 'abc'}}, '受保护'),
    ({'step': 4, 'module_id': 'file_read', 'params': {'file_path': '{{step1}}'}}, '占位符'),
    ({'step': 5, 'module_id': 'run_python', 'params': {'code': 'import os'}}, 'forbidden'),
    ({'step': 6, 'module_id': 'file_read', 'params': {'file_path': 'core/config.py'}}, '正常'),
]

for i, (s, d) in enumerate(tests, 1):
    r = _precheck_steps([s])
    ok = bool(r) if i < 6 else not r
    print('OK' if ok else 'FAIL', i, d, r)

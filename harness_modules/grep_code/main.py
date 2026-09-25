import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)
SKIP_DIRS = ('venv312', 'venv', 'node_modules', '.git', '__pycache__', '.backups', 'archive', 'training_data', 'seeds')
SKIP_EXT = ('.pyc', '.zip', '.safetensors', '.onnx', '.db', '.bin', '.key', '.png', '.jpg', '.ico')


def _iter_files(root, rel_base, file_ext):
    _full_base = os.path.join(root, rel_base)
    if os.path.isfile(_full_base):
        _ext = os.path.splitext(_full_base)[1].lower()
        if _ext not in SKIP_EXT and (not file_ext or _ext == file_ext):
            yield _full_base, rel_base
        return
    for dirpath, dirnames, filenames in os.walk(_full_base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXT:
                continue
            if file_ext and ext != file_ext:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(BACKSLASH, '/')
            yield full, rel


def run(params):
    pattern = params.get('pattern', '').strip()
    if not pattern:
        return {'success': False, 'error': '缺少 pattern'}
    if len(pattern) > 100:
        return {'success': False, 'error': 'pattern 太长（>100）'}
    path = params.get('path', '.')
    safe = path.replace(BACKSLASH, '/').strip() if path else '.'
    if safe.startswith('/') or (len(safe) > 1 and safe[1] == ':'):
        return {'success': False, 'error': 'path 不合法'}
    if '..' in safe.split('/'):
        return {'success': False, 'error': 'path 不合法'}
    file_ext = params.get('file_ext', '').strip()
    if file_ext and not file_ext.startswith('.'):
        file_ext = '.' + file_ext
    max_results = int(params.get('max_results', 30))
    if max_results < 1 or max_results > 100:
        max_results = 30
    matches = []
    scanned = 0
    for full, rel in _iter_files(REPO_ROOT, safe, file_ext):
        scanned += 1
        if scanned > 2000:
            break
        try:
            with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                for ln, line in enumerate(f, 1):
                    if pattern in line:
                        matches.append({'file': rel, 'line': ln, 'text': line.rstrip()[:200]})
                        if len(matches) >= max_results:
                            break
        except Exception:
            continue
        if len(matches) >= max_results:
            break
    return {'success': True, 'pattern': pattern, 'scanned_files': scanned, 'count': len(matches), 'matches': matches}
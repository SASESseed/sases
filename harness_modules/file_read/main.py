import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)
FORBIDDEN_PARTS = ('.env', 'users.db', 'secret_key', 'api_key_encryption')
FORBIDDEN_EXT = ('.key', '.bin', '.pem', '.crt', '.db', '.sqlite')


def _safe_path(p):
    if not p:
        return None
    p = p.replace(BACKSLASH, '/').strip()
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        return None
    if '..' in p.split('/'):
        return None
    lower = p.lower()
    for part in FORBIDDEN_PARTS:
        if part in lower:
            return None
    ext = os.path.splitext(p)[1].lower()
    if ext in FORBIDDEN_EXT:
        return None
    return p


def run(params):
    file_path = params.get('file_path', '')
    safe = _safe_path(file_path)
    if not safe:
        return {'success': False, 'error': 'file_path 不合法或指向敏感文件'}
    abs_path = os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_path):
        return {'success': False, 'error': '文件不存在: ' + safe}
    if os.path.isdir(abs_path):
        return {'success': False, 'error': safe + ' 是目录，请用 dir_tree'}
    max_lines = int(params.get('max_lines', 200))
    if max_lines < 1 or max_lines > 1000:
        max_lines = 200
    offset = int(params.get('offset', 0))
    if offset < 0:
        offset = 0
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return {'success': False, 'error': str(e)}
    total = len(lines)
    selected = lines[offset:offset + max_lines]
    content = ''.join(selected)
    if len(content) > 8000:
        content = content[:8000] + '...[已截断]'
    return {
        'success': True,
        'file_path': safe,
        'total_lines': total,
        'showing_from': offset + 1,
        'showing_to': min(offset + max_lines, total),
        'content': content,
    }
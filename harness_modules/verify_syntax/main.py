import os
import ast
import subprocess
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOWED_DIRS = ('core/', 'static/', 'scripts/', 'docs/', 'harness_modules/')
FORBIDDEN = ('.env', 'users.db', '.key', '.bin', '.pem', '.crt', 'secret_key', 'api_key_encryption')
BACKUP_DIR = '.backups'


def _check(p):
    if not isinstance(p, str):
        raise ValueError('path must be str')
    p = p.replace(chr(92), '/').strip()
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        raise ValueError('absolute path forbidden')
    if '..' in p.split('/'):
        raise ValueError('path traversal forbidden')
    lower = p.lower()
    for part in FORBIDDEN:
        if part in lower:
            raise ValueError('forbidden path')
    if not any(p.startswith(d) for d in ALLOWED_DIRS):
        raise ValueError('outside allowed dirs')
    return p


def _find_latest_backup(safe_path):
    safe_name = safe_path.replace('/', '__').replace(chr(92), '__')
    bdir = os.path.join(REPO_ROOT, BACKUP_DIR)
    if not os.path.isdir(bdir):
        return None
    matches = [f for f in os.listdir(bdir) if f.startswith(safe_name + '.')]
    if not matches:
        return None
    matches.sort(reverse=True)
    return os.path.join(bdir, matches[0])


def _verify_py(abs_p):
    try:
        with open(abs_p, 'r', encoding='utf-8') as f:
            src = f.read()
        ast.parse(src)
        return True, ''
    except SyntaxError as e:
        return False, 'line ' + str(e.lineno) + ': ' + str(e.msg)
    except Exception as e:
        return False, str(e)


def _verify_js(abs_p):
    try:
        r = subprocess.run(['node', '--check', abs_p], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
        if r.returncode == 0:
            return True, ''
        return False, (r.stderr or '')[:500]
    except FileNotFoundError:
        return None, 'node not available'
    except Exception as e:
        return None, str(e)


def run(params):
    fp = params.get('file_path', '')
    if not fp:
        return {'success': False, 'error': 'missing file_path'}
    try:
        safe = _check(fp)
    except Exception as e:
        return {'success': False, 'error': str(e)}
    abs_p = os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_p):
        return {'success': False, 'error': 'not found: ' + safe}
    ext = os.path.splitext(safe)[1].lower()
    if ext == '.py':
        ok, err = _verify_py(abs_p)
        supported = True
    elif ext == '.js':
        ok, err = _verify_js(abs_p)
        supported = ok is not None
        if ok is None:
            return {'success': True, 'file_path': safe, 'skipped': True, 'reason': err}
    else:
        return {'success': True, 'file_path': safe, 'skipped': True, 'reason': 'ext not checked: ' + ext}
    result = {'success': ok, 'file_path': safe, 'syntax_ok': bool(ok)}
    if not ok:
        result['error'] = err
        bak = _find_latest_backup(safe)
        if bak:
            result['latest_backup'] = os.path.relpath(bak, REPO_ROOT).replace(chr(92), '/')
            result['hint'] = 'from run_python: import shutil; shutil.copy2(\'' + result['latest_backup'] + '\', \'' + safe + '\')'
    return result
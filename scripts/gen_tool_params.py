import os
import re
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, 'harness_modules')

PARAM_PATTERN = re.compile(r"params\.get\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*(.+?))?\)")


def _infer_type(default_repr):
    if not default_repr:
        return 'any'
    d = default_repr.strip()
    if d.startswith('['):
        return 'array'
    if d.startswith('{') or d.startswith('dict('):
        return 'object'
    if d in ('True', 'False'):
        return 'bool'
    if d in ('None',):
        return 'any'
    if d.startswith('int(') or (d and d[0].isdigit()):
        return 'int'
    if d.startswith('float('):
        return 'float'
    if d.startswith('\"') or d.startswith("'"):
        return 'string'
    return 'any'


def _clean_default(default_repr):
    if not default_repr:
        return None
    d = default_repr.strip()
    if d in ('None',):
        return None
    try:
        return eval(d, {'__builtins__': {}}, {})
    except Exception:
        return d.strip('\"\'')


def main():
    updated = 0
    for module_name in sorted(os.listdir(HARNESS_DIR)):
        module_path = os.path.join(HARNESS_DIR, module_name)
        if not os.path.isdir(module_path):
            continue
        main_py = os.path.join(module_path, 'main.py')
        manifest_json = os.path.join(module_path, 'manifest.json')
        if not os.path.exists(main_py) or not os.path.exists(manifest_json):
            continue
        try:
            with open(main_py, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception:
            continue
        matches = PARAM_PATTERN.findall(code)
        if not matches:
            continue
        params_schema = {}
        for name, default in matches:
            if name in params_schema:
                continue
            entry = {'type': _infer_type(default)}
            if default:
                cd = _clean_default(default)
                if cd is not None:
                    entry['default'] = cd
                    entry['desc'] = '\u53ef\u9009'
                else:
                    entry['desc'] = '\u5fc5\u586b'
            else:
                entry['desc'] = '\u5fc5\u586b'
            params_schema[name] = entry
        try:
            with open(manifest_json, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception:
            continue
        if manifest.get('params') == params_schema:
            continue
        manifest['params'] = params_schema
        try:
            with open(manifest_json, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            updated += 1
            print(f'updated: {module_name} -> {list(params_schema.keys())}')
        except Exception as e:
            print(f'failed: {module_name}: {e}')
    print(f'\n\u5171\u66f4\u65b0 {updated} \u4e2a\u6a21\u5757')


if __name__ == '__main__':
    main()

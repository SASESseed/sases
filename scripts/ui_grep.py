import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness_modules.grep_code.main import run

cmds = [
    ('avatar', 'static/css'),
    ('border-radius|padding|max-width', 'static/css/chat.css'),
    ('font-size|#999|#888|#b2b2b2|#95EC69', 'static/css/chat.css'),
    ('group-msg-sender', 'static'),
    ('message-avatar', 'static/css'),
    ('message.user|message.assistant', 'static/css'),
]

for pat, path in cmds:
    print('=' * 60)
    print(f'PATTERN: {pat}  PATH: {path}')
    print('=' * 60)
    r = run({'pattern': pat, 'path': path, 'max_results': 50})
    if not r.get('success'):
        print('  ERROR:', r.get('error'))
        continue
    print(f"  count={r.get('count', 0)}, scanned={r.get('scanned_files', 0)}")
    for m in r.get('matches', []):
        print(f"  {m['file']}:{m['line']} | {m['text']}")
    print()

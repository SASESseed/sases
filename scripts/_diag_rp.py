import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness_modules.run_python.main import run

code = 'from core.services import transfer_service\nr = transfer_service.get_sent_red_packets(2, 10)\nprint("OK:", len(r))'
r = run({'code': code})
print('=== run_python 返回 ===')
print(json.dumps(r, ensure_ascii=False, indent=2))
print('')
print('=== transfer_service 直接 import 测试 ===')
try:
    from core.services import transfer_service
    print('import OK')
    rows = transfer_service.get_sent_red_packets(2, 10)
    print('查询 OK, 行数:', len(rows))
    for x in rows[:3]:
        print(' ', x)
except Exception as e:
    import traceback
    traceback.print_exc()
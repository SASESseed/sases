c = open('static/modules/group_chat.js', encoding='utf-8').read()
import re
for name in ['群积分', '质押积分', '红包配置', '群排行榜', '群公告', '群文件', '群知识库']:
    key = f"openSubpage('{name}'"
    i = c.find(key)
    if i > 0:
        line_no = c[:i].count('\n') + 1
        print(f'=== {name} (行 {line_no}) ===')
        print(c[i:i+250])
        print()
    else:
        print(f'=== {name}: NOT FOUND ===')
        print()
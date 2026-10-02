p = 'static/modules/group_chat.js'
new_func_path = 'temp_group_credits.js'

with open(new_func_path, encoding='utf-8') as f:
    new_func = f.read().rstrip() + '\n\n\n'

with open(p, encoding='utf-8') as f:
    c = f.read()

old_line = "function openGroupCreditsDetail() { alert('群积分详情开发中'); }"
idx = c.find(old_line)
if idx < 0:
    print('old line not found')
else:
    end = idx + len(old_line)
    c = c[:idx] + new_func + c[end:]
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('replaced OK')
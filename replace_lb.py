p = 'static/modules/group_chat.js'
new_func_path = 'temp_leaderboard.js'

with open(new_func_path, encoding='utf-8') as f:
    new_func = f.read().rstrip() + '\n\n\n'

with open(p, encoding='utf-8') as f:
    c = f.read()

old_line = "function openGroupLeaderboard() { alert('群排行榜开发中'); }"
if old_line not in c:
    print('old line not found')
else:
    c = c.replace(old_line, new_func.rstrip())
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('replaced OK')
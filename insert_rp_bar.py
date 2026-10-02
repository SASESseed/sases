p = 'static/modules/group_chat.js'
new_func_path = 'temp_rp_bar.js'

with open(new_func_path, encoding='utf-8') as f:
    new_func = f.read().rstrip() + '\n\n\n'

with open(p, encoding='utf-8') as f:
    c = f.read()

if 'async function loadGroupRedPackets()' in c:
    print('already exists')
else:
    marker = 'async function loadGroupMessages()'
    idx = c.find(marker)
    if idx < 0:
        print('marker not found')
    else:
        c = c[:idx] + new_func + c[idx:]
        # 在 openGroupChat 里调用
        old_call = '  loadGroupTasks();'
        new_call = '  loadGroupTasks();\n  loadGroupRedPackets();'
        c = c.replace(old_call, new_call, 1)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print('inserted OK')
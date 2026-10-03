p = 'static/modules/group_chat.js'
new_func_path = 'temp_transfer_owner_v2.js'

with open(new_func_path, encoding='utf-8') as f:
    new_func = f.read().rstrip() + '\n\n\n'

with open(p, encoding='utf-8') as f:
    c = f.read()

if 'window.openTransferOwnerDialog = async function' in c:
    print('already defined')
else:
    marker = 'window.openAddAdminDialog = function'
    idx = c.find(marker)
    if idx < 0:
        print('marker not found')
    else:
        c = c[:idx] + new_func + c[idx:]
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print('inserted OK')
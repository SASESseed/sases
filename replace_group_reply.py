p = 'static/modules/group_chat.js'
new_func_path = 'temp_group_reply_v2.js'

with open(new_func_path, encoding='utf-8') as f:
    new_func = f.read().rstrip() + '\n\n\n'

with open(p, encoding='utf-8') as f:
    c = f.read()

start = c.find('window.openGroupAgentPickerForReply')
if start < 0:
    print('start not found')
else:
    end = c.find('async function loadGroupMessages', start)
    if end < 0:
        print('end not found')
    else:
        c = c[:start] + new_func + c[end:]
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print('replaced OK')
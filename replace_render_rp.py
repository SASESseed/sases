p = 'static/modules/chat_ui.js'
new_func_path = 'temp_render_rp.js'

with open(new_func_path, encoding='utf-8') as f:
    new_func = f.read().rstrip() + '\n\n'

with open(p, encoding='utf-8') as f:
    c = f.read()

start = c.find('export function renderGroupRedPacketBubble(content) {')
if start < 0:
    print('start not found')
else:
    end = c.find('\n}\n', start)
    if end < 0:
        print('end not found')
    else:
        end += 3
        c = c[:start] + new_func + c[end:]
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print('replaced OK')
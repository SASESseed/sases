p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

start = c.find('window.openSwarmConfig = async function')
if start < 0:
    print('not found')
else:
    end = c.find('window.openSwarmUsage = async function', start)
    if end < 0:
        print('end not found')
    else:
        block = c[start:end]
        block_new = block.replace('}, 100);', '}, 300);')
        if block_new == block:
            print('no 100 to replace')
        else:
            c = c[:start] + block_new + c[end:]
            with open(p, 'w', encoding='utf-8') as f:
                f.write(c)
            print('fixed OK')
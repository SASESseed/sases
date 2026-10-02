p = 'static/modules/chat_menu.js'
with open(p, encoding='utf-8') as f:
    lines = f.readlines()

out = []
for line in lines:
    if 'openRedPacketDialog()' in line and 'function' not in line:
        # 旧的红包入口：群聊时不显示
        stripped = line.strip()
        out.append('      ...(window.currentGroupId ? [] : [' + stripped + ']),\n')
    else:
        out.append(line)

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(out)
print('done')
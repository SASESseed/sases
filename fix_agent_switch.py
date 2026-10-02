p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 找 openAgentSwitch 里的判断
old = "if (swarmEnabled && sharedAgents.length > 0) {"
new = "if (sharedAgents.length > 0) {"

if old in c:
    c = c.replace(old, new)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('fixed')
else:
    print('not found')
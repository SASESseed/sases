p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 尝试多种可能的写法
candidates = [
    "if (swarmEnabled && currentGroupMode === 'swarm' && sharedAgents.length > 0) {",
    "if (swarmEnabled && currentGroupMode === \"swarm\" && sharedAgents.length > 0) {",
]

found = False
for old in candidates:
    if old in c:
        new = "if (swarmEnabled && sharedAgents.length > 0) {"
        c = c.replace(old, new)
        print('replaced:', old[:50])
        found = True
        break

if not found:
    print('NOT FOUND - 请执行以下命令查看实际内容：')
    print("  findstr /n \"swarmEnabled\" static\\modules\\group_chat.js")
else:
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('done')
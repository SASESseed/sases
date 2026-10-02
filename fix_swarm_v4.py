p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. 删掉带 _uid 的 getItem
c = c.replace(
    "localStorage.getItem('sases_group_mode_' + _uid + '_' + groupId)",
    "localStorage.getItem('sases_group_mode_' + groupId)"
)
c = c.replace(
    "localStorage.getItem('sases_agent_' + _uid2 + '_' + currentGroupMode + '_' + groupId)",
    "localStorage.getItem('sases_agent_' + currentGroupMode + '_' + groupId)"
)
c = c.replace(
    "localStorage.getItem('sases_agent_' + _uid + '_' + mode + '_' + currentGroupId)",
    "localStorage.getItem('sases_agent_' + mode + '_' + currentGroupId)"
)

# 2. 删掉带 _uid 的 setItem
c = c.replace(
    "localStorage.setItem('sases_agent_' + _uid + '_' + currentGroupMode + '_' + currentGroupId, currentAgentId || '')",
    "localStorage.setItem('sases_agent_' + currentGroupMode + '_' + currentGroupId, currentAgentId || '')"
)
c = c.replace(
    "localStorage.setItem('sases_group_mode_' + _uid + '_' + currentGroupId, mode)",
    "localStorage.setItem('sases_group_mode_' + currentGroupId, mode)"
)

# 3. 清掉无用的 _uid / _uid2 变量行
c = c.replace("    const _uid = currentUserId || 'anon';\n", "")
c = c.replace("    const _uid2 = currentUserId || 'anon';\n", "")
c = c.replace("  const _uid = currentUserId || 'anon';\n", "")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
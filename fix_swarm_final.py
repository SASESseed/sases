p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 修复 1：删除硬编码的 currentGroupMode = 'normal'
old1 = """  window.currentGroupId = groupId;
  currentGroupName = groupName;
  currentAgentId = null;
  currentGroupMode = 'normal';
  window.currentGroupChat = true;"""
new1 = """  window.currentGroupId = groupId;
  currentGroupName = groupName;
  window.currentGroupChat = true;"""

if old1 in c:
    c = c.replace(old1, new1)
    print('1. removed hardcoded normal mode')
else:
    print('1. not found')

# 修复 2：updateIdentityButton 字段名
old2 = "m.updateIdentityButton({ currentAgentId: currentAgentId });"
new2 = "m.updateIdentityButton({ senderAgentId: currentAgentId });"
if old2 in c:
    c = c.replace(old2, new2)
    print('2. fixed field name')
else:
    print('2. not found')

# 修复 3：openAgentSwitch 里过滤 sases_assistant
old3 = "    myAgents.forEach(agent => {"
new3 = "    myAgents.filter(a => !(a.agent_id || '').startsWith('sases_assistant')).forEach(agent => {"
if old3 in c:
    c = c.replace(old3, new3)
    print('3. filter sases_assistant')
else:
    print('3. not found')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
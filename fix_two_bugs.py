p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# Bug 1: 删除硬编码的 currentGroupMode = 'normal';
old1 = """  window.currentGroupId = groupId;
  currentGroupName = groupName;
  currentAgentId = null;
  currentGroupMode = 'normal';
  window.currentGroupChat = true;"""

new1 = """  window.currentGroupId = groupId;
  currentGroupName = groupName;
  window.currentGroupChat = true;"""

if old1 not in c:
    print('1. NOT FOUND')
else:
    c = c.replace(old1, new1)
    print('1. removed hardcoded normal mode')

# Bug 2: updateIdentityButton 调用字段
old2 = "m.updateIdentityButton({ currentAgentId: currentAgentId });"
new2 = "m.updateIdentityButton({ senderAgentId: currentAgentId });"

if old2 not in c:
    print('2. NOT FOUND')
else:
    c = c.replace(old2, new2)
    print('2. field name fixed')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
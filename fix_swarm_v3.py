p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. openGroupChat: 调整顺序 + key 加 uid
old1 = """export async function openGroupChat(groupId, groupName) {
  currentGroupId = groupId;
  try {
    currentGroupMode = localStorage.getItem('sases_group_mode_' + groupId) || 'normal';
  } catch (e) {
    currentGroupMode = 'normal';
  }

  window.currentGroupId = groupId;
  currentGroupName = groupName;
  window.currentGroupChat = true;

  // 恢复当前模式对应的身份
  try {
    const _saved = localStorage.getItem('sases_agent_' + currentGroupMode + '_' + groupId) || '';
    currentAgentId = _saved || null;
  } catch (e) {
    currentAgentId = null;
  }

  // 获取当前用户ID（await 保证 loadGroupMessages 前就绪）
  try {
    const _me = await api.getMe();
    currentUserId = _me.user_id;
  } catch (_e) {
    currentUserId = null;
  }
"""

new1 = """export async function openGroupChat(groupId, groupName) {
  currentGroupId = groupId;

  // 先获取当前用户ID
  try {
    const _me = await api.getMe();
    currentUserId = _me.user_id;
  } catch (_e) {
    currentUserId = null;
  }

  // 从 localStorage 读取该用户的群模式
  try {
    const _uid = currentUserId || 'anon';
    currentGroupMode = localStorage.getItem('sases_group_mode_' + _uid + '_' + groupId) || 'normal';
  } catch (e) {
    currentGroupMode = 'normal';
  }

  window.currentGroupId = groupId;
  currentGroupName = groupName;
  window.currentGroupChat = true;

  // 恢复当前模式对应的身份
  try {
    const _uid2 = currentUserId || 'anon';
    const _saved = localStorage.getItem('sases_agent_' + _uid2 + '_' + currentGroupMode + '_' + groupId) || '';
    currentAgentId = _saved || null;
  } catch (e) {
    currentAgentId = null;
  }
"""

if old1 not in c:
    print('1. openGroupChat NOT FOUND')
else:
    c = c.replace(old1, new1)
    print('1. openGroupChat reordered: OK')

# 2. applyGroupMode: 保存时用 uid
old2 = """  // 保存当前模式下的身份选择
  try {
    localStorage.setItem('sases_agent_' + currentGroupMode + '_' + currentGroupId, currentAgentId || '');
  } catch (e) {}
  currentGroupMode = mode;
  try {
    localStorage.setItem('sases_group_mode_' + currentGroupId, mode);
  } catch (e) {}"""

new2 = """  const _uid = currentUserId || 'anon';
  // 保存当前模式下的身份选择
  try {
    localStorage.setItem('sases_agent_' + _uid + '_' + currentGroupMode + '_' + currentGroupId, currentAgentId || '');
  } catch (e) {}
  currentGroupMode = mode;
  try {
    localStorage.setItem('sases_group_mode_' + _uid + '_' + currentGroupId, mode);
  } catch (e) {}"""

if old2 not in c:
    print('2. applyGroupMode save NOT FOUND')
else:
    c = c.replace(old2, new2)
    print('2. applyGroupMode save: OK')

# 3. applyGroupMode: 恢复时用 uid
old3 = """  // 恢复新模式下的身份选择
  try {
    const saved = localStorage.getItem('sases_agent_' + mode + '_' + currentGroupId) || '';
    currentAgentId = saved || null;
  } catch (e) {
    currentAgentId = null;
  }"""

new3 = """  // 恢复新模式下的身份选择
  try {
    const _saved = localStorage.getItem('sases_agent_' + _uid + '_' + mode + '_' + currentGroupId) || '';
    currentAgentId = _saved || null;
  } catch (e) {
    currentAgentId = null;
  }"""

if old3 not in c:
    print('3. applyGroupMode restore NOT FOUND')
else:
    c = c.replace(old3, new3)
    print('3. applyGroupMode restore: OK')

# 4. closeGroupChat: 不重置 currentGroupMode
old4 = """  currentAgentId = null;
  currentGroupMode = 'normal';
  currentUserId = null;"""
new4 = """  currentAgentId = null;
  currentUserId = null;"""

if old4 not in c:
    print('4. closeGroupChat NOT FOUND')
else:
    c = c.replace(old4, new4)
    print('4. closeGroupChat: OK')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. 替换 applyGroupMode：不再调后端，改本地存储
old_apply = """async function applyGroupMode(mode) {
  try {
    await api.setGroupMode(currentGroupId, mode);
    currentGroupMode = mode;
    const modeText = document.getElementById('chat-mode-text');
    if (modeText) modeText.textContent = mode === 'normal' ? '普通聊天' : '蜂群模式';
    if (typeof window.showGroupToast === 'function') {
      window.showGroupToast(mode === 'swarm' ? '已切换到蜂群模式' : '已切换到普通模式');
    }
  } catch (e) {
    alert('切换失败：' + e.message);
  }
}"""

new_apply = """async function applyGroupMode(mode) {
  currentGroupMode = mode;
  try {
    localStorage.setItem('sases_group_mode_' + currentGroupId, mode);
  } catch (e) {}
  const modeText = document.getElementById('chat-mode-text');
  if (modeText) modeText.textContent = mode === 'normal' ? '普通聊天' : '蜂群模式';
  if (typeof window.showGroupToast === 'function') {
    window.showGroupToast(mode === 'swarm' ? '已切换到蜂群模式' : '已切换到普通模式');
  }
}"""

if old_apply not in c:
    print('1. applyGroupMode NOT FOUND')
else:
    c = c.replace(old_apply, new_apply)
    print('1. applyGroupMode replaced')

# 2. 打开群聊时恢复本地模式
old_open = "  currentGroupId = groupId;"
new_open = """  currentGroupId = groupId;
  try {
    currentGroupMode = localStorage.getItem('sases_group_mode_' + groupId) || 'normal';
  } catch (e) {
    currentGroupMode = 'normal';
  }"""

if old_open not in c:
    print('2. openGroupChat anchor NOT FOUND')
else:
    # 只替换第一次出现（openGroupChat 里）
    c = c.replace(old_open, new_open, 1)
    print('2. openGroupChat restored mode from localStorage')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
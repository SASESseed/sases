p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. applyGroupMode 里切换/恢复身份
old1 = """async function applyGroupMode(mode) {
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

new1 = """async function applyGroupMode(mode) {
  // 保存当前模式下的身份选择
  try {
    localStorage.setItem('sases_agent_' + currentGroupMode + '_' + currentGroupId, currentAgentId || '');
  } catch (e) {}
  currentGroupMode = mode;
  try {
    localStorage.setItem('sases_group_mode_' + currentGroupId, mode);
  } catch (e) {}
  // 恢复新模式下的身份选择
  try {
    const saved = localStorage.getItem('sases_agent_' + mode + '_' + currentGroupId) || '';
    currentAgentId = saved || null;
  } catch (e) {
    currentAgentId = null;
  }
  const modeText = document.getElementById('chat-mode-text');
  if (modeText) modeText.textContent = mode === 'normal' ? '普通聊天' : '蜂群模式';
  if (typeof window.showGroupToast === 'function') {
    window.showGroupToast(mode === 'swarm' ? '已切换到蜂群模式' : '已切换到普通模式');
  }
  // 更新 🤖 按钮显示
  try {
    const m = await import('./chat_identity.js');
    if (m && typeof m.updateIdentityButton === 'function') {
      m.updateIdentityButton({ currentAgentId: currentAgentId });
    }
  } catch (e) {}
}"""

if old1 not in c:
    print('1. applyGroupMode NOT FOUND')
else:
    c = c.replace(old1, new1)
    print('1. applyGroupMode updated')

# 2. 身份选择后保存到对应模式
old2 = """        currentAgentId = opt.dataset.agentId || null;
        window.currentAgentSource = opt.dataset.agentSource || 'self';
        window.closeSubpage();"""
new2 = """        currentAgentId = opt.dataset.agentId || null;
        window.currentAgentSource = opt.dataset.agentSource || 'self';
        try {
          localStorage.setItem('sases_agent_' + currentGroupMode + '_' + currentGroupId, currentAgentId || '');
        } catch (e) {}
        window.closeSubpage();"""

if old2 not in c:
    print('2. NOT FOUND')
else:
    c = c.replace(old2, new2)
    print('2. agent selection saved per mode')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
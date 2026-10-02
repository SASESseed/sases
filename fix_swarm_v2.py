p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 修复 1：打开群聊时同步模式按钮 + 恢复身份
old1 = """  window.currentGroupId = groupId;
  currentGroupName = groupName;
  window.currentGroupChat = true;
"""
new1 = """  window.currentGroupId = groupId;
  currentGroupName = groupName;
  window.currentGroupChat = true;

  // 恢复当前模式对应的身份
  try {
    const _saved = localStorage.getItem('sases_agent_' + currentGroupMode + '_' + groupId) || '';
    currentAgentId = _saved || null;
  } catch (e) {
    currentAgentId = null;
  }
"""
if old1 in c:
    c = c.replace(old1, new1)
    print('1. restore identity by mode: OK')
else:
    print('1. NOT FOUND')

# 修复 2：模式按钮文字同步（在 openGroupChat 里 update 一下）
old2 = """  document.getElementById('chat-window-title').textContent = groupName;
  document.getElementById('view-chat-window').style.display = 'flex';"""
new2 = """  document.getElementById('chat-window-title').textContent = groupName;
  const _mt0 = document.getElementById('chat-mode-text');
  if (_mt0) _mt0.textContent = currentGroupMode === 'normal' ? '普通聊天' : '蜂群模式';
  document.getElementById('view-chat-window').style.display = 'flex';"""
if old2 in c:
    c = c.replace(old2, new2, 1)
    print('2. sync mode text on open: OK')
else:
    print('2. NOT FOUND')

# 修复 3：openAgentSwitch 里，蜂群模式只显示共享，普通模式只显示个人
old3 = """    let html = '';
    html += '<div class="section-title">我的智能体</div>';
    html += '<div class="me-menu">';
    html += '<div class="me-menu-item agent-option" data-agent-id="" data-agent-source="self">以本人身份</div>';
    if (myAgents.length === 0) {
      html += '<div class="subpage-placeholder" style="padding:20px 0;font-size:13px;">你还没有智能体</div>';
    } else {
      myAgents.filter(a => !(a.agent_id || '').startsWith('sases_assistant')).forEach(agent => {
        html += '<div class="me-menu-item agent-option" data-agent-id="' + agent.agent_id + '" data-agent-source="self">';
        html += '<span class="menu-label">' + (agent.name || agent.agent_id) + '</span>';
        html += '<span class="menu-arrow">›</span>';
        html += '</div>';
      });
    }
    html += '</div>';"""

new3 = """    let html = '';
    const isSwarm = currentGroupMode === 'swarm';

    if (!isSwarm) {
      // 普通模式：我的智能体
      html += '<div class="section-title">我的智能体</div>';
      html += '<div class="me-menu">';
      html += '<div class="me-menu-item agent-option" data-agent-id="" data-agent-source="self">以本人身份</div>';
      const _myFiltered = myAgents.filter(a => !(a.agent_id || '').startsWith('sases_assistant'));
      if (_myFiltered.length === 0) {
        html += '<div class="subpage-placeholder" style="padding:20px 0;font-size:13px;">你还没有智能体</div>';
      } else {
        _myFiltered.forEach(agent => {
          html += '<div class="me-menu-item agent-option" data-agent-id="' + agent.agent_id + '" data-agent-source="self">';
          html += '<span class="menu-label">' + (agent.name || agent.agent_id) + '</span>';
          html += '<span class="menu-arrow">›</span>';
          html += '</div>';
        });
      }
      html += '</div>';
    } else {
      // 蜂群模式：以本人身份 + 群共享
      html += '<div class="section-title">群共享智能体</div>';
      html += '<div class="me-menu">';
      html += '<div class="me-menu-item agent-option" data-agent-id="" data-agent-source="self">以本人身份</div>';
      if (sharedAgents.length === 0) {
        html += '<div class="subpage-placeholder" style="padding:20px 0;font-size:13px;">群主未共享智能体</div>';
      } else {
        sharedAgents.forEach(p => {
          html += '<div class="me-menu-item agent-option" data-agent-id="' + p.agent_id + '" data-agent-source="group">';
          html += '<span class="menu-label">' + (p.model_name || p.agent_id) + '</span>';
          html += '</div>';
        });
      }
      html += '</div>';
    }"""

if old3 in c:
    c = c.replace(old3, new3)
    print('3. mode-specific identity list: OK')
else:
    print('3. NOT FOUND')

# 修复 4：切模式时如果当前身份不可用，重置为本人
old4 = """  // 恢复新模式下的身份选择
  try {
    const saved = localStorage.getItem('sases_agent_' + mode + '_' + currentGroupId) || '';
    currentAgentId = saved || null;
  } catch (e) {
    currentAgentId = null;
  }"""
new4 = """  // 恢复新模式下的身份选择
  try {
    const saved = localStorage.getItem('sases_agent_' + mode + '_' + currentGroupId) || '';
    currentAgentId = saved || null;
  } catch (e) {
    currentAgentId = null;
  }
  // 校验当前身份是否合法（蜂群模式下不能选自己的私有智能体）
  if (mode === 'swarm' && currentAgentId) {
    try {
      const _pr = await fetch('/group/' + currentGroupId + '/resource-pool', {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      });
      const _pd = await _pr.json();
      const _sharedIds = (_pd.pool || []).map(p => p.agent_id);
      if (!_sharedIds.includes(currentAgentId)) {
        currentAgentId = null;
      }
    } catch (e) {
      currentAgentId = null;
    }
  }"""
if old4 in c:
    c = c.replace(old4, new4)
    print('4. validate identity by mode: OK')
else:
    print('4. NOT FOUND')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
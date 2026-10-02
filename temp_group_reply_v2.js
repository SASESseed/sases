window._generateReplyWithAgent = async function(agentId, source, quotedText, groupId) {
  const prompt = '请基于以下群友的消息，帮我生成一条合适的回复：\n\n' + (quotedText || '');
  try {
    const url = source === 'group'
      ? '/group/' + groupId + '/ai-suggest'
      : '/agents/chat';
    const body = source === 'group'
      ? { agent_id: agentId, question: prompt }
      : { agent_id: agentId, query: prompt };
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await resp.json();
    if (data.error || data.detail) { alert('生成失败：' + (data.error || data.detail)); return; }
    const reply = data.response || '（无建议）';
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = reply;
      if (typeof window.updateSendButtonVisibility === 'function') {
        window.updateSendButtonVisibility();
      }
      input.focus();
    }
  } catch (e) {
    alert('网络错误：' + e.message);
  }
};

window.openGroupAgentPickerForReply = async function(quotedText, groupId) {
  // 决策 1：优先用当前切换的身份
  if (typeof currentAgentId !== 'undefined' && currentAgentId) {
    const source = window.currentAgentSource || 'self';
    await window._generateReplyWithAgent(currentAgentId, source, quotedText, groupId);
    return;
  }

  // 决策 2：没切身份 → 弹选择列表
  let myAgents = [];
  let sharedAgents = [];

  try {
    const mine = await api.listMyAgents();
    myAgents = ((mine && mine.agents) || []).filter(a => !(a.agent_id || '').startsWith('sases_assistant'));
  } catch (e) {}

  try {
    const poolResp = await fetch('/group/' + groupId + '/resource-pool', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const poolData = await poolResp.json();
    sharedAgents = (poolData.pool || []).filter(p => p.enabled);
  } catch (e) {}

  const html = `
    <div class="me-menu" id="reply-agent-list">
      <div class="section-title">我的智能体</div>
      ${myAgents.length === 0 ? '<div class="subpage-placeholder" style="padding:20px 0;font-size:13px;">无</div>' : ''}
      ${myAgents.map(a => '<div class="me-menu-item reply-agent-option" data-agent-id="' + a.agent_id + '" data-source="self"><span class="menu-label">' + (a.name || a.agent_id) + '</span><span class="menu-arrow">›</span></div>').join('')}
      ${sharedAgents.length > 0 ? '<div class="section-title">群共享智能体</div>' : ''}
      ${sharedAgents.map(p => '<div class="me-menu-item reply-agent-option" data-agent-id="' + p.agent_id + '" data-source="group"><span class="menu-label">' + (p.model_name || p.agent_id) + '</span><span class="menu-value" style="font-size:12px;color:#999;">群共享</span></div>').join('')}
    </div>
  `;

  window.openSubpage('选择智能体生成回复', html, {
    showMore: false,
    returnAction: () => {}
  });

  setTimeout(() => {
    document.querySelectorAll('.reply-agent-option').forEach(el => {
      el.onclick = async () => {
        const agentId = el.dataset.agentId;
        const source = el.dataset.source;
        window.closeSubpage();
        await window._generateReplyWithAgent(agentId, source, quotedText, groupId);
      };
    });
  }, 300);
};
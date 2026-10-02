async function openAgentSwitch() {
  const contentHtml = `
    <div class="me-menu" id="agent-switch-list">
      <div class="subpage-placeholder">加载中...</div>
    </div>
  `;
  window.openSubpage('选择发言身份', contentHtml, {
    returnAction: () => openGroupSettings()
  });

  try {
    const mine = await api.listMyAgents();
    const myAgents = (mine && mine.agents) || [];

    let sharedAgents = [];
    let swarmEnabled = false;
    try {
      const poolResp = await fetch('/group/' + currentGroupId + '/resource-pool', {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      });
      const poolData = await poolResp.json();
      swarmEnabled = !!poolData.swarm_enabled;
      sharedAgents = (poolData.pool || []).filter(p => p.enabled);
    } catch (e) {}

    const container = document.getElementById('agent-switch-list');
    if (!container) return;

    let html = '';
    html += '<div class="section-title">我的智能体</div>';
    html += '<div class="me-menu">';
    html += '<div class="me-menu-item agent-option" data-agent-id="" data-agent-source="self">以本人身份</div>';
    if (myAgents.length === 0) {
      html += '<div class="subpage-placeholder" style="padding:20px 0;font-size:13px;">你还没有智能体</div>';
    } else {
      myAgents.forEach(agent => {
        html += '<div class="me-menu-item agent-option" data-agent-id="' + agent.agent_id + '" data-agent-source="self">';
        html += '<span class="menu-label">' + (agent.name || agent.agent_id) + '</span>';
        html += '<span class="menu-arrow">›</span>';
        html += '</div>';
      });
    }
    html += '</div>';

    if (swarmEnabled && sharedAgents.length > 0) {
      html += '<div class="section-title">群共享（蜂群模式）</div>';
      html += '<div class="me-menu">';
      sharedAgents.forEach(p => {
        html += '<div class="me-menu-item agent-option" data-agent-id="' + p.agent_id + '" data-agent-source="group">';
        html += '<span class="menu-label">' + (p.model_name || p.agent_id) + '</span>';
        html += '<span class="menu-value" style="font-size:12px;color:#999;">群共享</span>';
        html += '</div>';
      });
      html += '</div>';
    }

    container.innerHTML = html;

    container.querySelectorAll('.agent-option').forEach(opt => {
      opt.addEventListener('click', () => {
        currentAgentId = opt.dataset.agentId || null;
        window.currentAgentSource = opt.dataset.agentSource || 'self';
        window.closeSubpage();
        document.getElementById('chat-window-title').textContent = currentGroupName + (currentAgentId ? ' (智能体)' : '');
        openGroupSettings();
      });
    });
  } catch (e) {
    const container = document.getElementById('agent-switch-list');
    if (container) {
      container.innerHTML = '<div class="subpage-placeholder">加载失败：' + e.message + '</div>';
    }
  }
}
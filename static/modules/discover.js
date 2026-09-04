// static/modules/discover.js
import { api } from './api.js';
import { t } from './i18n.js';

let initialized = false;

export function initDiscover() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('discover-content');
  if (!container) return;

  renderDiscoverEntries(container);

  // 监听语言变化，重新渲染入口
  window.addEventListener('langchange', () => {
    renderDiscoverEntries(container);
  });
}

function renderDiscoverEntries(container) {
  const entries = [
    { icon: '🌌', title: t('wisdom_space'), desc: t('ai_contribution_nodes'), action: 'wisdom' },
    { icon: '🌐', title: t('ai_circle'), desc: t('ai_moments'), action: 'ai-circle' },
    { icon: '📷', title: t('scan'), desc: t('scan_qr_or_seed'), action: 'scan' },
    { icon: '🎮', title: t('games'), desc: t('ai_game_center'), action: 'game' },
    { icon: '🏆', title: t('leaderboard'), desc: t('contribution_rank'), action: 'leaderboard' },
    { icon: '🧠', title: t('ai_agents'), desc: t('agent_market'), action: 'agents' }
  ];

  let html = `<div class="me-menu">`;
  entries.forEach(entry => {
    html += `
      <div class="me-menu-item" data-entry="${entry.title}" data-action="${entry.action}">
        <span class="menu-icon">${entry.icon}</span>
        <div class="menu-text">
          <div class="menu-title">${entry.title}</div>
          <div class="menu-desc">${entry.desc}</div>
        </div>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;

  // 绑定点击事件
  container.querySelectorAll('[data-entry]').forEach(item => {
    item.addEventListener('click', () => {
      const action = item.dataset.action;
      const title = item.dataset.entry;
      if (action === 'wisdom') {
        openWisdomSpace(title);
      } else if (action === 'ai-circle') {
        openAiCircle(title);
      } else if (action === 'leaderboard') {
        openLeaderboard(title);
      } else {
        window.openSubpage(title, `<div class="subpage-placeholder">${t('coming_soon')}</div>`);
      }
    });
  });
}

async function openWisdomSpace(title) {
  let nodesHtml = `<div class="subpage-placeholder">${t('loading')}</div>`;
  window.openSubpage(title, nodesHtml);

  try {
    const data = await api.getWisdomSpaceNodes();
    const nodes = data.nodes || [];
    if (nodes.length === 0) {
      nodesHtml = `<div class="subpage-placeholder">${t('no_nodes')}</div>`;
    } else {
      nodesHtml = '<div class="me-menu">';
      nodes.forEach(node => {
        const icon = node.node_type === 'agent' ? '🤖' : node.node_type === 'contribution' ? '🌱' : '📚';
        nodesHtml += `
          <div class="me-menu-item">
            <span class="menu-icon">${icon}</span>
            <div class="menu-text">
              <div class="menu-title">${node.name}</div>
              <div class="menu-desc">${node.detail || ''}</div>
            </div>
          </div>
        `;
      });
      nodesHtml += '</div>';
    }
  } catch (e) {
    nodesHtml = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }

  document.getElementById('subpage-content').innerHTML = nodesHtml;
}

async function openAiCircle(title) {
  let postsHtml = `<div class="subpage-placeholder">${t('loading')}</div>`;
  window.openSubpage(title, postsHtml);

  try {
    const data = await api.getAiCirclePosts();
    const posts = data.posts || [];
    if (posts.length === 0) {
      postsHtml = `<div class="subpage-placeholder">${t('no_posts')}</div>`;
    } else {
      postsHtml = '<div class="ai-post-list">';
      posts.forEach(post => {
        const date = new Date(post.created_at).toLocaleString('zh-CN');
        postsHtml += `
          <div class="ai-post-item">
            <div class="ai-post-header">
              <span class="ai-post-agent">🤖 ${post.agent_id}</span>
              <span class="ai-post-owner">by ${post.owner_name}</span>
            </div>
            <div class="ai-post-content">${post.content}</div>
            <div class="ai-post-time">${date}</div>
          </div>
        `;
      });
      postsHtml += '</div>';
    }
  } catch (e) {
    postsHtml = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }

  const contentHtml = `
    <div class="ai-publish-area">
      <textarea id="ai-post-input" class="ai-post-input" placeholder="${t('share_agent_moment')}"></textarea>
      <button id="ai-post-btn" class="save-btn">${t('publish')}</button>
    </div>
    ${postsHtml}
  `;
  document.getElementById('subpage-content').innerHTML = contentHtml;

  const publishBtn = document.getElementById('ai-post-btn');
  const postInput = document.getElementById('ai-post-input');
  if (publishBtn && postInput) {
    publishBtn.addEventListener('click', async () => {
      const content = postInput.value.trim();
      if (!content) { alert(t('please_input_all')); return; }
      try {
        await api.createAiCirclePost(content, 'daily');
        alert(t('publish_success'));
        postInput.value = '';
        openAiCircle(title);
      } catch (e) {
        alert(t('publish_failed') + ': ' + e.message);
      }
    });
  }
}

async function openLeaderboard(title) {
  let contentHtml = `<div class="subpage-placeholder">${t('loading')}</div>`;
  window.openSubpage(title, contentHtml);

  try {
    const data = await api.getLeaderboard();
    const users = data.leaderboard || [];
    if (users.length === 0) {
      contentHtml = `<div class="subpage-placeholder">${t('no_data')}</div>`;
    } else {
      let listHtml = '<div class="me-menu">';
      users.forEach(user => {
        const medal = user.rank === 1 ? '🥇' : user.rank === 2 ? '🥈' : user.rank === 3 ? '🥉' : `${user.rank}.`;
        listHtml += `
          <div class="me-menu-item leaderboard-item">
            <span class="menu-icon">${medal}</span>
            <div class="leaderboard-avatar">${user.avatar}</div>
            <div class="menu-text">
              <div class="menu-title">${user.username}</div>
            </div>
          </div>
        `;
      });
      listHtml += '</div>';
      contentHtml = listHtml;
    }
  } catch (e) {
    contentHtml = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }
  document.getElementById('subpage-content').innerHTML = contentHtml;
}
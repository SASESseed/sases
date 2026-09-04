// static/modules/discover.js
import { api } from './api.js';

let initialized = false;

export function initDiscover() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('discover-content');
  if (!container) return;

  const entries = [
    { icon: '🌌', title: '智维空间', desc: 'AI 贡献节点', action: 'wisdom' },
    { icon: '🌐', title: 'AI圈', desc: 'AI 朋友圈', action: 'ai-circle' },
    { icon: '📷', title: '扫一扫', desc: '扫描二维码或种子', action: 'scan' },
    { icon: '🎮', title: '游戏', desc: 'AI 游戏中心', action: 'game' },
    { icon: '🏆', title: '排行榜', desc: '贡献排行（非积分）', action: 'leaderboard' },
    { icon: '🧠', title: 'AI代理', desc: '智能体市场', action: 'agents' }
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
        window.openSubpage(title, `<div class="subpage-placeholder">${title} 功能待实现</div>`);
      }
    });
  });
}

async function openWisdomSpace(title) {
  let nodesHtml = '<div class="subpage-placeholder">加载中...</div>';
  window.openSubpage(title, nodesHtml);

  try {
    const data = await api.getWisdomSpaceNodes();
    const nodes = data.nodes || [];
    if (nodes.length === 0) {
      nodesHtml = '<div class="subpage-placeholder">暂无节点</div>';
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
    nodesHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }

  document.getElementById('subpage-content').innerHTML = nodesHtml;
}

async function openAiCircle(title) {
  let postsHtml = '<div class="subpage-placeholder">加载中...</div>';
  window.openSubpage(title, postsHtml);

  try {
    const data = await api.getAiCirclePosts();
    const posts = data.posts || [];
    if (posts.length === 0) {
      postsHtml = '<div class="subpage-placeholder">暂无动态</div>';
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
    postsHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }

  const contentHtml = `
    <div class="ai-publish-area">
      <textarea id="ai-post-input" class="ai-post-input" placeholder="分享你的智能体动态..."></textarea>
      <button id="ai-post-btn" class="save-btn">发布</button>
    </div>
    ${postsHtml}
  `;
  document.getElementById('subpage-content').innerHTML = contentHtml;

  const publishBtn = document.getElementById('ai-post-btn');
  const postInput = document.getElementById('ai-post-input');
  if (publishBtn && postInput) {
    publishBtn.addEventListener('click', async () => {
      const content = postInput.value.trim();
      if (!content) { alert('请输入内容'); return; }
      try {
        await api.createAiCirclePost(content, 'daily');
        alert('发布成功');
        postInput.value = '';
        openAiCircle(title);
      } catch (e) {
        alert('发布失败：' + e.message);
      }
    });
  }
}

async function openLeaderboard(title) {
  let contentHtml = '<div class="subpage-placeholder">加载中...</div>';
  window.openSubpage(title, contentHtml);

  try {
    const data = await api.getLeaderboard();
    const users = data.leaderboard || [];
    if (users.length === 0) {
      contentHtml = '<div class="subpage-placeholder">暂无排行数据</div>';
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
    contentHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
  document.getElementById('subpage-content').innerHTML = contentHtml;
}
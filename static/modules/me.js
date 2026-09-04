// static/modules/me.js
import { api } from './api.js';

let initialized = false;

export function initMe() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('me-content');
  if (!container) return;

  const username = localStorage.getItem('sases_username') || '用户';
  const sasesId = localStorage.getItem('sases_sas_id') || '未设置';
  const credits = localStorage.getItem('sases_credits_cache') || '0';

  container.innerHTML = `
    <div class="me-profile-card">
      <div class="me-profile-main" id="me-profile-main">
        <div class="me-avatar">${username.charAt(0).toUpperCase()}</div>
        <div class="me-info">
          <div class="me-name">${username}</div>
          <div class="me-id">SASES ID: ${sasesId}</div>
          <div class="me-credits">种子积分: ${credits}</div>
        </div>
        <div class="me-qrcode" id="me-qrcode">二维码</div>
        <div class="me-edit" id="me-edit-profile">✏️</div>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-models">
        <span class="menu-icon">🤖</span>
        <span class="menu-label">模型管理</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="menu-wallet">
        <span class="menu-icon">💰</span>
        <span class="menu-label">积分中心</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-knowledge">
        <span class="menu-icon">📚</span>
        <span class="menu-label">知识库</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="menu-contributions">
        <span class="menu-icon">🌱</span>
        <span class="menu-label">我的贡献</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-settings">
        <span class="menu-icon">⚙️</span>
        <span class="menu-label">设置</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
  `;

  document.getElementById('me-profile-main').addEventListener('click', openPersonalInfo);
  document.getElementById('me-edit-profile').addEventListener('click', (e) => {
    e.stopPropagation();
    openPersonalInfo();
  });

  document.getElementById('me-qrcode').addEventListener('click', (e) => {
    e.stopPropagation();
    window.openSubpage('我的二维码', `
      <div style="text-align:center;padding:40px 20px;">
        <div style="font-size:16px;margin-bottom:20px;">扫描添加我为好友</div>
        <div style="width:200px;height:200px;margin:0 auto;background:#fff;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:80px;">🔳</div>
        <div style="margin-top:16px;color:#888;font-size:13px;">SASES ID: ${sasesId}</div>
      </div>
    `);
  });

  document.getElementById('menu-models').addEventListener('click', openModelManagement);
  document.getElementById('menu-wallet').addEventListener('click', openWallet);
  document.getElementById('menu-knowledge').addEventListener('click', openKnowledgeBase);
  document.getElementById('menu-contributions').addEventListener('click', openContributions);
  document.getElementById('menu-settings').addEventListener('click', openSettings);

  // 更新缓存积分
  api.getBalance().then(data => {
    localStorage.setItem('sases_credits_cache', data.balance);
    const creditEl = document.querySelector('.me-credits');
    if (creditEl) creditEl.textContent = `种子积分: ${data.balance}`;
  }).catch(() => {});
}

// ==================== 个人主页（从后端加载/保存） ====================
async function openPersonalInfo() {
  let profile = null;
  try {
    profile = await api.getUserProfile();
  } catch (e) {
    console.warn('获取资料失败，使用本地缓存', e);
  }

  const username = profile?.username || localStorage.getItem('sases_username') || '用户';
  const sasesId = profile?.sases_id || localStorage.getItem('sases_sas_id') || '未设置';
  const gender = profile?.gender || localStorage.getItem('sases_gender') || '未设置';
  const region = profile?.region || localStorage.getItem('sases_region') || '未设置';
  const signature = profile?.signature || localStorage.getItem('sases_signature') || '未设置';

  const contentHtml = `
    <div class="personal-info-header">
      <div class="personal-info-avatar">${username.charAt(0).toUpperCase()}</div>
      <div class="personal-info-name">${username}</div>
      <div class="personal-info-id">SASES ID: ${sasesId}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="edit-nickname">
        <span class="menu-label">昵称</span>
        <span class="menu-value">${username}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-sases-id">
        <span class="menu-label">SASES ID</span>
        <span class="menu-value">${sasesId}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-gender">
        <span class="menu-label">性别</span>
        <span class="menu-value">${gender}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-region">
        <span class="menu-label">地区</span>
        <span class="menu-value">${region}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-signature">
        <span class="menu-label">个性签名</span>
        <span class="menu-value">${signature}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
  `;

  window.openSubpage('个人信息', contentHtml);

  setTimeout(() => {
    document.getElementById('edit-nickname').onclick = async () => {
      const newName = prompt('请输入新昵称：', username);
      if (newName && newName.trim()) {
        try {
          await api.updateUserProfile({ username: newName.trim() });
          localStorage.setItem('sases_username', newName.trim());
          alert('昵称已更新');
          window.closeSubpage();
          initMe();
        } catch (e) {
          alert('更新失败：' + e.message);
        }
      }
    };

    document.getElementById('edit-sases-id').onclick = () => alert('SASES ID 不可修改');

    document.getElementById('edit-gender').onclick = async () => {
      const newGender = prompt('请输入性别：', gender);
      if (newGender) {
        try {
          await api.updateUserProfile({ gender: newGender });
          localStorage.setItem('sases_gender', newGender);
          alert('性别已保存');
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) {
          alert('保存失败：' + e.message);
        }
      }
    };

    document.getElementById('edit-region').onclick = async () => {
      const newRegion = prompt('请输入地区：', region);
      if (newRegion) {
        try {
          await api.updateUserProfile({ region: newRegion });
          localStorage.setItem('sases_region', newRegion);
          alert('地区已保存');
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) {
          alert('保存失败：' + e.message);
        }
      }
    };

    document.getElementById('edit-signature').onclick = async () => {
      const newSignature = prompt('请输入个性签名：', signature);
      if (newSignature) {
        try {
          await api.updateUserProfile({ signature: newSignature });
          localStorage.setItem('sases_signature', newSignature);
          alert('个性签名已保存');
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) {
          alert('保存失败：' + e.message);
        }
      }
    };
  }, 100);
}

// ==================== 模型管理 ====================
async function openModelManagement() {
  let modelsHtml = '';

  try {
    const data = await api.listModels();
    const models = data.models || [];
    if (models.length === 0) {
      modelsHtml = '<div class="subpage-placeholder">暂无模型，点击下方按钮添加</div>';
    } else {
      modelsHtml = '<div class="me-menu">';
      models.forEach(m => {
        const icon = m.model_type === 'local' ? '🖥️' : '🔑';
        const detail = m.model_type === 'local' ? `${m.model_name} @ ${m.node_url}` : `${m.provider}`;
        const bonusTag = m.model_type === 'local' ? ' <span style="color:green;font-size:12px;">授粉+2</span>' : '';
        const shareText = m.is_shared ? '已共享' : '未共享';
        modelsHtml += `
          <div class="me-menu-item model-item" data-model-id="${m.id}" data-is-shared="${m.is_shared}" data-visibility="${m.visibility}" data-price="${m.price}">
            <span>${icon}</span>
            <div class="model-info">
              <div>${m.name}${bonusTag}</div>
              <div class="model-detail">${detail}</div>
              <div class="model-id-display" style="font-size:12px;color:#999;">ID: ${m.id}</div>
              <div class="model-share-info" style="font-size:12px;color:#007aff;">${shareText} · ${m.visibility} · ${m.price}积分/次</div>
            </div>
            <button class="edit-share-btn" data-model-id="${m.id}">共享设置</button>
          </div>
        `;
      });
      modelsHtml += '</div>';
    }
  } catch (e) {
    modelsHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }

  const contentHtml = `
    <div style="background:#fff;border-radius:8px;padding:12px;margin-bottom:12px;border-left:4px solid #007aff;">
      <div style="font-weight:500;margin-bottom:6px;">🧭 配置引导</div>
      <div style="font-size:13px;color:#666;line-height:1.5;">
        · <strong>API Key</strong>：调用云端模型（如DeepSeek、OpenAI），无需本地算力，数据将发送至对应服务商。<br>
        · <strong>本地模型</strong>：使用您自己的电脑/节点算力，数据不出设备，隐私性更高，并可获得授粉积分加成（+2）。
      </div>
    </div>
    <div style="background:#fff;border-radius:8px;padding:12px;margin-bottom:12px;border-left:4px solid #ff9500;">
      <div style="font-weight:500;margin-bottom:6px;">⚠️ 风险与合规提示</div>
      <div style="font-size:13px;color:#666;line-height:1.5;">
        · 所有 API Key 均加密存储于本地设备，不会上传至 SASES 服务器。<br>
        · 使用本地模型时，请确保已遵守相关模型的许可证协议。<br>
        · 请勿将 API Key 分享给他人，否则可能导致费用损失。
      </div>
    </div>
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <button id="add-api-key" style="flex:1;padding:10px;background:#007aff;color:#fff;border:none;border-radius:6px;">添加 API Key</button>
      <button id="add-local-model" style="flex:1;padding:10px;background:#34c759;color:#fff;border:none;border-radius:6px;">添加本地模型</button>
    </div>
    ${modelsHtml}
  `;

  window.openSubpage('模型管理', contentHtml, { showMore: false });

  setTimeout(() => {
    document.getElementById('add-api-key').addEventListener('click', openAddApiKeyForm);
    document.getElementById('add-local-model').addEventListener('click', openAddLocalModelForm);

    document.querySelectorAll('.edit-share-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const modelId = btn.dataset.modelId;
        const modelItem = btn.closest('.model-item');
        const isShared = modelItem.dataset.isShared === '1' ? 1 : 0;
        const visibility = modelItem.dataset.visibility;
        const price = parseFloat(modelItem.dataset.price);
        openShareSettings(modelId, isShared, visibility, isNaN(price) ? 0 : price);
      });
    });
  }, 100);
}

function openAddApiKeyForm() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">名称</span>
        <input type="text" id="api-name-input" class="inline-input" placeholder="例如：主用DeepSeek">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">供应商</span>
        <input type="text" id="api-provider-input" class="inline-input" placeholder="deepseek/openai/gpt/claude">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">API Key</span>
        <input type="password" id="api-key-input" class="inline-input" placeholder="sk-...">
      </div>
    </div>
    <button class="save-btn" id="save-api-key">保存</button>
  `;
  window.openSubpage('添加 API Key', contentHtml);

  setTimeout(() => {
    document.getElementById('save-api-key').addEventListener('click', async () => {
      const name = document.getElementById('api-name-input').value.trim();
      const provider = document.getElementById('api-provider-input').value.trim();
      const api_key = document.getElementById('api-key-input').value.trim();
      if (!name || !provider || !api_key) { alert('请填写完整'); return; }
      try {
        await api.addApiKey({ name, provider, api_key, priority: 1 });
        alert('添加成功');
        window.closeSubpage();
        openModelManagement();
      } catch (e) {
        alert('添加失败：' + e.message);
      }
    });
  }, 100);
}

function openAddLocalModelForm() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">名称</span>
        <input type="text" id="local-name-input" class="inline-input" placeholder="例如：家里的4090">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">节点URL</span>
        <input type="text" id="local-url-input" class="inline-input" placeholder="http://192.168.1.100:11434">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">模型名称</span>
        <input type="text" id="local-model-input" class="inline-input" placeholder="例如：tinyllama">
      </div>
    </div>
    <button class="save-btn" id="save-local-model">保存</button>
  `;
  window.openSubpage('添加本地模型', contentHtml);

  setTimeout(() => {
    document.getElementById('save-local-model').addEventListener('click', async () => {
      const name = document.getElementById('local-name-input').value.trim();
      const node_url = document.getElementById('local-url-input').value.trim();
      const model_name = document.getElementById('local-model-input').value.trim();
      if (!name || !node_url || !model_name) { alert('请填写完整'); return; }
      try {
        await api.addLocalModel({ name, node_url, model_name });
        alert('添加成功');
        window.closeSubpage();
        openModelManagement();
      } catch (e) {
        alert('添加失败：' + e.message);
      }
    });
  }, 100);
}

function openShareSettings(modelId, isShared, visibility, price) {
  const safePrice = isNaN(price) ? 0 : price;
  const visibilityMap = { 'private': '仅自己', 'friends': '仅好友', 'public': '公开' };
  const currentVisibilityText = visibilityMap[visibility] || visibility;

  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">允许共享</span>
        <label class="switch">
          <input type="checkbox" id="share-enabled" ${isShared ? 'checked' : ''}>
          <span class="slider"></span>
        </label>
      </div>
      <div class="me-menu-item" id="share-visibility-selector">
        <span class="menu-label">可见范围</span>
        <span class="menu-value" id="share-visibility-text">${currentVisibilityText}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-label">调用价格</span>
        <input type="number" id="share-price" class="inline-input" value="${safePrice}" min="0" step="0.5">
        <span class="menu-unit">积分/次</span>
      </div>
    </div>
    <button class="save-btn" id="save-share-settings">保存</button>
  `;
  window.openSubpage('共享设置', contentHtml, { showMore: false });

  setTimeout(() => {
    document.getElementById('share-visibility-selector').addEventListener('click', () => {
      const optionsHtml = `
        <div class="me-menu">
          <div class="me-menu-item visibility-option" data-value="private">仅自己</div>
          <div class="me-menu-item visibility-option" data-value="friends">仅好友</div>
          <div class="me-menu-item visibility-option" data-value="public">公开</div>
        </div>
      `;
      window.openSubpage('选择可见范围', optionsHtml, { showMore: false });
      setTimeout(() => {
        document.querySelectorAll('.visibility-option').forEach(opt => {
          opt.addEventListener('click', () => {
            const newValue = opt.dataset.value;
            document.getElementById('share-visibility-text').textContent = opt.textContent;
            document.getElementById('share-visibility-selector').dataset.value = newValue;
            window.closeSubpage();
          });
        });
      }, 100);
    });

    document.getElementById('save-share-settings').addEventListener('click', async () => {
      const enabled = document.getElementById('share-enabled').checked ? 1 : 0;
      const vis = document.getElementById('share-visibility-selector').dataset.value || 'private';
      const priceVal = parseFloat(document.getElementById('share-price').value) || 0;
      try {
        await api.updateModelShare(modelId, { is_shared: enabled, visibility: vis, price: priceVal });
        alert('保存成功');
        window.closeSubpage();
        openModelManagement();
      } catch (e) {
        alert('保存失败：' + e.message);
      }
    });
  }, 100);
}

// ==================== 积分中心 ====================
async function openWallet() {
  let balance = 0;
  let computePower = parseFloat(localStorage.getItem('sases_compute_power') || '0');
  let historyHtml = '';

  try {
    const balanceData = await api.getBalance();
    balance = balanceData.balance;
  } catch (e) {
    console.warn('获取种子积分失败', e);
  }

  try {
    const historyData = await api.getCreditHistory(20);
    const history = historyData.history || [];
    if (history.length === 0) {
      historyHtml = '<div class="subpage-placeholder">暂无积分记录</div>';
    } else {
      historyHtml = '<div class="me-menu">';
      history.forEach(item => {
        const date = new Date(item.created_at).toLocaleString('zh-CN');
        historyHtml += `
          <div class="me-menu-item">
            <span class="menu-label">${item.action || '积分变动'}</span>
            <span class="menu-value">${item.points > 0 ? '+' : ''}${item.points} 分</span>
          </div>
          <div style="padding:0 12px 8px;font-size:12px;color:#999;">${date}</div>
        `;
      });
      historyHtml += '</div>';
    }
  } catch (e) {
    historyHtml = '<div class="subpage-placeholder">加载失败</div>';
  }

  const contentHtml = `
    <div class="wallet-card" style="background: linear-gradient(135deg, #007aff, #00c6ff);">
      <div class="wallet-label">种子积分</div>
      <div class="wallet-balance">${balance}</div>
    </div>
    <div class="wallet-card" style="background: linear-gradient(135deg, #34c759, #b2df8a);">
      <div class="wallet-label">算力积分</div>
      <div class="wallet-balance">${computePower}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-exchange"><span class="menu-label">积分兑换</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="menu-stake"><span class="menu-label">积分质押</span><span class="menu-arrow">›</span></div>
    </div>
    <div class="section-title">最近记录</div>
    ${historyHtml}
  `;
  window.openSubpage('积分中心', contentHtml);

  setTimeout(() => {
    const exchangeMenu = document.getElementById('menu-exchange');
    const stakeMenu = document.getElementById('menu-stake');
    if (exchangeMenu) exchangeMenu.addEventListener('click', openExchangePage);
    if (stakeMenu) stakeMenu.addEventListener('click', openStakePage);
  }, 100);
}

function openExchangePage() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">积分数量</span>
        <input type="number" id="exchange-credits" class="inline-input" placeholder="输入积分">
      </div>
    </div>
    <button class="save-btn" id="save-exchange">确认兑换</button>
  `;
  window.openSubpage('积分兑换', contentHtml);
  setTimeout(() => {
    document.getElementById('save-exchange').addEventListener('click', async () => {
      const credits = parseFloat(document.getElementById('exchange-credits').value);
      if (!credits || credits <= 0) { alert('请输入有效积分数量'); return; }
      try {
        const data = await api.exchangeCredits(credits);
        const currentPower = parseFloat(localStorage.getItem('sases_compute_power') || '0');
        localStorage.setItem('sases_compute_power', (currentPower + data.compute_power).toString());
        alert(`兑换成功！获得 ${data.compute_power} 算力`);
        window.closeSubpage();
        openWallet();
      } catch (e) {
        alert('兑换失败：' + e.message);
      }
    });
  }, 100);
}

function openStakePage() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">积分数量</span>
        <input type="number" id="stake-credits" class="inline-input" placeholder="输入积分">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">质押时长（天）</span>
        <input type="number" id="stake-days" class="inline-input" value="30">
      </div>
    </div>
    <button class="save-btn" id="save-stake">确认质押</button>
  `;
  window.openSubpage('积分质押', contentHtml);
  setTimeout(() => {
    document.getElementById('save-stake').addEventListener('click', async () => {
      const credits = parseFloat(document.getElementById('stake-credits').value);
      const days = parseInt(document.getElementById('stake-days').value);
      if (!credits || credits <= 0 || !days || days <= 0) { alert('请输入有效数值'); return; }
      try {
        const data = await api.stakeCredits(credits, days);
        alert(`质押成功！预计收益 ${data.expected_reward.toFixed(2)} 积分`);
        window.closeSubpage();
        openWallet();
      } catch (e) {
        alert('质押失败：' + e.message);
      }
    });
  }, 100);
}

// ==================== 知识库 ====================
async function openKnowledgeBase() {
  let knowledgeHtml = '';
  try {
    const data = await api.listKnowledge();
    const knowledge = data.knowledge || [];
    if (knowledge.length === 0) {
      knowledgeHtml = '<div class="subpage-placeholder">暂无知识条目</div>';
    } else {
      knowledgeHtml = '<div class="me-menu">';
      knowledge.forEach(item => {
        const verifiedIcon = item.verified ? '✅' : '❌';
        knowledgeHtml += `
          <div class="me-menu-item">
            <span class="menu-icon">${verifiedIcon}</span>
            <div class="menu-text">
              <div class="menu-title">${item.task}</div>
              <div class="menu-desc">${item.solution.substring(0, 50)}...</div>
            </div>
          </div>
        `;
      });
      knowledgeHtml += '</div>';
    }
  } catch (e) {
    knowledgeHtml = '<div class="subpage-placeholder">加载失败</div>';
  }
  window.openSubpage('知识库', knowledgeHtml);
}

// ==================== 我的贡献 ====================
async function openContributions() {
  let contribHtml = '';
  try {
    const data = await api.getCreditHistory(50);
    const history = data.history || [];
    if (history.length === 0) {
      contribHtml = '<div class="subpage-placeholder">暂无贡献记录</div>';
    } else {
      contribHtml = '<div class="me-menu">';
      history.forEach(item => {
        const date = new Date(item.created_at).toLocaleString('zh-CN');
        contribHtml += `
          <div class="me-menu-item">
            <span class="menu-label">${item.action || '贡献'}</span>
            <span class="menu-value">${item.points > 0 ? '+' : ''}${item.points} 分</span>
          </div>
          <div style="padding:0 12px 8px;font-size:12px;color:#999;">${date} · ${item.detail || ''}</div>
        `;
      });
      contribHtml += '</div>';
    }
  } catch (e) {
    contribHtml = '<div class="subpage-placeholder">加载失败</div>';
  }
  window.openSubpage('我的贡献', contribHtml);
}

// ==================== 设置 ====================
function openSettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item" id="set-account"><span class="menu-label">账号与安全</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-pollination"><span class="menu-label">授粉计划</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-notify"><span class="menu-label">通知设置</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-privacy"><span class="menu-label">隐私</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-language"><span class="menu-label">语言设置</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-about"><span class="menu-label">关于 SASES</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-logout" style="justify-content:center;">
        <span class="menu-label" style="color:#ff3b30;">退出登录</span>
      </div>
    </div>
  `;
  window.openSubpage('设置', contentHtml);

  setTimeout(() => {
    document.getElementById('set-account').addEventListener('click', openAccountSettings);
    document.getElementById('set-pollination').addEventListener('click', openPollinationPlan);
    document.getElementById('set-notify').addEventListener('click', openNotificationSettings);
    document.getElementById('set-privacy').addEventListener('click', openPrivacySettings);
    document.getElementById('set-language').addEventListener('click', openLanguageSettings);
    document.getElementById('set-about').addEventListener('click', openAboutPage);
    document.getElementById('set-logout').addEventListener('click', () => {
      localStorage.removeItem('sases_token');
      localStorage.removeItem('sases_username');
      localStorage.removeItem('sases_user_id');
      localStorage.removeItem('sases_sas_id');
      localStorage.removeItem('sases_credits_cache');
      window.location.reload();
    });
  }, 100);
}

function openPollinationPlan() {
  const contentHtml = `
    <div style="padding:20px 16px;background:#fff;border-radius:8px;margin-bottom:12px;">
      <h3 style="margin-bottom:8px;">🌱 授粉计划</h3>
      <p style="color:#666;font-size:14px;line-height:1.6;">授粉是分享知识、获取积分的重要方式。当你贡献有价值的种子或数据时，你将获得积分奖励。</p>
    </div>
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">基础价值</span><span class="menu-value">+1 积分</span></div>
      <div class="me-menu-item"><span class="menu-label">专业领域价值</span><span class="menu-value">+2 积分</span></div>
      <div class="me-menu-item"><span class="menu-label">极高价值</span><span class="menu-value">+3 积分</span></div>
      <div class="me-menu-item"><span class="menu-label">本地模型加成</span><span class="menu-value">额外 +2 积分</span></div>
      <div class="me-menu-item"><span class="menu-label">每日个人授粉上限</span><span class="menu-value">100 积分</span></div>
      <div class="me-menu-item"><span class="menu-label">挑坏果子奖励</span><span class="menu-value">+5 积分/次（每日上限50）</span></div>
    </div>
    <div style="margin-top:12px;background:#f5f5f5;border-radius:8px;padding:12px;font-size:13px;color:#888;">
      群任务授粉分配：群主5%，算力提供者70%，执行者15%，红包池10%。具体规则以群设置为准。
    </div>
  `;
  window.openSubpage('授粉计划', contentHtml, { showMore: false });
}

function openAccountSettings() {
  const username = localStorage.getItem('sases_username') || '用户';
  const sasesId = localStorage.getItem('sases_sas_id') || '未设置';
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">用户名</span><span class="menu-value">${username}</span></div>
      <div class="me-menu-item"><span class="menu-label">SASES ID</span><span class="menu-value">${sasesId}</span></div>
      <div class="me-menu-item" id="account-change-password"><span class="menu-label">修改密码</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="account-logout-devices"><span class="menu-label">登录设备管理</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage('账号与安全', contentHtml);
  setTimeout(() => {
    document.getElementById('account-change-password').addEventListener('click', () => alert('修改密码功能待实现'));
    document.getElementById('account-logout-devices').addEventListener('click', () => alert('登录设备管理待实现'));
  }, 100);
}

function openNotificationSettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">接收新消息通知</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">智能体动态通知</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">积分变动通知</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">悬赏任务通知</span><label class="switch"><input type="checkbox"><span class="slider"></span></label></div>
    </div>
  `;
  window.openSubpage('通知设置', contentHtml);
}

function openPrivacySettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">谁可以看到我的智能体</span><span class="menu-value">仅好友</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item"><span class="menu-label">谁可以搜索到我</span><span class="menu-value">所有人</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="privacy-export-data"><span class="menu-label">导出我的数据</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="privacy-delete-data"><span class="menu-label">删除云端数据</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage('隐私', contentHtml);
  setTimeout(() => {
    document.getElementById('privacy-export-data').addEventListener('click', async () => {
      try {
        const data = await api.exportUserData();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'sases_data.json';
        a.click();
        URL.revokeObjectURL(url);
        alert('导出成功，文件已下载');
      } catch (e) {
        alert('导出失败：' + e.message);
      }
    });
    document.getElementById('privacy-delete-data').addEventListener('click', async () => {
      if (!confirm('确定要删除您的云端公开数据吗？此操作不可恢复。')) return;
      try {
        await api.deleteUserCloudData();
        alert('已删除云端数据');
      } catch (e) {
        alert('删除失败：' + e.message);
      }
    });
  }, 100);
}

function openLanguageSettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item" id="lang-zh"><span class="menu-label">简体中文</span><span class="menu-check">✓</span></div>
      <div class="me-menu-item" id="lang-en"><span class="menu-label">English</span><span class="menu-check"></span></div>
    </div>
  `;
  window.openSubpage('语言设置', contentHtml);
  setTimeout(() => {
    document.getElementById('lang-zh').addEventListener('click', () => {
      localStorage.setItem('sases_lang', 'zh');
      alert('已切换为简体中文');
    });
    document.getElementById('lang-en').addEventListener('click', () => {
      localStorage.setItem('sases_lang', 'en');
      alert('Switched to English');
    });
  }, 100);
}

function openAboutPage() {
  const contentHtml = `
    <div style="text-align:center;padding:30px 20px;">
      <div style="font-size:40px;margin-bottom:16px;">🌱</div>
      <div style="font-size:20px;font-weight:600;">SASES</div>
      <div style="color:#888;font-size:14px;margin-top:8px;">版本 v0.12.1</div>
      <div style="color:#888;font-size:13px;margin-top:4px;">隐私优先的自进化 AI 生态</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="about-docs"><span class="menu-label">开发文档</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="about-license"><span class="menu-label">开源许可</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="about-feedback"><span class="menu-label">反馈建议</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage('关于 SASES', contentHtml);
  setTimeout(() => {
    document.getElementById('about-docs').addEventListener('click', () => window.openSubpage('开发文档', '<div class="subpage-placeholder">文档待补充</div>'));
    document.getElementById('about-license').addEventListener('click', () => window.openSubpage('开源许可', '<div class="subpage-placeholder">MIT License</div>'));
    document.getElementById('about-feedback').addEventListener('click', () => window.openSubpage('反馈建议', '<div class="subpage-placeholder">反馈渠道待实现</div>'));
  }, 100);
}

// 导出全局
window.openModelManagement = openModelManagement;
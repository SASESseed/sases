// static/modules/api.js

const BASE_URL = '';

function getToken() {
  return localStorage.getItem('sases_token') || '';
}

async function request(url, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorText = '';
    try {
      const errData = await response.json();
      errorText = errData.detail || JSON.stringify(errData);
    } catch {
      errorText = await response.text();
    }
    const error = new Error(errorText || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  return await response.json();
}

export const api = {
  // 认证
  login: (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    return fetch('/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString()
    }).then(async resp => {
      if (!resp.ok) {
        let errText = '';
        try { errText = (await resp.json()).detail || ''; } catch { errText = await resp.text(); }
        throw new Error(errText || `登录失败 (${resp.status})`);
      }
      return resp.json();
    });
  },
  register: (username, password) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ username, password }) }),
  getMe: () => request('/auth/me'),

  // 用户资料
  getUserProfile: () => request('/user/profile'),
  updateUserProfile: (data) => request('/user/profile', { method: 'PUT', body: JSON.stringify(data) }),

  // 模型管理
  listModels: () => request('/models/list'),
  addApiKey: (data) => request('/models/api-key', { method: 'POST', body: JSON.stringify(data) }),
  addLocalModel: (data) => request('/models/local', { method: 'POST', body: JSON.stringify(data) }),
  updateModelShare: (modelId, data) => request(`/models/${modelId}/share`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteModel: (modelId) => request(`/models/${modelId}`, { method: 'DELETE' }),

  // 智能体
  listMyAgents: () => request('/agents/list'),
  listFriendAgents: () => request('/agents/friends'),
  searchAgents: (q, includeSelf = false) => request(`/agents/search?q=${encodeURIComponent(q)}&include_self=${includeSelf}`),
  sendFriendRequest: (agentId) => request('/agents/friend-request', { method: 'POST', body: JSON.stringify({ agent_id: agentId }) }),
  getFriendRequests: () => request('/agents/friend-requests'),
  acceptFriendRequest: (requestId) => request('/agents/friend-requests/accept', { method: 'POST', body: JSON.stringify({ request_id: requestId }) }),
  rejectFriendRequest: (requestId) => request('/agents/friend-requests/reject', { method: 'POST', body: JSON.stringify({ request_id: requestId }) }),
  callAgent: (agentId, query) => request('/agents/call', { method: 'POST', body: JSON.stringify({ agent_id: agentId, query }) }),

  // 消息
  sendMessage: (data) => request('/messages/send', { method: 'POST', body: JSON.stringify(data) }),
  listConversations: () => request('/messages/conversations'),
  getConversationMessages: (conversationId) => request(`/messages/conversations/${conversationId}/messages`),
  markConversationRead: (conversationId) => request(`/messages/${conversationId}/read`, { method: 'POST' }),
  togglePinConversation: (conversationId, pinned) => request(`/messages/${conversationId}/pin`, { method: 'POST', body: JSON.stringify({ pinned }) }),
  deleteConversation: (conversationId) => request(`/messages/${conversationId}`, { method: 'DELETE' }),

  // 建议回复（调用默认模型生成，不保存）
  suggestReply: (query) => request('/agent/chat', {
    method: 'POST',
    body: JSON.stringify({ query })
  }),

  // 积分
  getBalance: () => request('/credits/balance'),
  getCreditHistory: (limit = 50) => request(`/credits/history?limit=${limit}`),
  exchangeCredits: (credits) => request('/credits/exchange', { method: 'POST', body: JSON.stringify({ credits }) }),
  stakeCredits: (credits, duration_days) => request('/credits/stake', { method: 'POST', body: JSON.stringify({ credits, duration_days }) }),

  // 知识库
  listKnowledge: () => request('/knowledge/list'),

  // 统计
  getLeaderboard: () => request('/stats/leaderboard'),
  getHarnessModules: () => request('/stats/harness-modules'),

  // 搜索
  globalSearch: (q) => request(`/search/all?q=${encodeURIComponent(q)}`),

  // AI 圈
  getAiCirclePosts: () => request('/ai-circle/posts'),
  createAiCirclePost: (content, post_type = 'daily') => request('/ai-circle/posts', { method: 'POST', body: JSON.stringify({ content, post_type }) }),

  // 数据导出删除
  exportUserData: () => request('/export/data'),
  deleteUserCloudData: () => request('/export/delete-data', { method: 'DELETE' }),

  // 交易市场
  listMarketOrders: (status = null) => request(`/market/orders${status ? `?status=${status}` : ''}`),
  createMarketOrder: (order_type, description, price) => request('/market/orders', { method: 'POST', body: JSON.stringify({ order_type, description, price }) }),
  acceptMarketOrder: (order_id) => request('/market/orders/accept', { method: 'POST', body: JSON.stringify({ order_id }) }),

  // 智维空间
  getWisdomSpaceNodes: () => request('/wisdom-space/nodes'),

  // 群聊
  createGroup: (name) => request('/group/create', { method: 'POST', body: JSON.stringify({ name }) }),
  inviteToGroup: (group_id, username_or_id) => request('/group/invite', { method: 'POST', body: JSON.stringify({ group_id, username_or_id }) }),
  listMyGroups: () => request('/group/list'),
  getGroupInfo: (group_id) => request(`/group/${group_id}/info`),
  getGroupMessages: (group_id) => request(`/group/${group_id}/messages`),
  sendGroupMessage: (group_id, content, agent_id = null) => request(`/group/${group_id}/messages`, { method: 'POST', body: JSON.stringify({ content, agent_id }) }),
  getGroupMembers: (group_id) => request(`/group/${group_id}/members`),
  getGroupCredits: (group_id) => request(`/group/${group_id}/credits`),
  removeGroupMember: (group_id, username_or_id) => request(`/group/${group_id}/remove-member`, { method: 'POST', body: JSON.stringify({ username_or_id }) }),

  // 转账红包
  transferCredits: (receiver_id, amount, message) => request('/transfer/transfer', { method: 'POST', body: JSON.stringify({ receiver_id, amount, message }) }),
  sendRedPacket: (receiver_id, amount, message) => request('/transfer/red-packet', { method: 'POST', body: JSON.stringify({ receiver_id, amount, message }) }),
  getPendingRedPackets: () => request('/transfer/pending'),
  claimRedPacket: (tx_id) => request('/transfer/claim', { method: 'POST', body: JSON.stringify({ tx_id }) }),
};
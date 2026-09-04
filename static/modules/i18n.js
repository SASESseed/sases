// static/modules/i18n.js
const translations = {
  zh: {
    'message': '消息',
    'contacts': '智能体',
    'discover': '发现',
    'me': '我的',
    'settings': '设置',
    'logout': '退出登录',
    'model_management': '模型管理',
    'credits_center': '积分中心',
    'knowledge_base': '知识库',
    'my_contributions': '我的贡献',
    'free_mode': '自由模式',
    'domain_mode': '领域模式',
    'proposition_mode': '命题模式',
    'normal_chat': '普通聊天',
    'task_mode': '任务模式',
    'add_agent': '添加智能体',
    'new_agent': '新智能体',
    'group_chat': '群聊',
    'send': '发送',
    'input_placeholder': '输入消息...',
    'pollination_plan': '授粉计划',
    'language_settings': '语言设置',
    'about_sases': '关于 SASES',
    // ... 更多文本
  },
  en: {
    'message': 'Messages',
    'contacts': 'Agents',
    'discover': 'Discover',
    'me': 'Me',
    'settings': 'Settings',
    'logout': 'Log Out',
    'model_management': 'Model Management',
    'credits_center': 'Credits Center',
    'knowledge_base': 'Knowledge Base',
    'my_contributions': 'My Contributions',
    'free_mode': 'Free Mode',
    'domain_mode': 'Domain Mode',
    'proposition_mode': 'Proposition Mode',
    'normal_chat': 'Normal Chat',
    'task_mode': 'Task Mode',
    'add_agent': 'Add Agent',
    'new_agent': 'New Agent',
    'group_chat': 'Group Chat',
    'send': 'Send',
    'input_placeholder': 'Type a message...',
    'pollination_plan': 'Pollination Plan',
    'language_settings': 'Language Settings',
    'about_sases': 'About SASES',
    // ... 更多文本
  }
};

let currentLang = localStorage.getItem('sases_lang') || 'zh';

export function t(key) {
  return translations[currentLang][key] || key;
}

export function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('sases_lang', lang);
}
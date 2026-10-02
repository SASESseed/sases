async function openGroupLeaderboard() {
  const tabs = [
    { key: 'contribution', label: '贡献榜' },
    { key: 'task', label: '任务榜' },
    { key: 'redpacket', label: '红包榜' }
  ];
  let currentType = 'contribution';
  let cache = {};

  const renderList = (items) => {
    if (!items || items.length === 0) {
      return '<div style="text-align:center;color:#999;padding:40px 0;">暂无数据</div>';
    }
    let html = '<div style="padding:8px 12px;">';
    items.forEach((it, idx) => {
      const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : (idx + 1) + '';
      html += '<div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #f5f5f5;">';
      html += '<div style="width:36px;text-align:center;font-size:' + (idx < 3 ? '20px' : '14px') + ';color:' + (idx < 3 ? '#333' : '#999') + ';">' + medal + '</div>';
      html += '<div style="flex:1;margin-left:12px;font-size:14px;color:#333;">' + (it.username || '匿名') + '</div>';
      html += '<div style="font-size:14px;color:#f59e0b;font-weight:600;">' + (it.score || 0) + '</div>';
      html += '</div>';
    });
    html += '</div>';
    return html;
  };

  const loadData = async (type) => {
    if (cache[type]) return cache[type];
    try {
      const resp = await fetch('/group/' + currentGroupId + '/leaderboard?type=' + type, {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      });
      const data = await resp.json();
      cache[type] = data.leaderboard || [];
      return cache[type];
    } catch (e) {
      return [];
    }
  };

  const renderTabs = () => {
    return tabs.map(t =>
      '<div class="lb-tab" data-type="' + t.key + '" style="flex:1;text-align:center;padding:10px 0;font-size:14px;cursor:pointer;">' + t.label + '</div>'
    ).join('');
  };

  const renderPage = async () => {
    const items = await loadData(currentType);
    const contentHtml = `
      <div>
        <div style="display:flex;border-bottom:1px solid #eee;background:#fff;">${renderTabs()}</div>
        <div id="lb-list">${renderList(items)}</div>
      </div>
    `;
    window.openSubpage('群排行榜', contentHtml, { showMore: false });
    setTimeout(() => {
      document.querySelectorAll('.lb-tab').forEach(el => {
        const t = el.dataset.type;
        const active = t === currentType;
        el.style.color = active ? '#007aff' : '#666';
        el.style.fontWeight = active ? '600' : '400';
        el.style.borderBottom = active ? '2px solid #007aff' : 'none';
        el.onclick = async () => {
          currentType = t;
          const newItems = await loadData(t);
          document.getElementById('lb-list').innerHTML = renderList(newItems);
          document.querySelectorAll('.lb-tab').forEach(e => {
            const tt = e.dataset.type;
            const a = tt === currentType;
            e.style.color = a ? '#007aff' : '#666';
            e.style.fontWeight = a ? '600' : '400';
            e.style.borderBottom = a ? '2px solid #007aff' : 'none';
          });
        };
      });
    }, 100);
  };

  await renderPage();
}
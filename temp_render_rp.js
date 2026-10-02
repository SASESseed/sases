export function renderGroupRedPacketBubble(content) {
  let data = {};
  try { data = JSON.parse(content.substring(13)); } catch (e) {}
  const isPool = data.source_type === 'group_pool';
  const div = document.createElement('div');
  div.className = 'group-red-packet-bubble';
  const bg = isPool
    ? 'linear-gradient(135deg,#8b5cf6,#6366f1)'
    : 'linear-gradient(135deg,#f59e0b,#ef4444)';
  div.style.cssText = 'background:' + bg + ';color:#fff;padding:12px 16px;border-radius:12px;cursor:pointer;min-width:220px;';
  div.dataset.packetId = data.packet_id || '';
  const t1 = document.createElement('div');
  t1.style.fontSize = '13px';
  t1.style.opacity = '0.9';
  t1.textContent = isPool ? '🎁 群福利红包' : '🧧 群红包';
  div.appendChild(t1);
  const t2 = document.createElement('div');
  t2.style.fontSize = '20px';
  t2.style.fontWeight = '700';
  t2.style.marginTop = '4px';
  t2.textContent = (data.total_amount || 0) + ' 积分';
  div.appendChild(t2);
  const t3 = document.createElement('div');
  t3.style.fontSize = '12px';
  t3.style.opacity = '0.85';
  t3.style.marginTop = '4px';
  t3.textContent = '共 ' + (data.total_count || 0) + ' 份' + (isPool ? ' · 群池出资' : '');
  div.appendChild(t3);
  if (data.message) {
    const t4 = document.createElement('div');
    t4.style.fontSize = '12px';
    t4.style.opacity = '0.85';
    t4.style.marginTop = '4px';
    t4.textContent = data.message;
    div.appendChild(t4);
  }
  div.onclick = function() {
    if (typeof window.openGroupRedPacket === 'function') window.openGroupRedPacket(data.packet_id);
  };
  return div;
}
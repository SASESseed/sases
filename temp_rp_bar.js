async function loadGroupRedPackets() {
  if (!currentGroupId) return;
  try {
    const data = await api.getActiveGroupRedPackets(currentGroupId);
    const packets = (data && data.packets) || [];
    const bar = document.getElementById('group-red-packet-bar');
    const text = document.getElementById('group-red-packet-bar-text');
    if (!bar || !text) return;
    if (packets.length === 0) {
      bar.style.display = 'none';
      return;
    }
    text.textContent = '🧧 待抢红包 (' + packets.length + ')';
    bar.style.display = 'flex';
    bar.onclick = function() {
      openRedPacketListPage(packets);
    };
  } catch (e) {
    console.log('loadGroupRedPackets error:', e);
  }
}

function openRedPacketListPage(packets) {
  let html = '<div style="padding:12px;">';
  packets.forEach(p => {
    const isPool = p.source_type === 'group_pool';
    const title = isPool ? '🎁 群福利红包' : '🧧 群红包';
    html += '<div class="rp-list-item" data-pid="' + p.id + '" style="border:1px solid #eee;border-radius:8px;padding:12px;margin-bottom:10px;cursor:pointer;background:' + (isPool ? '#f5f3ff' : '#fff7ed') + ';">';
    html += '<div style="font-size:15px;font-weight:600;margin-bottom:4px;">' + title + '</div>';
    html += '<div style="font-size:12px;color:#666;">' + (p.total_amount || 0) + ' 积分 · 已抢 ' + (p.claimed_count || 0) + '/' + (p.total_count || 0) + '</div>';
    if (p.message) {
      html += '<div style="font-size:12px;color:#999;margin-top:4px;">' + p.message + '</div>';
    }
    html += '</div>';
  });
  html += '</div>';
  window.openSubpage('待抢红包', html);
  setTimeout(function() {
    document.querySelectorAll('.rp-list-item').forEach(el => {
      el.onclick = function() {
        if (typeof window.openGroupRedPacket === 'function') window.openGroupRedPacket(parseInt(el.dataset.pid));
      };
    });
  }, 100);
}
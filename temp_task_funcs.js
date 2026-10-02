async function loadGroupTasks() {
  if (!currentGroupId) return;
  try {
    const data = await api.getGroupTasks(currentGroupId, 'open');
    const tasks = data.tasks || [];
    const bar = document.getElementById('group-task-bar');
    const text = document.getElementById('group-task-bar-text');
    if (!bar || !text) return;
    if (tasks.length === 0) {
      bar.style.display = 'none';
      return;
    }
    text.textContent = '进行中任务 (' + tasks.length + ')';
    bar.style.display = 'flex';
    bar.onclick = function() {
      openTaskListPage(tasks);
    };
  } catch (e) {
    console.log('loadGroupTasks error:', e);
  }
}

function openTaskListPage(tasks) {
  let html = '<div style="padding:12px;">';
  tasks.forEach(t => {
    html += '<div class="task-list-item" data-tid="' + t.id + '" style="border:1px solid #eee;border-radius:8px;padding:12px;margin-bottom:10px;cursor:pointer;">';
    html += '<div style="font-size:15px;font-weight:600;margin-bottom:4px;">' + (t.title || '未命名') + '</div>';
    html += '<div style="font-size:12px;color:#666;">质押 ' + (t.reward_credits || 0) + ' 积分 · ' + (t.task_category || 'text') + '</div>';
    html += '</div>';
  });
  html += '</div>';
  window.openSubpage('进行中任务', html);
  setTimeout(function() {
    document.querySelectorAll('.task-list-item').forEach(el => {
      el.onclick = function() {
        if (typeof window.openTaskDetail === 'function') window.openTaskDetail(parseInt(el.dataset.tid));
      };
    });
  }, 100);
}
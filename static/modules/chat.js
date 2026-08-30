import { showToast, apiFetch, token } from './utils.js';

let selectedImageBase64 = null;
let selectedAudioBase64 = null;
let selectedVideoBase64 = null;

export function initChat() {
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) sendBtn.addEventListener('click', chat);

    const imageBtn = document.getElementById('image-btn');
    if (imageBtn) imageBtn.addEventListener('click', () => document.getElementById('chat-image').click());
    const audioBtn = document.getElementById('audio-btn');
    if (audioBtn) audioBtn.addEventListener('click', () => document.getElementById('chat-audio').click());
    const videoBtn = document.getElementById('video-btn');
    if (videoBtn) videoBtn.addEventListener('click', () => document.getElementById('chat-video').click());

    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chat();
            }
        });
    }

    // 绑定文件选择
    document.getElementById('chat-image').addEventListener('change', handleImageSelect);
    document.getElementById('chat-audio').addEventListener('change', handleAudioSelect);
    document.getElementById('chat-video').addEventListener('change', handleVideoSelect);
}

function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
        showToast('图片大小不能超过 5MB', 'error');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
        selectedImageBase64 = e.target.result.split(',')[1];
        document.getElementById('image-preview').innerHTML = `
            <div style="display:flex; align-items:center;">
                <img src="data:image/jpeg;base64,${selectedImageBase64}" style="max-width:80px; max-height:80px; margin-right:5px;" />
                <button id="remove-image-btn" style="margin-left:5px;">移除</button>
            </div>`;
        document.getElementById('remove-image-btn').addEventListener('click', () => clearSelectedFile('image'));
        event.target.value = '';
    };
    reader.readAsDataURL(file);
}

function handleAudioSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
        showToast('音频大小不能超过 10MB', 'error');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
        selectedAudioBase64 = e.target.result.split(',')[1];
        showToast('已选择音频：' + file.name, 'info');
        event.target.value = '';
    };
    reader.readAsDataURL(file);
}

function handleVideoSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 25 * 1024 * 1024) {
        showToast('视频大小不能超过 25MB', 'error');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
        selectedVideoBase64 = e.target.result.split(',')[1];
        showToast('已选择视频：' + file.name, 'info');
        event.target.value = '';
    };
    reader.readAsDataURL(file);
}

function clearSelectedFile(type) {
    if (type === 'image') {
        selectedImageBase64 = null;
        document.getElementById('image-preview').innerHTML = '';
    } else if (type === 'audio') {
        selectedAudioBase64 = null;
    } else if (type === 'video') {
        selectedVideoBase64 = null;
    }
}

async function chat() {
    const query = document.getElementById('chat-input').value.trim();
    const image = selectedImageBase64;
    const audio = selectedAudioBase64;
    const video = selectedVideoBase64;

    if (!query && !image && !audio && !video) {
        showToast('请输入问题或选择文件', 'error');
        return;
    }

    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    sendBtn.textContent = '发送中...';
    document.getElementById('chat-loading').style.display = 'flex';
    document.getElementById('chat-error').style.display = 'none';

    const payload = { query };
    if (image) payload.image = image;
    if (audio) payload.audio = audio;
    if (video) payload.video = video;

    try {
        const data = await apiFetch('/chat', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        document.getElementById('chat-result').textContent = data.answer;
        clearSelectedFile('image');
        clearSelectedFile('audio');
        clearSelectedFile('video');
        if (data.deducted) {
            showToast(`本次查询已扣除 ${data.deducted} 积分`, 'info');
            document.dispatchEvent(new CustomEvent('sases-credits-updated'));
        }
    } catch (e) {
        document.getElementById('chat-error').textContent = e.message;
        document.getElementById('chat-error').style.display = 'block';
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = '发送';
        document.getElementById('chat-loading').style.display = 'none';
    }
}
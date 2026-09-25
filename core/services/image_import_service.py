"""图片导入知识库服务"""
from datetime import datetime


def extract_text_from_image(image_url):
    import os, base64, openai
    from .. import config
    try:
        fn = (image_url or '').split('/')[-1]
        if not fn:
            return None
        fp = os.path.join('uploads', fn)
        if not os.path.exists(fp):
            return None
        with open(fp, 'rb') as f:
            raw = f.read()
        low = fn.lower()
        mime = 'image/png'
        if low.endswith('.jpg') or low.endswith('.jpeg'):
            mime = 'image/jpeg'
        elif low.endswith('.gif'):
            mime = 'image/gif'
        elif low.endswith('.webp'):
            mime = 'image/webp'
        b64s = base64.b64encode(raw).decode()
        cli = openai.OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL, timeout=60)
        r = cli.chat.completions.create(
            model=config.VISION_MODEL_NAME,
            messages=[{'role': 'user', 'content': [
                {'type': 'text', 'text': '请完整提取这张图片中的所有文字内容，保留排版结构。只输出文字，不要任何说明。'},
                {'type': 'image_url', 'image_url': {'url': 'data:' + mime + ';base64,' + b64s}}
            ]}],
            max_tokens=4000
        )
        msg = r.choices[0].message
        txt = (msg.content or '').strip()
        if not txt:
            rc = getattr(msg, 'reasoning_content', None) or ''
            txt = rc.strip()
        return txt or None
    except Exception as e:
        print('[image_import] 提取失败: ' + str(e))
        return None


def import_image_to_kb(image_url, user_id):
    from . import project_service
    txt = extract_text_from_image(image_url)
    if not txt:
        return {'success': False, 'error': '图片识别失败或未提取到文字'}
    src = '图片导入_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.md'
    try:
        n = project_service.import_document(src, 'v1.0-image', txt, user_id=user_id)
    except Exception as e:
        return {'success': False, 'error': str(e)}
    if n > 0:
        return {'success': True, 'chunks': n, 'source': src}
    return {'success': False, 'error': '图片文字重复或未新增'
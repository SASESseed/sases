import base64
import json
import httpx
from ...db import db_cursor
from .model_call import call_model_with_config

def _enrich_attachment(content):
    """[IMAGE]:/[FILE]: 消息 → 附加内容描述，供模型理解"""
    import os as _os, base64 as _b64, glob as _glob
    try:
        _prefix, _rest = content.split(':', 1)
        # support [FILE]:/uploads/xxx|filename|size
        _rel = _rest.split('|')[0].strip().lstrip('/')
    except Exception:
        return content
    _root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    _abs = _os.path.join(_root, _rel)
    if not _os.path.exists(_abs):
        return content + ' (文件不存在)'
    if content.startswith('[FILE]:'):
        try:
            _txt = open(_abs, 'r', encoding='utf-8', errors='replace').read(5000)
            return '[用户发了一个文件 ' + _rel + '，内容如下]' + chr(10) + _txt
        except Exception as _e:
            return content + ' (读文件失败: ' + str(_e) + ')'
    if content.startswith('[IMAGE]:'):
        try:
            from ... import config as _cfg
            import openai as _oai
            _raw = open(_abs, 'rb').read()
            if len(_raw) > 4 * 1024 * 1024:
                return content + ' (图片过大)'
            _mime = 'image/png'
            _low = _rel.lower()
            if _low.endswith('.jpg') or _low.endswith('.jpeg'):
                _mime = 'image/jpeg'
            elif _low.endswith('.gif'):
                _mime = 'image/gif'
            elif _low.endswith('.webp'):
                _mime = 'image/webp'
            _b64s = _b64.b64encode(_raw).decode()
            _cli = _oai.OpenAI(api_key=_cfg.DEEPSEEK_API_KEY, base_url=_cfg.DEEPSEEK_BASE_URL, timeout=30)
            _r = _cli.chat.completions.create(
                model=_cfg.VISION_MODEL_NAME,
                messages=[{'role': 'user', 'content': [
                    {'type': 'text', 'text': '用 100 字以内描述这张图片的内容、文字、场景。'},
                    {'type': 'image_url', 'image_url': {'url': 'data:' + _mime + ';base64,' + _b64s}}
                ]}],
                max_tokens=300
            )
            _desc = (_r.choices[0].message.content or '').strip()
            if not _desc:
                _rc = getattr(_r.choices[0].message, 'reasoning_content', None) or ''
                _desc = _rc.strip()[:200]
            return '[用户发了一张图片] 图片描述：' + _desc
        except Exception as _e:
            print('[message] vision API 失败: ' + str(_e))
            return content + ' (vision 分析失败)'
    return content


def _extract_text_from_image(image_url):
    """Extract full text from an image for KB import."""
    import os as _os_x, base64 as _b64_x, openai as _oai_x
    from ... import config as _cfg_x
    try:
        _fn = (image_url or '').split('/')[-1]
        if not _fn:
            return None
        _fp = _os_x.path.join('uploads', _fn)
        if not _os_x.path.exists(_fp):
            return None
        with open(_fp, 'rb') as _f:
            _raw = _f.read()
        _low = _fn.lower()
        _mime = 'image/png'
        if _low.endswith('.jpg') or _low.endswith('.jpeg'):
            _mime = 'image/jpeg'
        elif _low.endswith('.gif'):
            _mime = 'image/gif'
        elif _low.endswith('.webp'):
            _mime = 'image/webp'
        _b64s = _b64_x.b64encode(_raw).decode()
        _cli = _oai_x.OpenAI(api_key=_cfg_x.DEEPSEEK_API_KEY, base_url=_cfg_x.DEEPSEEK_BASE_URL, timeout=60)
        _r = _cli.chat.completions.create(
            model=_cfg_x.VISION_MODEL_NAME,
            messages=[{'role': 'user', 'content': [
                {'type': 'text', 'text': '请完整提取这张图片中的所有文字内容，保留排版结构。只输出文字，不要任何说明。'},
                {'type': 'image_url', 'image_url': {'url': 'data:' + _mime + ';base64,' + _b64s}}
            ]}],
            max_tokens=4000
        )
        _msg = _r.choices[0].message
        _txt = (_msg.content or '').strip()
        if not _txt:
            _rc = getattr(_msg, 'reasoning_content', None) or ''
            _txt = _rc.strip()
        return _txt or None
    except Exception as _e_x:
        print('[message] 提取图片文字失败: ' + str(_e_x))
        return None



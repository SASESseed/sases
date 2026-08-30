import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-v4-flash")

# 视觉模型
VISION_MODEL_NAME = os.environ.get("VISION_MODEL_NAME", "deepseek-v4-flash-vision-exp")
VISION_MODEL_BY_PROVIDER = {
    "deepseek": {"model": "deepseek-v4-flash-vision-exp", "supports_image": True},
    "openai": {"model": "gpt-4o-mini", "supports_image": True},
    "moonshot": {"model": "", "supports_image": False},
    "zhipu": {"model": "glm-4v", "supports_image": True},
    "qwen": {"model": "qwen-vl-plus", "supports_image": True},
}

# 音频识别模型（Whisper 等）
AUDIO_MODEL_BY_PROVIDER = {
    "openai": "whisper-1",
    "deepseek": "",
    "moonshot": "",
    "zhipu": "",
    "qwen": "",
}

# 视频理解模型（通常先抽帧再调用视觉模型）
VIDEO_MODEL_BY_PROVIDER = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-v4-flash-vision-exp",
    "moonshot": "",
    "zhipu": "glm-4v",
    "qwen": "qwen-vl-plus",
}

# 文件大小限制
MAX_IMAGE_SIZE = int(os.environ.get("MAX_IMAGE_SIZE", 5 * 1024 * 1024))
MAX_AUDIO_SIZE = int(os.environ.get("MAX_AUDIO_SIZE", 10 * 1024 * 1024))
MAX_VIDEO_SIZE = int(os.environ.get("MAX_VIDEO_SIZE", 25 * 1024 * 1024))

# 其他配置保持不变...

import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-v4-flash")

# 视觉模型配置
VISION_MODEL_NAME = os.environ.get("VISION_MODEL_NAME", "deepseek-v4-flash-vision-exp")
VISION_MODEL_BY_PROVIDER = {
    "deepseek": {"model": "deepseek-v4-flash-vision-exp", "supports_image": True},
    "openai": {"model": "gpt-4o-mini", "supports_image": True},
    "moonshot": {"model": "", "supports_image": False},
    "zhipu": {"model": "glm-4v", "supports_image": True},
    "qwen": {"model": "qwen-vl-plus", "supports_image": True},
}
AUDIO_MODEL_BY_PROVIDER = {
    "openai": "whisper-1",
    "deepseek": "",
    "moonshot": "",
    "zhipu": "",
    "qwen": "",
}
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

# 提供商映射
PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}
PROVIDER_ALIASES = {
    "ds": "deepseek",
    "deepseek-chat": "deepseek",
    "gpt": "openai",
    "openai-chat": "openai",
    "moonshot-v1": "moonshot",
    "kimi": "moonshot",
    "glm": "zhipu",
    "chatglm": "zhipu",
    "qwen-turbo": "qwen",
    "tongyi": "qwen",
}

# 安全与密钥
SASES_SECRET_KEY = os.environ.get("SASES_SECRET_KEY", "sases-dev-secret-key")
SIGN_KEY_FILE = os.environ.get("SIGN_KEY_FILE", "secret_key.bin")
API_KEY_ENCRYPTION_KEY_FILE = os.environ.get("API_KEY_ENCRYPTION_KEY_FILE", "api_key_encryption.key")
NODE_TOKEN = os.environ.get("SASES_NODE_TOKEN", "")

# 数据库文件
DB_FILE = os.environ.get("DB_FILE", "users.db")
KB_FILE = os.environ.get("KB_FILE", "success_kb.json")
SEED_POOL_FILE = os.environ.get("SEED_POOL_FILE", "seed_tasks_external.jsonl")
MAIN_SEED_FILE = os.environ.get("MAIN_SEED_FILE", "seed_tasks_new.jsonl")
SHARED_LOG_FILE = os.environ.get("SHARED_LOG_FILE", "shared_pollinate_log.jsonl")
CONTRIBUTION_LOG_DB = os.environ.get("CONTRIBUTION_LOG_DB", "users.db")

# 相似度与积分
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.30"))
EXTERNAL_SEED_REWARD = int(os.environ.get("EXTERNAL_SEED_REWARD", "5"))
MANUAL_POLLINATE_BASIC_REWARD = int(os.environ.get("MANUAL_POLLINATE_BASIC_REWARD", "3"))
MANUAL_POLLINATE_EXPERT_REWARD = int(os.environ.get("MANUAL_POLLINATE_EXPERT_REWARD", "10"))
QUERY_DEDUCTION = int(os.environ.get("QUERY_DEDUCTION", "2"))

# 节点相关
NODE_ID = os.environ.get("SASES_NODE_ID", "node-001")
NODE_NAME = os.environ.get("SASES_NODE_NAME", "SASES Node")
PEER_NODES = [x.strip() for x in os.environ.get("SASES_PEERS", "").split(",") if x.strip()]

# mDNS 发现（新增）
ENABLE_MDNS = os.environ.get("SASES_ENABLE_MDNS", "false").lower() == "true"
MDNS_SERVICE_TYPE = "_sases._tcp.local."

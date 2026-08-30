import os

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-v4-flash")

# SASES JWT 密钥
SASES_SECRET_KEY = os.environ.get("SASES_SECRET_KEY", "sases-dev-secret-key")

# 状态签名密钥文件
SIGN_KEY_FILE = os.environ.get("SIGN_KEY_FILE", "secret_key.bin")

# 数据库与知识库文件
DB_FILE = os.environ.get("DB_FILE", "users.db")
KB_FILE = os.environ.get("KB_FILE", "success_kb.json")
SEED_POOL_FILE = os.environ.get("SEED_POOL_FILE", "seed_tasks_external.jsonl")
MAIN_SEED_FILE = os.environ.get("MAIN_SEED_FILE", "seed_tasks_new.jsonl")
SHARED_LOG_FILE = os.environ.get("SHARED_LOG_FILE", "shared_pollinate_log.jsonl")
CONTRIBUTION_LOG_DB = os.environ.get("CONTRIBUTION_LOG_DB", "users.db")

# 相似度阈值
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.30"))

# 积分规则
EXTERNAL_SEED_REWARD = int(os.environ.get("EXTERNAL_SEED_REWARD", "5"))
MANUAL_POLLINATE_BASIC_REWARD = int(os.environ.get("MANUAL_POLLINATE_BASIC_REWARD", "3"))
MANUAL_POLLINATE_EXPERT_REWARD = int(os.environ.get("MANUAL_POLLINATE_EXPERT_REWARD", "10"))
QUERY_DEDUCTION = int(os.environ.get("QUERY_DEDUCTION", "2"))

# 节点相关
NODE_ID = os.environ.get("SASES_NODE_ID", "node-001")
NODE_NAME = os.environ.get("SASES_NODE_NAME", "SASES Node")
PEER_NODES = [x.strip() for x in os.environ.get("SASES_PEERS", "").split(",") if x.strip()]

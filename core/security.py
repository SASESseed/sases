# core/security.py
import os
import base64
import secrets
import string
import hmac
import hashlib
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("JWT_SECRET", "sases-dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.environ.get("REFRESH_TOKEN_EXPIRE_MINUTES", "43200"))
SIGN_KEY_FILE = os.environ.get("SIGN_KEY_FILE", "secret_key.bin")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: int, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def generate_sases_id() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "sases_" + ''.join(secrets.choice(alphabet) for _ in range(8))

def encrypt_api_key(api_key: str) -> str:
    return base64.b64encode(api_key.encode()).decode()

def decrypt_api_key(encrypted: str) -> str:
    return base64.b64decode(encrypted.encode()).decode()

def normalize_provider(provider: str) -> str:
    """将供应商名称标准化，兼容大小写、空格、连字符等"""
    p = provider.lower().replace(" ", "").replace("-", "").replace("_", "")
    if p in ("deepseek", "deepseekai", "deepseekchat"):
        return "deepseek"
    elif p in ("kimi", "moonshot", "moonshotai"):
        return "moonshot"
    elif p in ("openai", "gpt", "chatgpt"):
        return "openai"
    elif p in ("claude", "anthropic"):
        return "claude"
    else:
        return p

def _load_or_create_sign_key():
    if os.path.exists(SIGN_KEY_FILE):
        with open(SIGN_KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = os.urandom(32)
        with open(SIGN_KEY_FILE, 'wb') as f:
            f.write(key)
        return key

SIGN_KEY = _load_or_create_sign_key()

def sign_state(data: str) -> str:
    return hmac.new(SIGN_KEY, data.encode(), hashlib.sha256).hexdigest()

def verify_state(data: str, signature: str) -> bool:
    expected = sign_state(data)
    return hmac.compare_digest(expected, signature)

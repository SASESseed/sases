with open("auth.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 替换导入：移除 passlib，使用 bcrypt
if "from passlib.context import CryptContext" in content:
    content = content.replace(
        "from passlib.context import CryptContext",
        "import bcrypt"
    )

# 2. 删除 pwd_context 定义
content = content.replace(
    "pwd_context = CryptContext(schemes=[\"bcrypt\"], deprecated=\"auto\")",
    ""
)

# 3. 替换 create_user 中的哈希
old_create_hash = "hash = pwd_context.hash(password)"
new_create_hash = "hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')"
content = content.replace(old_create_hash, new_create_hash)

# 4. 替换 authenticate_user 中的验证
old_verify = "pwd_context.verify(password, user[\"password_hash\"])"
new_verify = "bcrypt.checkpw(password.encode('utf-8'), user[\"password_hash\"].encode('utf-8'))"
content = content.replace(old_verify, new_verify)

with open("auth.py", "w", encoding="utf-8") as f:
    f.write(content)

print("auth.py 已修复，使用 bcrypt 直接哈希。")

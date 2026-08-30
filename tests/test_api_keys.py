import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import auth
import core.db as db
import core.encryption as encryption
from core import auth_service

@pytest.fixture
def temp_api_env(tmp_path, monkeypatch):
    """使用临时数据库和假加密函数，避免真实密钥文件和数据库冲突"""
    # 临时数据库
    db_file = tmp_path / "test_users.db"
    monkeypatch.setattr(db, "DB_FILE", str(db_file))
    db.init_db()

    # 假加密：直接返回原文，避免生成密钥文件
    monkeypatch.setattr(encryption, "encrypt_text", lambda x: x)
    monkeypatch.setattr(encryption, "decrypt_text", lambda x: x)

    # 返回测试用户ID
    # 创建一个测试用户
    auth.create_user("apiuser", "apiuser@example.com", "password")
    user = auth.authenticate_user("apiuser", "password")
    return user["id"]

def test_add_api_key_and_standardize_provider(temp_api_env):
    uid = temp_api_env
    # 添加 provider='ds'，应被标准化为 'deepseek'
    auth.add_api_key(uid, "ds", "sk-test1234567890", priority=1)
    keys = auth.list_api_keys(uid)
    assert len(keys) == 1
    assert keys[0]["provider"] == "deepseek"
    assert keys[0]["priority"] == 1

def test_add_api_key_updates_existing_provider(temp_api_env):
    uid = temp_api_env
    auth.add_api_key(uid, "deepseek", "sk-old", priority=1)
    auth.add_api_key(uid, "deepseek", "sk-new", priority=2)
    keys = auth.list_api_keys(uid)
    assert len(keys) == 1
    # 注意：masked_key 由于假加密显示为 "****" + 最后四位
    # 原始 key 是 "sk-new"，最后四位为 "new"
    assert keys[0]["masked_key"].endswith("new")
    assert keys[0]["priority"] == 2

def test_list_api_keys_masks_key(temp_api_env):
    uid = temp_api_env
    auth.add_api_key(uid, "openai", "sk-abcdefghijklmnop", priority=0)
    keys = auth.list_api_keys(uid)
    assert len(keys) == 1
    # 假加密下 encrypted_key 为原文 "sk-abcdefghijklmnop"，最后四位为 "mnop"
    assert keys[0]["masked_key"] == "****mnop"

def test_delete_api_key(temp_api_env):
    uid = temp_api_env
    auth.add_api_key(uid, "moonshot", "sk-delete-me", priority=1)
    keys = auth.list_api_keys(uid)
    assert len(keys) == 1
    key_id = keys[0]["id"]
    auth.delete_api_key(uid, key_id)
    assert len(auth.list_api_keys(uid)) == 0

def test_set_api_key_priority(temp_api_env):
    uid = temp_api_env
    auth.add_api_key(uid, "zhipu", "sk-priority", priority=1)
    keys = auth.list_api_keys(uid)
    key_id = keys[0]["id"]
    auth.set_api_key_priority(uid, key_id, 10)
    keys = auth.list_api_keys(uid)
    assert keys[0]["priority"] == 10

def test_get_active_api_keys_returns_decrypted_sorted(temp_api_env):
    uid = temp_api_env
    # 添加多个 key，优先级不同
    auth.add_api_key(uid, "qwen", "sk-low", priority=1)
    auth.add_api_key(uid, "deepseek", "sk-high", priority=5)
    auth.add_api_key(uid, "openai", "sk-mid", priority=3)

    active = auth.get_active_api_keys(uid)
    # 应按优先级从高到低排序
    assert len(active) == 3
    assert active[0]["provider"] == "deepseek"
    assert active[0]["key"] == "sk-high"
    assert active[1]["provider"] == "openai"
    assert active[1]["key"] == "sk-mid"
    assert active[2]["provider"] == "qwen"
    assert active[2]["key"] == "sk-low"

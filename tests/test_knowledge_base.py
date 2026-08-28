import os
import sys
import json
import pytest

# 确保可以导入 core 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import knowledge_base

@pytest.fixture
def temp_kb(tmp_path):
    """使用临时文件作为知识库和共享日志，避免污染真实数据"""
    kb_file = tmp_path / "test_success_kb.json"
    shared_file = tmp_path / "test_shared_log.jsonl"
    knowledge_base.KB_FILE = str(kb_file)
    knowledge_base.SHARED_LOG_FILE = str(shared_file)
    return knowledge_base

def test_add_and_load_kb(temp_kb):
    # 初始应为空
    assert temp_kb.load_kb() == []

    # 添加一条记录
    temp_kb.add_to_kb(
        task="测试任务",
        branch_a="思路A",
        branch_b="思路B",
        synthesis="解决方案",
        model_id="test_model",
        user_id="user_1",
        backtrack_count=1,
        test_cases=[{"input": 1, "expected_output": 2}]
    )

    kb = temp_kb.load_kb()
    assert len(kb) == 1
    assert kb[0]["task"] == "测试任务"
    assert kb[0]["solution"] == "解决方案"
    assert kb[0]["model_id"] == "test_model"
    assert kb[0]["user_id"] == "user_1"
    assert kb[0]["backtrack_count"] == 1
    assert kb[0]["verified"] is True
    assert "id" in kb[0]
    assert "timestamp" in kb[0]

def test_save_and_load_persistence(temp_kb):
    entries = [
        {"id": "1", "task": "任务1", "solution": "方案1", "verified": True},
        {"id": "2", "task": "任务2", "solution": "方案2", "verified": True},
    ]
    temp_kb.save_kb(entries)
    loaded = temp_kb.load_kb()
    assert loaded == entries

def test_shared_id_management(temp_kb):
    # 初始共享ID集合为空
    assert temp_kb.load_shared_ids() == set()

    # 添加共享ID
    temp_kb.add_shared_id("entry-123")
    temp_kb.add_shared_id("entry-456")

    shared = temp_kb.load_shared_ids()
    assert shared == {"entry-123", "entry-456"}

def test_find_pending_pollinate_only_manual_and_unshared(temp_kb):
    # 添加不同类型的记录
    # 1. 系统生成的记录，未分享，不应被找到
    temp_kb.add_to_kb(
        task="系统生成任务",
        branch_a="",
        branch_b="",
        synthesis="系统方案",
        model_id="deepseek-v4-flash",
        user_id="user_1"
    )
    # 2. 手动授粉记录，未分享，应被找到
    temp_kb.add_to_kb(
        task="手动授粉任务",
        branch_a="",
        branch_b="",
        synthesis="手动方案",
        model_id="manual_pollinate",
        user_id="user_1"
    )
    # 3. 手动授粉记录，已分享，不应被找到
    temp_kb.add_to_kb(
        task="已分享手动任务",
        branch_a="",
        branch_b="",
        synthesis="已分享方案",
        model_id="manual_pollinate",
        user_id="user_1"
    )
    # 标记第三个为已分享
    temp_kb.add_shared_id(temp_kb.load_kb()[-1]["id"])

    pending = temp_kb.find_pending_pollinate("user_1")
    assert pending is not None
    assert pending["model_id"] == "manual_pollinate"
    assert pending["task"] == "手动授粉任务"

def test_find_pending_pollinate_no_record(temp_kb):
    # 没有任何记录
    assert temp_kb.find_pending_pollinate("user_1") is None

    # 只有系统记录
    temp_kb.add_to_kb(
        task="系统任务",
        branch_a="",
        branch_b="",
        synthesis="系统方案",
        model_id="deepseek-v4-flash",
        user_id="user_1"
    )
    assert temp_kb.find_pending_pollinate("user_1") is None

def test_tokenize_function(temp_kb):
    # 测试分词函数
    tokens = temp_kb.tokenize("Hello World, 你好世界")
    assert "hello" in tokens
    assert "world" in tokens
    assert "你好世界" in tokens

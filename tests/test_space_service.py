import os
import sys
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.space_service import SpaceService
from core.harness_models import ToolInvokeResponse

@pytest.fixture
def temp_space(tmp_path):
    nodes_file = tmp_path / "test_space_nodes.json"
    service = SpaceService(str(nodes_file))
    return service

def test_register_and_list_node(temp_space):
    temp_space.register_node("node-1", "Test Node", "A test harness node", capabilities=["test"])
    nodes = temp_space.list_nodes()
    assert len(nodes) == 1
    assert nodes[0]["name"] == "Test Node"

def test_register_and_get_node(temp_space):
    temp_space.register_node("node-2", "Node 2", "Another node")
    node = temp_space.get_node("node-2")
    assert node is not None
    assert node["node_id"] == "node-2"

def test_update_reputation(temp_space):
    temp_space.register_node("node-3", "Node 3", "Node for reputation")
    temp_space.update_reputation("node-3", True)
    temp_space.update_reputation("node-3", False)
    node = temp_space.get_node("node-3")
    assert node["total_count"] == 2
    assert node["success_count"] == 1
    assert node["reputation"] == 0.75

def test_remote_invoke(temp_space):
    # 创建一个简单的远程 FastAPI 应用作为 mock endpoint
    remote_app = FastAPI()

    @remote_app.post("/harness/invoke")
    async def invoke():
        return ToolInvokeResponse(
            module_id="unit-converter",
            success=True,
            result={"fahrenheit": 86.0},
            error=None
        ).dict()

    remote_client = TestClient(remote_app)
    # 由于 httpx 需要真实 HTTP，我们使用一个简单的本地 server 或者 monkeypatch httpx.Client
    # 这里采用 monkeypatch 方式模拟 httpx.Client 的 post 方法
    import core.space_service as space_module

    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"success": True, "result": {"fahrenheit": 86.0}, "error": None}

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, json):
            return MockResponse()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(space_module.httpx, "Client", MockClient)

    # 注册一个带 endpoint 的节点
    temp_space.register_node("remote-node", "Remote Unit Converter", "Remote converter",
                             endpoint="http://fake-endpoint:8000")
    result = temp_space.invoke_remote_node("remote-node", {"celsius": 30})
    assert result["success"] is True
    assert result["result"]["fahrenheit"] == 86.0

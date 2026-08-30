import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.space_service import SpaceService

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

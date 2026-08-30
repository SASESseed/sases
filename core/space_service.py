import json
import os
import time
from typing import Dict, Any, List, Optional

import httpx

from core.harness_runtime import harness_runtime
from core import config

SPACE_NODES_FILE = "space_nodes.json"

class SpaceService:
    def __init__(self, nodes_file: str = SPACE_NODES_FILE):
        self.nodes_file = nodes_file
        self.nodes = self._load_nodes()
        # 注册本节点信息（如果有的话，可选）
        self._register_self()

    def _load_nodes(self) -> Dict[str, dict]:
        if not os.path.exists(self.nodes_file):
            return {}
        with open(self.nodes_file, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}

    def _save_nodes(self):
        with open(self.nodes_file, "w", encoding="utf-8") as f:
            json.dump(self.nodes, f, ensure_ascii=False, indent=2)

    def _register_self(self):
        """如果配置了节点 ID 和名称，自动注册本节点为服务节点"""
        if config.NODE_ID and config.NODE_NAME:
            self.register_node(
                node_id=config.NODE_ID,
                name=config.NODE_NAME,
                description="SASES Node",
                node_type="sases_service",
                capabilities=["node_service"],
                endpoint=None,  # 本地节点没有远程端点
                owner_id="self"
            )

    def register_node(self, node_id: str, name: str, description: str,
                      node_type: str = "harness", capabilities: List[str] = None,
                      endpoint: str = None, icon: str = None, owner_id: str = "system") -> Dict[str, Any]:
        capabilities = capabilities or []
        node = {
            "node_id": node_id,
            "name": name,
            "description": description,
            "node_type": node_type,
            "capabilities": capabilities,
            "endpoint": endpoint,
            "icon": icon,
            "owner_id": owner_id,
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reputation": 1.0,
            "success_count": 0,
            "total_count": 0
        }
        self.nodes[node_id] = node
        self._save_nodes()
        return node

    def list_nodes(self, node_type: str = None) -> List[Dict[str, Any]]:
        result = []
        for node in self.nodes.values():
            if node_type and node.get("node_type") != node_type:
                continue
            result.append(node)
        return result

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(node_id)

    def update_reputation(self, node_id: str, success: bool):
        node = self.nodes.get(node_id)
        if not node:
            return
        node["total_count"] = node.get("total_count", 0) + 1
        if success:
            node["success_count"] = node.get("success_count", 0) + 1
        if node["total_count"] > 0:
            success_rate = node["success_count"] / node["total_count"]
            node["reputation"] = 0.5 + success_rate * 0.5
        self._save_nodes()

    def invoke_remote_node(self, node_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        node = self.get_node(node_id)
        if not node:
            return {"success": False, "error": f"Node {node_id} not found"}

        if node.get("node_type") == "harness" and not node.get("endpoint"):
            resp = harness_runtime.invoke_tool(node_id, params)
            self.update_reputation(node_id, resp.success)
            return {
                "success": resp.success,
                "result": resp.result if resp.success else None,
                "error": resp.error if not resp.success else None
            }

        endpoint = node.get("endpoint")
        if not endpoint:
            return {"success": False, "error": "Node has no endpoint for remote invocation"}

        url = f"{endpoint.rstrip('/')}/harness/invoke"
        payload = {"module_id": node_id, "params": params}
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                success = data.get("success", False)
                self.update_reputation(node_id, success)
                return data
        except Exception as e:
            self.update_reputation(node_id, False)
            return {"success": False, "error": f"Remote call failed: {e}"}

    def sync_from_peer(self, peer_url: str) -> dict:
        """从远程节点拉取节点列表并合并到本地。"""
        url = f"{peer_url.rstrip('/')}/space/nodes"
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(url)
                response.raise_for_status()
                remote_nodes = response.json()
                added = 0
                for node in remote_nodes:
                    node_id = node.get("node_id")
                    if node_id and node_id not in self.nodes:
                        self.nodes[node_id] = node
                        added += 1
                self._save_nodes()
                return {"success": True, "added": added, "total_local": len(self.nodes)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_to_peer(self, peer_url: str) -> dict:
        """向远程节点注册本节点信息。"""
        url = f"{peer_url.rstrip('/')}/space/register_node_external"
        self_node = self.get_node(config.NODE_ID)
        if not self_node:
            return {"success": False, "error": "Local node not registered"}
        payload = {
            "node_id": self_node["node_id"],
            "name": self_node["name"],
            "description": self_node["description"],
            "node_type": self_node["node_type"],
            "capabilities": self_node["capabilities"],
            "endpoint": self_node.get("endpoint"),
            "icon": self_node.get("icon"),
            "owner_id": self_node.get("owner_id")
        }
        try:
            with httpx.Client(timeout=5) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

# 全局单例
space_service = SpaceService()

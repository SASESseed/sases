import json
import os
import time
from typing import Dict, Any, List, Optional

import httpx

from core.harness_runtime import harness_runtime

SPACE_NODES_FILE = "space_nodes.json"

class SpaceService:
    def __init__(self, nodes_file: str = SPACE_NODES_FILE):
        self.nodes_file = nodes_file
        self.nodes = self._load_nodes()

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

    def register_node(self, node_id: str, name: str, description: str,
                      node_type: str = "harness", capabilities: List[str] = None,
                      endpoint: str = None, icon: str = None, owner_id: str = "system") -> Dict[str, Any]:
        """注册或更新节点"""
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
        """
        调用远程节点。
        - 如果节点是 harness 类型且 endpoint 为空，则调用本地 Harness 模块。
        - 如果 endpoint 存在，则通过 HTTP POST 到远程节点的 /harness/invoke 接口。
        """
        node = self.get_node(node_id)
        if not node:
            return {"success": False, "error": f"Node {node_id} not found"}

        # 本地调用
        if node.get("node_type") == "harness" and not node.get("endpoint"):
            resp = harness_runtime.invoke_tool(node_id, params)
            self.update_reputation(node_id, resp.success)
            return {
                "success": resp.success,
                "result": resp.result if resp.success else None,
                "error": resp.error if not resp.success else None
            }

        # 远程调用
        endpoint = node.get("endpoint")
        if not endpoint:
            return {"success": False, "error": "Node has no endpoint for remote invocation"}

        url = f"{endpoint.rstrip('/')}/harness/invoke"
        payload = {
            "module_id": node_id,
            "params": params
        }
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

# 全局单例
space_service = SpaceService()

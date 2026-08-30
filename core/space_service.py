import json
import os
import time
from typing import Dict, Any, List, Optional

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
            "reputation": 1.0,   # 初始信誉分
            "success_count": 0,
            "total_count": 0
        }
        self.nodes[node_id] = node
        self._save_nodes()
        return node

    def list_nodes(self, node_type: str = None) -> List[Dict[str, Any]]:
        """返回节点列表，可按类型过滤"""
        result = []
        for node in self.nodes.values():
            if node_type and node.get("node_type") != node_type:
                continue
            result.append(node)
        return result

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(node_id)

    def update_reputation(self, node_id: str, success: bool):
        """根据任务结果更新节点信誉分"""
        node = self.nodes.get(node_id)
        if not node:
            return
        node["total_count"] = node.get("total_count", 0) + 1
        if success:
            node["success_count"] = node.get("success_count", 0) + 1
        # 简单信誉计算：成功率加权，初始为1.0
        if node["total_count"] > 0:
            success_rate = node["success_count"] / node["total_count"]
            node["reputation"] = 0.5 + success_rate * 0.5
        self._save_nodes()

    def invoke_remote_node(self, node_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用远程节点。当前简化版本：只支持本地 Harness 模块调用。
        未来可通过节点 endpoint 进行 HTTP 调用。
        """
        from core.harness_runtime import harness_runtime

        node = self.get_node(node_id)
        if not node:
            return {"success": False, "error": f"Node {node_id} not found"}

        # 如果是 harness 类型，直接调用本地 Harness 模块
        if node.get("node_type") == "harness":
            resp = harness_runtime.invoke_tool(node_id, params)
            self.update_reputation(node_id, resp.success)
            return {
                "success": resp.success,
                "result": resp.result if resp.success else None,
                "error": resp.error if not resp.success else None
            }

        # 远程节点暂未实现
        return {"success": False, "error": "Remote node invocation not implemented yet"}

# 全局单例
space_service = SpaceService()

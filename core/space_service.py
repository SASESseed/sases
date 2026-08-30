import json
import os
import time
import threading
from typing import Dict, Any, List, Optional

import httpx

from core.harness_runtime import harness_runtime
from core import config

SPACE_NODES_FILE = "space_nodes.json"

class SpaceService:
    def __init__(self, nodes_file: str = SPACE_NODES_FILE):
        self.nodes_file = nodes_file
        self._lock = threading.RLock()
        self.nodes = self._load_nodes()
        self._register_self()
        # 自动同步相关
        self._sync_thread = None
        self._stop_sync = threading.Event()
        # 健康检查相关
        self._health_thread = None
        self._stop_health = threading.Event()

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
        if config.NODE_ID and config.NODE_NAME:
            self.register_node(
                node_id=config.NODE_ID,
                name=config.NODE_NAME,
                description="SASES Node",
                node_type="sases_service",
                capabilities=["node_service"],
                endpoint=None,
                owner_id="self"
            )

    def _is_valid_node(self, node: dict) -> bool:
        required_fields = ["node_id", "name", "node_type"]
        for field in required_fields:
            if field not in node or not node[field]:
                return False
        if "capabilities" in node and not isinstance(node["capabilities"], list):
            return False
        if "endpoint" in node and node["endpoint"] is not None and not isinstance(node["endpoint"], str):
            return False
        return True

    def register_node(self, node_id: str, name: str, description: str,
                      node_type: str = "harness", capabilities: List[str] = None,
                      endpoint: str = None, icon: str = None, owner_id: str = "system") -> Dict[str, Any]:
        capabilities = capabilities or []
        with self._lock:
            existing = self.nodes.get(node_id)
            if existing:
                existing.update({
                    "name": name,
                    "description": description,
                    "node_type": node_type,
                    "capabilities": capabilities,
                    "endpoint": endpoint,
                    "icon": icon,
                    "owner_id": owner_id,
                    "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    # 保留状态和信誉
                    "status": existing.get("status", "unknown")
                })
                node = existing
            else:
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
                    "total_count": 0,
                    "status": "unknown"
                }
            self.nodes[node_id] = node
            self._save_nodes()
            return node

    def list_nodes(self, node_type: str = None) -> List[Dict[str, Any]]:
        with self._lock:
            result = []
            for node in self.nodes.values():
                if node_type and node.get("node_type") != node_type:
                    continue
                result.append(node)
            return result

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.nodes.get(node_id)

    def update_reputation(self, node_id: str, success: bool):
        with self._lock:
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

    def update_node_status(self, node_id: str, status: str):
        """更新节点在线状态：online/offline/unknown"""
        with self._lock:
            node = self.nodes.get(node_id)
            if node:
                node["status"] = status
                self._save_nodes()

    def check_node_health(self, node_id: str) -> bool:
        """检查指定节点是否在线，返回 True/False"""
        node = self.get_node(node_id)
        if not node or not node.get("endpoint"):
            return False
        endpoint = node["endpoint"].rstrip("/")
        health_url = f"{endpoint}/space/health"
        try:
            with httpx.Client(timeout=3) as client:
                response = client.get(health_url)
                if response.status_code == 200:
                    self.update_node_status(node_id, "online")
                    return True
                else:
                    self.update_node_status(node_id, "offline")
                    return False
        except Exception:
            self.update_node_status(node_id, "offline")
            return False

    def _update_all_nodes_health(self):
        """更新所有有 endpoint 的节点的在线状态"""
        for node_id in list(self.nodes.keys()):
            if self.nodes[node_id].get("endpoint"):
                self.check_node_health(node_id)

    def invoke_remote_node(self, node_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
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
        url = f"{peer_url.rstrip('/')}/space/nodes"
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(url)
                response.raise_for_status()
                remote_nodes = response.json()
                added = 0
                invalid = 0
                if not isinstance(remote_nodes, list):
                    return {"success": False, "error": "Invalid response format from peer"}
                with self._lock:
                    for node in remote_nodes:
                        if not isinstance(node, dict) or not self._is_valid_node(node):
                            invalid += 1
                            continue
                        node_id = node.get("node_id")
                        if node_id and node_id not in self.nodes:
                            self.nodes[node_id] = node
                            self.nodes[node_id]["status"] = "unknown"  # 新节点初始状态
                            added += 1
                    self._save_nodes()
                return {
                    "success": True,
                    "added": added,
                    "invalid": invalid,
                    "total_local": len(self.nodes)
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_to_peer(self, peer_url: str) -> dict:
        url = f"{peer_url.rstrip('/')}/space/register_node_external"
        with self._lock:
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

    # ========== 自动同步 ==========
    def start_auto_sync(self, interval: int = 300):
        """启动后台自动同步线程，默认每 300 秒同步一次"""
        if self._sync_thread and self._sync_thread.is_alive():
            return
        self._stop_sync.clear()
        self._sync_thread = threading.Thread(
            target=self._auto_sync_loop,
            args=(interval,),
            daemon=True,
            name="space-auto-sync"
        )
        self._sync_thread.start()
        print(f"自动同步线程已启动，间隔 {interval} 秒")

    def stop_auto_sync(self):
        """停止自动同步线程"""
        self._stop_sync.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
            self._sync_thread = None
            print("自动同步线程已停止")

    def _auto_sync_loop(self, interval: int):
        while not self._stop_sync.is_set():
            self.sync_all_peers()
            self._stop_sync.wait(interval)

    def sync_all_peers(self):
        """对所有配置的 peer 执行同步和注册"""
        peers = config.PEER_NODES
        if not peers:
            return
        for peer in peers:
            result = self.sync_from_peer(peer)
            if result.get("success"):
                print(f"同步 {peer} 成功，新增节点 {result.get('added', 0)}")
            else:
                print(f"同步 {peer} 失败: {result.get('error')}")
            reg_result = self.register_to_peer(peer)
            if reg_result.get("success") or "Node registered" in str(reg_result):
                print(f"向 {peer} 注册成功")
            else:
                print(f"向 {peer} 注册失败: {reg_result.get('error')}")

    # ========== 健康检查 ==========
    def start_health_check(self, interval: int = 60):
        """启动健康检查后台线程，默认每 60 秒检查一次"""
        if self._health_thread and self._health_thread.is_alive():
            return
        self._stop_health.clear()
        self._health_thread = threading.Thread(
            target=self._health_check_loop,
            args=(interval,),
            daemon=True,
            name="space-health-check"
        )
        self._health_thread.start()
        print(f"健康检查线程已启动，间隔 {interval} 秒")

    def stop_health_check(self):
        """停止健康检查线程"""
        self._stop_health.set()
        if self._health_thread:
            self._health_thread.join(timeout=5)
            self._health_thread = None
            print("健康检查线程已停止")

    def _health_check_loop(self, interval: int):
        while not self._stop_health.is_set():
            self._update_all_nodes_health()
            self._stop_health.wait(interval)

# 全局单例
space_service = SpaceService()

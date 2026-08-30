import json
import time
import threading
from typing import Dict, Any, List, Optional

import httpx

from core.harness_runtime import harness_runtime
from core import config
from core.db import get_db, init_db

class SpaceService:
    def __init__(self, nodes_file: Optional[str] = None):
        # 忽略 nodes_file 参数，仅用于兼容旧测试
        init_db()
        self._register_self()

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

    def _row_to_dict(self, row):
        if not row:
            return None
        d = dict(row)
        if d.get("capabilities"):
            try:
                d["capabilities"] = json.loads(d["capabilities"])
            except:
                d["capabilities"] = []
        else:
            d["capabilities"] = []
        return d

    def register_node(self, node_id: str, name: str, description: str,
                      node_type: str = "harness", capabilities: List[str] = None,
                      endpoint: str = None, icon: str = None, owner_id: str = "system") -> Dict[str, Any]:
        capabilities = capabilities or []
        caps_json = json.dumps(capabilities)
        with get_db() as conn:
            existing = conn.execute("SELECT * FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
            if existing:
                conn.execute("""
                UPDATE space_nodes
                SET name = ?, description = ?, node_type = ?, capabilities = ?, endpoint = ?, icon = ?, owner_id = ?, registered_at = ?
                WHERE node_id = ?
                """, (name, description, node_type, caps_json, endpoint, icon, owner_id, time.strftime("%Y-%m-%d %H:%M:%S"), node_id))
            else:
                conn.execute("""
                INSERT INTO space_nodes (node_id, name, description, node_type, capabilities, endpoint, icon, owner_id, registered_at, reputation, success_count, total_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, 0, 0, 'unknown')
                """, (node_id, name, description, node_type, caps_json, endpoint, icon, owner_id, time.strftime("%Y-%m-%d %H:%M:%S")))
            row = conn.execute("SELECT * FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
        return self._row_to_dict(row)

    def list_nodes(self, node_type: str = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            if node_type:
                rows = conn.execute("SELECT * FROM space_nodes WHERE node_type = ?", (node_type,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM space_nodes").fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
        return self._row_to_dict(row)

    def update_reputation(self, node_id: str, success: bool):
        with get_db() as conn:
            node = conn.execute("SELECT total_count, success_count FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
            if not node:
                return
            total = node["total_count"] + 1
            success_count = node["success_count"] + (1 if success else 0)
            reputation = 0.5 + (success_count / total) * 0.5 if total > 0 else 1.0
            conn.execute("""
            UPDATE space_nodes
            SET total_count = ?, success_count = ?, reputation = ?
            WHERE node_id = ?
            """, (total, success_count, reputation, node_id))

    def update_node_status(self, node_id: str, status: str):
        with get_db() as conn:
            conn.execute("UPDATE space_nodes SET status = ? WHERE node_id = ?", (status, node_id))

    def check_node_health(self, node_id: str) -> bool:
        node = self.get_node(node_id)
        if not node or not node.get("endpoint"):
            return False
        endpoint = node["endpoint"].rstrip("/")
        health_url = f"{endpoint}/space/health"
        headers = {}
        if config.NODE_TOKEN:
            headers["X-Node-Token"] = config.NODE_TOKEN
        try:
            with httpx.Client(timeout=3) as client:
                response = client.get(health_url, headers=headers)
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
        nodes = self.list_nodes()
        for node in nodes:
            if node.get("endpoint"):
                self.check_node_health(node["node_id"])

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
        headers = {}
        if config.NODE_TOKEN:
            headers["X-Node-Token"] = config.NODE_TOKEN
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload, headers=headers)
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
        headers = {}
        if config.NODE_TOKEN:
            headers["X-Node-Token"] = config.NODE_TOKEN
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                remote_nodes = response.json()
                added = 0
                invalid = 0
                if not isinstance(remote_nodes, list):
                    return {"success": False, "error": "Invalid response format from peer"}
                with get_db() as conn:
                    for node in remote_nodes:
                        if not isinstance(node, dict):
                            invalid += 1
                            continue
                        node_id = node.get("node_id")
                        name = node.get("name")
                        node_type = node.get("node_type")
                        if not node_id or not name or not node_type:
                            invalid += 1
                            continue
                        existing = conn.execute("SELECT 1 FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
                        if not existing:
                            capabilities = json.dumps(node.get("capabilities", []))
                            conn.execute("""
                            INSERT INTO space_nodes (node_id, name, description, node_type, capabilities, endpoint, icon, owner_id, registered_at, reputation, success_count, total_count, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 'unknown')
                            """, (
                                node_id,
                                name,
                                node.get("description", ""),
                                node_type,
                                capabilities,
                                node.get("endpoint"),
                                node.get("icon"),
                                node.get("owner_id", "remote"),
                                time.strftime("%Y-%m-%d %H:%M:%S"),
                                node.get("reputation", 1.0),
                            ))
                            added += 1
                return {
                    "success": True,
                    "added": added,
                    "invalid": invalid,
                    "total_local": len(self.list_nodes())
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_to_peer(self, peer_url: str) -> dict:
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
        headers = {}
        if config.NODE_TOKEN:
            headers["X-Node-Token"] = config.NODE_TOKEN
        try:
            with httpx.Client(timeout=5) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ---------- 后台任务 ----------
    def start_auto_sync(self, interval: int = 300):
        import threading
        if getattr(self, "_sync_thread", None) and self._sync_thread.is_alive():
            return
        self._stop_sync = threading.Event()
        self._sync_thread = threading.Thread(target=self._auto_sync_loop, args=(interval,), daemon=True)
        self._sync_thread.start()
        print(f"自动同步线程已启动，间隔 {interval} 秒")

    def stop_auto_sync(self):
        if getattr(self, "_stop_sync", None):
            self._stop_sync.set()
            if getattr(self, "_sync_thread", None):
                self._sync_thread.join(timeout=5)
        print("自动同步线程已停止")

    def _auto_sync_loop(self, interval):
        while not self._stop_sync.is_set():
            self.sync_all_peers()
            self._stop_sync.wait(interval)

    def sync_all_peers(self):
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

    def start_health_check(self, interval: int = 60):
        import threading
        if getattr(self, "_health_thread", None) and self._health_thread.is_alive():
            return
        self._stop_health = threading.Event()
        self._health_thread = threading.Thread(target=self._health_check_loop, args=(interval,), daemon=True)
        self._health_thread.start()
        print(f"健康检查线程已启动，间隔 {interval} 秒")

    def stop_health_check(self):
        if getattr(self, "_stop_health", None):
            self._stop_health.set()
            if getattr(self, "_health_thread", None):
                self._health_thread.join(timeout=5)
        print("健康检查线程已停止")

    def _health_check_loop(self, interval):
        while not self._stop_health.is_set():
            self._update_all_nodes_health()
            self._stop_health.wait(interval)

# 全局单例
space_service = SpaceService()

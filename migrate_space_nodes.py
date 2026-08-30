import json
import os
from core.db import init_db
from core.space_service import SpaceService

init_db()
service = SpaceService()

if os.path.exists("space_nodes.json"):
    with open("space_nodes.json", "r", encoding="utf-8") as f:
        nodes = json.load(f)
    for node in nodes.values():
        service.register_node(
            node_id=node.get("node_id"),
            name=node.get("name"),
            description=node.get("description", ""),
            node_type=node.get("node_type", "harness"),
            capabilities=node.get("capabilities", []),
            endpoint=node.get("endpoint"),
            icon=node.get("icon"),
            owner_id=node.get("owner_id", "system")
        )
    print(f"迁移完成，共 {len(nodes)} 个节点")
else:
    print("未找到 space_nodes.json，无需迁移。")

from typing import Dict, Any, List, Optional

from core.harness_loader import load_harness_modules, HARNESS_MODULES_DIR
from core.harness_models import ModuleManifest, ToolDefinition, ToolInvokeResponse

class HarnessRuntime:
    def __init__(self, modules_dir: str = HARNESS_MODULES_DIR):
        self.modules_dir = modules_dir
        self._modules = load_harness_modules(modules_dir)

    def list_tools(self) -> List[ToolDefinition]:
        tools = []
        for module_id, info in self._modules.items():
            manifest = info["manifest"]
            tools.append(ToolDefinition(
                module_id=manifest.id,
                name=manifest.name,
                description=manifest.description,
                capabilities=manifest.capabilities,
                permissions=manifest.permissions,
                version=manifest.version,
                node_type=manifest.node_type
            ))
        return tools

    def get_tool(self, module_id: str) -> Optional[ToolDefinition]:
        for tool in self.list_tools():
            if tool.module_id == module_id:
                return tool
        return None

    def invoke_tool(self, module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
        info = self._modules.get(module_id)
        if not info:
            return ToolInvokeResponse(
                module_id=module_id,
                success=False,
                error=f"Module {module_id} not found"
            )
        try:
            result = info["run_fn"](params)
            return ToolInvokeResponse(
                module_id=module_id,
                success=True,
                result=result
            )
        except Exception as e:
            return ToolInvokeResponse(
                module_id=module_id,
                success=False,
                error=str(e)
            )

    def get_node_info(self, module_id: str) -> Optional[dict]:
        info = self._modules.get(module_id)
        if not info:
            return None
        manifest = info["manifest"]
        return {
            "node_id": manifest.id,
            "name": manifest.name,
            "description": manifest.description,
            "node_type": manifest.node_type,
            "capabilities": manifest.capabilities,
            "icon": manifest.icon
        }

# 全局单例
harness_runtime = HarnessRuntime()

import json
import os
import importlib.util
from typing import List, Dict, Any, Optional

from core.harness_models import ModuleManifest, ToolDefinition, ToolInvokeResponse

HARNESS_MODULES_DIR = "harness_modules"

def _load_manifest(module_dir: str) -> Optional[ModuleManifest]:
    """从模块目录加载 manifest.json"""
    manifest_path = os.path.join(module_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ModuleManifest(**data)

def _load_module_function(module_dir: str, entrypoint: str):
    """加载模块入口文件中的 run 函数"""
    entry_path = os.path.join(module_dir, entrypoint)
    if not os.path.exists(entry_path):
        raise FileNotFoundError(f"Entrypoint {entry_path} not found")
    spec = importlib.util.spec_from_file_location("harness_module", entry_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "run"):
        raise AttributeError("Module entrypoint must define a run(params) function")
    return module.run

class HarnessRuntime:
    def __init__(self, modules_dir: str = HARNESS_MODULES_DIR):
        self.modules_dir = modules_dir
        self._modules = self._scan_modules()

    def _scan_modules(self) -> Dict[str, dict]:
        """扫描模块目录，返回模块字典 {module_id: {manifest, dir, run_fn}}"""
        modules = {}
        if not os.path.exists(self.modules_dir):
            return modules
        for module_id in os.listdir(self.modules_dir):
            module_dir = os.path.join(self.modules_dir, module_id)
            if not os.path.isdir(module_dir):
                continue
            manifest = _load_manifest(module_dir)
            if manifest is None:
                continue
            try:
                run_fn = _load_module_function(module_dir, manifest.entrypoint)
            except Exception as e:
                print(f"Failed to load module {module_id}: {e}")
                continue
            modules[manifest.id] = {
                "manifest": manifest,
                "dir": module_dir,
                "run_fn": run_fn
            }
        return modules

    def list_tools(self) -> List[ToolDefinition]:
        """返回所有已加载模块的工具定义"""
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
        """调用指定模块的 run 函数"""
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
        """返回模块对应的智维空间节点元数据（未来扩展用）"""
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

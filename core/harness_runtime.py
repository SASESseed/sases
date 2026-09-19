# core/harness_runtime.py
from typing import Dict, Any, List, Optional

from core.harness_loader import load_harness_modules, HARNESS_MODULES_DIR
from core.harness_models import ModuleManifest, ToolDefinition, ToolInvokeResponse

# 默认允许的权限集合（安全权限）
DEFAULT_ALLOWED_PERMISSIONS = {
    "calculation",
    "text_processing",
    "json_formatting",
    "string_utils",
    "unit_conversion",
    "base64_codec",
    "text_stats",
    "file_patch",
    "frontend_edit",
    "restricted_file_write"
}

# 危险权限，默认拒绝，需要用户显式授权
DANGEROUS_PERMISSIONS = {
    "local_command",
    "file_write",
    "file_delete",
    "network",
    "socket",
    "subprocess",
    "system"
}


class HarnessRuntime:
    def __init__(self, modules_dir: str = HARNESS_MODULES_DIR):
        self.modules_dir = modules_dir
        self._modules = load_harness_modules(modules_dir)
        self.user_grants = set()

    def reload_modules(self) -> Dict[str, Any]:
        """
        重新扫描模块目录，动态加载新生成的 Harness 模块。
        返回加载结果报告。
        """
        old_ids = set(self._modules.keys())
        self._modules = load_harness_modules(self.modules_dir)
        new_ids = set(self._modules.keys())

        added = list(new_ids - old_ids)
        removed = list(old_ids - new_ids)
        total = len(new_ids)

        return {
            "success": True,
            "total_modules": total,
            "added": added,
            "removed": removed,
            "added_count": len(added),
            "removed_count": len(removed)
        }

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

    def _check_permissions(self, manifest: ModuleManifest) -> Optional[str]:
        """检查模块权限，返回错误信息或 None 表示通过"""
        for perm in manifest.permissions:
            if perm in self.user_grants:
                continue
            if perm in DANGEROUS_PERMISSIONS:
                return f"模块 '{manifest.name}' 需要危险权限 '{perm}'，但当前未被授权，已阻止执行"
            if perm not in DEFAULT_ALLOWED_PERMISSIONS:
                return f"模块 '{manifest.name}' 声明了未知权限 '{perm}'，已阻止执行"
        return None

    def invoke_tool(self, module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
        info = self._modules.get(module_id)
        if not info:
            return ToolInvokeResponse(
                module_id=module_id,
                success=False,
                error=f"Module {module_id} not found"
            )

        manifest = info["manifest"]

        perm_error = self._check_permissions(manifest)
        if perm_error:
            return ToolInvokeResponse(
                module_id=module_id,
                success=False,
                error=perm_error
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

    def grant_permission(self, module_id: str, permission: str):
        """用户授权某个模块的某个权限"""
        self.user_grants.add(permission)

    def revoke_permission(self, module_id: str, permission: str):
        """撤销授权"""
        self.user_grants.discard(permission)

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

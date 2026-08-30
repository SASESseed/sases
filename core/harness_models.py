from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class ModuleManifest(BaseModel):
    """Harness 模块清单，定义在模块目录的 manifest.json 中"""
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    capabilities: List[str] = []          # 能力标签，如 ["unit_conversion"]
    permissions: List[str] = []           # 权限声明，如 ["network", "file_read"]
    entrypoint: str = "main.py"           # 入口文件，默认 main.py
    icon: Optional[str] = None            # 节点图标（可选）
    node_type: str = "harness"            # 节点类型，默认为 harness

class ToolDefinition(BaseModel):
    """工具定义，用于返回给调用方"""
    module_id: str
    name: str
    description: str
    capabilities: List[str]
    permissions: List[str]
    version: str
    node_type: str

class ToolInvokeRequest(BaseModel):
    """调用工具请求体"""
    module_id: str
    params: Dict[str, Any] = {}

class ToolInvokeResponse(BaseModel):
    """调用工具响应体"""
    module_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None

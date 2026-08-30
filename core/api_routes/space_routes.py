from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.space_service import space_service
from core.api_routes.auth_routes import get_current_user

router = APIRouter()

class NodeRegisterRequest(BaseModel):
    node_id: str
    name: str
    description: str = ""
    node_type: str = "harness"
    capabilities: List[str] = []
    endpoint: Optional[str] = None
    icon: Optional[str] = None

class NodeRegisterExternalRequest(BaseModel):
    node_id: str
    name: str
    description: str = ""
    node_type: str = "harness"
    capabilities: List[str] = []
    endpoint: Optional[str] = None
    icon: Optional[str] = None
    owner_id: Optional[str] = "remote"

class NodeInvokeRequest(BaseModel):
    node_id: str
    params: Dict[str, Any] = {}

@router.post("/space/register_node")
async def register_node(req: NodeRegisterRequest, current_user=Depends(get_current_user)):
    node = space_service.register_node(
        node_id=req.node_id,
        name=req.name,
        description=req.description,
        node_type=req.node_type,
        capabilities=req.capabilities,
        endpoint=req.endpoint,
        icon=req.icon,
        owner_id=str(current_user["id"])
    )
    return {"message": "Node registered", "node": node}

# 节点间注册（不需要用户认证，供其他节点调用）
@router.post("/space/register_node_external")
async def register_node_external(req: NodeRegisterExternalRequest):
    node = space_service.register_node(
        node_id=req.node_id,
        name=req.name,
        description=req.description,
        node_type=req.node_type,
        capabilities=req.capabilities,
        endpoint=req.endpoint,
        icon=req.icon,
        owner_id=req.owner_id or "remote"
    )
    return {"message": "Node registered", "node": node}

@router.get("/space/nodes")
async def list_nodes(node_type: Optional[str] = None):
    return space_service.list_nodes(node_type)

@router.post("/space/invoke")
async def invoke_node(req: NodeInvokeRequest, current_user=Depends(get_current_user)):
    result = space_service.invoke_remote_node(req.node_id, req.params)
    return result

# 节点同步：拉取远程节点列表
@router.post("/space/sync_from_peer")
async def sync_from_peer(peer_url: str):
    result = space_service.sync_from_peer(peer_url)
    return result

# 节点同步：向远程节点注册自己
@router.post("/space/register_to_peer")
async def register_to_peer(peer_url: str):
    result = space_service.register_to_peer(peer_url)
    return result

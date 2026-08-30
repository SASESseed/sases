from fastapi import APIRouter, HTTPException
from typing import List

from core.harness_runtime import harness_runtime
from core.harness_models import ToolDefinition, ToolInvokeRequest, ToolInvokeResponse

router = APIRouter()

@router.get("/harness/tools", response_model=List[ToolDefinition])
async def list_tools():
    return harness_runtime.list_tools()

@router.get("/harness/node/{module_id}")
async def get_node(module_id: str):
    node_info = harness_runtime.get_node_info(module_id)
    if not node_info:
        raise HTTPException(status_code=404, detail="Module not found")
    return node_info

@router.post("/harness/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest):
    return harness_runtime.invoke_tool(req.module_id, req.params)

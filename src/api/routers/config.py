"""
配置路由 — models_config.json + user_settings.json
"""

import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter()


def _read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@router.get("")
async def get_config():
    """读取 models_config.json"""
    path = os.path.join(_PROJECT_ROOT, "models_config.json")
    return _read_json(path)


@router.get("/settings")
async def get_settings():
    """读取 user_settings.json"""
    path = os.path.join(_PROJECT_ROOT, "user_settings.json")
    return _read_json(path)


class SettingsUpdate(BaseModel):
    tdx_path: Optional[str] = None


@router.put("/settings")
async def update_settings(body: SettingsUpdate):
    """更新 user_settings.json"""
    path = os.path.join(_PROJECT_ROOT, "user_settings.json")
    current = _read_json(path)
    if body.tdx_path is not None:
        current["tdx_path"] = body.tdx_path
    _write_json(path, current)
    return {"ok": True, "settings": current}


@router.post("/validate-tdx")
async def validate_tdx(body: SettingsUpdate):
    """验证 TDX 路径是否包含 vipdoc"""
    if not body.tdx_path:
        raise HTTPException(400, "tdx_path required")
    vipdoc = os.path.join(body.tdx_path, "vipdoc")
    if os.path.exists(vipdoc):
        return {"valid": True, "vipdoc_path": vipdoc}
    # 也许用户直接给了 vipdoc 路径
    if os.path.basename(body.tdx_path) == "vipdoc" and os.path.exists(body.tdx_path):
        return {"valid": True, "vipdoc_path": body.tdx_path}
    return {"valid": False, "message": "vipdoc directory not found"}

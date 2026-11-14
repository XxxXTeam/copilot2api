from __future__ import annotations

import secrets

from fastapi import Request

from .config import Settings
from .errors import CopilotError


def _presented_key(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("X-Api-Key", "")


async def require_api_key(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if not settings.api_keys:
        return
    presented = _presented_key(request)
    if not any(secrets.compare_digest(presented, key) for key in settings.api_keys):
        raise CopilotError("API Key 无效或缺失", 401, "invalid_api_key")


async def require_admin(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if not settings.admin_token:
        return
    presented = request.headers.get("X-Admin-Key", "") or _presented_key(request)
    if not secrets.compare_digest(presented, settings.admin_token):
        raise CopilotError("管理令牌无效或缺失，请在管理界面登录", 401, "invalid_admin_token")

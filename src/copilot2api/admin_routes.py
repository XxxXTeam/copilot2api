from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request

from .auth import require_admin
from .copilot import available_chat_models
from .errors import CopilotError
from .schemas import AccountCreate, AccountUpdate

router = APIRouter(prefix="/api", dependencies=[Depends(require_admin)])


async def get_account_or_404(request: Request, account_id: str) -> dict[str, Any]:
    try:
        return await request.app.state.database.get_account(account_id)
    except KeyError as error:
        raise CopilotError("账号不存在", 404, "account_not_found") from error


def profile_values(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "login": profile.get("login"),
        "avatar_url": profile.get("avatar_url"),
        "plan": profile.get("copilot_plan"),
        "sku": profile.get("access_type_sku"),
        "quotas_json": json.dumps(profile.get("quota_snapshots", {})),
        "quota_reset_date": profile.get("quota_reset_date_utc") or profile.get("quota_reset_date"),
        "endpoints_json": json.dumps(profile.get("endpoints", {})),
        "status": "active",
        "last_error": None,
        "cooldown_until": 0,
    }


@router.get("/config")
async def config(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return {
        "strategy": request.app.state.pool.strategy,
        "api_auth_required": settings.api_auth_required,
        "admin_auth_required": bool(settings.admin_token),
        "request_timeout": settings.request_timeout,
    }


@router.get("/overview")
async def overview(request: Request) -> dict[str, Any]:
    pool = request.app.state.pool
    accounts = await pool.public_accounts()
    stats = await request.app.state.database.overview()
    quota_summary: dict[str, dict[str, Any]] = {}
    for account in accounts:
        if not account["enabled"]:
            continue
        for quota_id, quota in account["quotas"].items():
            summary = quota_summary.setdefault(
                quota_id, {"remaining": 0, "entitlement": 0, "unlimited": False, "accounts": 0}
            )
            summary["remaining"] += quota.get("remaining", quota.get("quota_remaining", 0)) or 0
            summary["entitlement"] += quota.get("entitlement", 0) or 0
            summary["unlimited"] = summary["unlimited"] or quota.get("unlimited", False)
            summary["accounts"] += 1
    return {
        "accounts": len(accounts),
        "enabled_accounts": sum(account["enabled"] for account in accounts),
        "healthy_accounts": sum(account["enabled"] and account["status"] == "active" for account in accounts),
        **stats,
        "quotas": quota_summary,
    }


@router.get("/accounts")
async def accounts(request: Request) -> list[dict[str, Any]]:
    return await request.app.state.pool.public_accounts()


@router.post("/accounts", status_code=201)
async def add_account(body: AccountCreate, request: Request) -> dict[str, Any]:
    profile = await request.app.state.copilot.fetch_profile(body.token)
    name = body.name.strip() or (profile or {}).get("login") or "Copilot 账号"
    account = await request.app.state.database.create_account(body.token, name, body.enabled, profile)
    return request.app.state.pool.public_account(account)


@router.patch("/accounts/{account_id}")
async def update_account(account_id: str, body: AccountUpdate, request: Request) -> dict[str, Any]:
    account = await get_account_or_404(request, account_id)
    values = body.model_dump(exclude_none=True)
    if "token" in values:
        token = values["token"].strip()
        if token.startswith("Bearer "):
            token = token[7:].strip()
        values["token"] = token
        profile = await request.app.state.copilot.fetch_profile(token)
        values.update(profile_values(profile))
    updated = await request.app.state.database.update_account(account["id"], **values)
    if "enabled" in values:
        updated = await request.app.state.database.update_account(
            account_id, status="active" if body.enabled else "disabled", last_error=None, cooldown_until=0
        )
    return request.app.state.pool.public_account(updated)


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(account_id: str, request: Request) -> None:
    await get_account_or_404(request, account_id)
    await request.app.state.database.delete_account(account_id)


@router.post("/accounts/{account_id}/refresh")
async def refresh_account(account_id: str, request: Request) -> dict[str, Any]:
    account = await get_account_or_404(request, account_id)
    try:
        profile = await request.app.state.copilot.fetch_profile(account["token"])
        values = profile_values(profile)
        if not account["enabled"]:
            values["status"] = "disabled"
        updated = await request.app.state.database.update_account(account_id, **values)
        return request.app.state.pool.public_account(updated)
    except CopilotError as error:
        await request.app.state.pool.mark_failure(account, error.status_code, error.message)
        raise


@router.get("/accounts/{account_id}/quota")
async def account_quota(account_id: str, request: Request, refresh: bool = True) -> dict[str, Any]:
    account = await get_account_or_404(request, account_id)
    if refresh:
        account = await refresh_account(account_id, request)
    return {
        "account_id": account_id,
        "quotas": account["quotas"],
        "quota_reset_date": account["quota_reset_date"],
        "updated_at": account["updated_at"],
    }


@router.get("/models")
async def models(request: Request, refresh: bool = False) -> dict[str, Any]:
    pool = request.app.state.pool
    account = await pool.acquire()
    try:
        data = await request.app.state.copilot.fetch_models(account)
        await pool.mark_success(account["id"])
        return {"data": data, "available": [model["id"] for model in available_chat_models(data)]}
    except CopilotError as error:
        await pool.mark_failure(account, error.status_code, error.message)
        raise
    finally:
        await pool.release(account["id"])

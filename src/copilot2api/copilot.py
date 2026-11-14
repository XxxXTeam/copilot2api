from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from .errors import CopilotError

GITHUB_USER_URL = "https://api.github.com/copilot_internal/user"
DEFAULT_COPILOT_API = "https://api.individual.githubcopilot.com"


class CopilotClient:
    def __init__(self, timeout: float = 180) -> None:
        self.machine_id = str(uuid.uuid4())
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=20),
            follow_redirects=False,
        )

    async def close(self) -> None:
        await self.client.aclose()

    def headers(self, token: str, initiator: str = "user") -> dict[str, str]:
        interaction_id = str(uuid.uuid4())
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "copilot/1.0.112 (linux) client/github/cli",
            "Editor-Version": "copilot/1.0.112",
            "Copilot-Integration-Id": "copilot-developer-cli",
            "Copilot-Harness-Id": "copilot-sdk",
            "OpenAI-Intent": "conversation-agent",
            "X-Github-Api-Version": "2026-08-01",
            "X-Initiator": initiator,
            "X-Interaction-Id": interaction_id,
            "X-Client-Session-Id": interaction_id,
            "X-Client-Machine-Id": self.machine_id,
        }

    @staticmethod
    def error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
            error = body.get("error", body)
            if isinstance(error, dict):
                return str(error.get("message") or error.get("code") or body)[:1000]
            return str(error)[:1000]
        except (ValueError, AttributeError):
            return (response.text or f"Copilot 上游返回 HTTP {response.status_code}")[:1000]

    async def fetch_profile(self, token: str) -> dict[str, Any]:
        try:
            response = await self.client.get(GITHUB_USER_URL, headers=self.headers(token))
        except httpx.RequestError as error:
            raise CopilotError(f"无法连接 GitHub：{error}", 502, "upstream_connection_error") from error
        if response.status_code != 200:
            raise CopilotError(
                f"令牌验证失败：{self.error_message(response)}",
                401 if response.status_code in {401, 403} else 502,
                "invalid_copilot_token",
            )
        profile = response.json()
        if not profile.get("chat_enabled"):
            raise CopilotError("该 GitHub 账号未启用 Copilot Chat", 400, "copilot_not_enabled")
        if profile.get("id"):
            profile["avatar_url"] = f"https://avatars.githubusercontent.com/u/{profile['id']}?v=4"
        return profile

    @staticmethod
    def api_base(account: dict[str, Any]) -> str:
        return str(account.get("endpoints", {}).get("api") or DEFAULT_COPILOT_API).rstrip("/")

    async def fetch_models(self, account: dict[str, Any]) -> list[dict[str, Any]]:
        response = await self.client.get(
            f"{self.api_base(account)}/models", headers=self.headers(account["token"])
        )
        if response.status_code != 200:
            raise CopilotError(self.error_message(response), response.status_code, "upstream_models_error")
        return response.json().get("data", [])

    async def chat_completions(
        self, account: dict[str, Any], payload: dict[str, Any], stream: bool
    ) -> httpx.Response:
        request = self.client.build_request(
            "POST",
            f"{self.api_base(account)}/chat/completions",
            headers=self.headers(account["token"], "agent"),
            json=payload,
        )
        try:
            return await self.client.send(request, stream=stream)
        except httpx.RequestError as error:
            raise CopilotError(f"无法连接 Copilot：{error}", 502, "upstream_connection_error") from error

    async def embeddings(self, account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self.client.post(
                f"{self.api_base(account)}/embeddings",
                headers=self.headers(account["token"]),
                json=payload,
            )
        except httpx.RequestError as error:
            raise CopilotError(f"无法连接 Copilot：{error}", 502, "upstream_connection_error") from error
        if response.status_code != 200:
            raise CopilotError(self.error_message(response), response.status_code, "upstream_embeddings_error")
        return response.json()


def available_chat_models(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available = []
    for model in models:
        if model.get("policy", {}).get("state") == "disabled":
            continue
        endpoints = model.get("supported_endpoints")
        model_id = model.get("id", "")
        if endpoints and "/chat/completions" not in endpoints and not model_id.startswith("text-embedding"):
            continue
        available.append(model)
    return available

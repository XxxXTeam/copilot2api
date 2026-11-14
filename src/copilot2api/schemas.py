from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountCreate(BaseModel):
    name: str = Field(default="", max_length=80)
    token: str = Field(min_length=8, max_length=4096)
    enabled: bool = True

    @field_validator("token")
    @classmethod
    def clean_token(cls, value: str) -> str:
        value = value.strip()
        if value.startswith("Bearer "):
            value = value[7:].strip()
        return value


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    token: str | None = Field(default=None, min_length=8, max_length=4096)
    enabled: bool | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[dict[str, Any]]
    stream: bool = False


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    input: str | list[str] | list[int] | list[list[int]]


class AccountOut(BaseModel):
    id: str
    name: str
    login: str | None
    avatar_url: str | None
    plan: str | None
    sku: str | None
    enabled: bool
    status: str
    created_at: str
    updated_at: str
    last_used_at: str | None
    last_error: str | None
    request_count: int
    total_tokens: int
    active_requests: int = 0
    quotas: dict[str, Any] = {}
    quota_reset_date: str | None = None


class OverviewOut(BaseModel):
    accounts: int
    enabled_accounts: int
    healthy_accounts: int
    total_requests: int
    total_tokens: int
    today_requests: int
    quotas: dict[str, Any]
    recent_requests: list[dict[str, Any]]


class PoolConfigOut(BaseModel):
    strategy: Literal["round_robin", "least_used"]
    api_auth_required: bool
    admin_auth_required: bool
    request_timeout: float

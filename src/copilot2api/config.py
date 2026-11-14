from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = os.getenv("COPILOT2API_HOST", "127.0.0.1")
    port: int = int(os.getenv("COPILOT2API_PORT", "8000"))
    database_path: Path = Path(os.getenv("COPILOT2API_DATABASE", "data/copilot2api.db"))
    web_dist: Path = Path(os.getenv("COPILOT2API_WEB_DIST", "web/dist"))
    api_keys: tuple[str, ...] = tuple(
        key.strip() for key in os.getenv("COPILOT2API_API_KEYS", "").split(",") if key.strip()
    )
    admin_token: str = os.getenv("COPILOT2API_ADMIN_TOKEN", "")
    request_timeout: float = float(os.getenv("COPILOT2API_TIMEOUT", "180"))
    pool_strategy: str = os.getenv("COPILOT2API_POOL_STRATEGY", "round_robin")
    expose_docs: bool = _as_bool(os.getenv("COPILOT2API_DOCS"), True)

    @property
    def api_auth_required(self) -> bool:
        return bool(self.api_keys)


settings = Settings()

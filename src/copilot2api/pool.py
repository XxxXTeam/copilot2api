from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any

from .database import Database, utc_now
from .errors import CopilotError


class AccountPool:
    def __init__(self, database: Database, strategy: str = "round_robin") -> None:
        self.database = database
        self.strategy = strategy if strategy in {"round_robin", "least_used"} else "round_robin"
        self._cursor = 0
        self._lock = asyncio.Lock()
        self._active: defaultdict[str, int] = defaultdict(int)

    async def acquire(self) -> dict[str, Any]:
        async with self._lock:
            accounts = await self.database.list_accounts()
            now = time.time()
            candidates = [
                account for account in accounts
                if account["enabled"] and float(account["cooldown_until"]) <= now
            ]
            if not candidates:
                raise CopilotError("账号池中没有可用账号，请添加或启用账号", 503, "no_available_accounts")
            if self.strategy == "least_used":
                candidates.sort(key=lambda item: (item["request_count"], self._active[item["id"]], item["created_at"]))
                account = candidates[0]
            else:
                candidates.sort(key=lambda item: item["created_at"])
                account = candidates[self._cursor % len(candidates)]
                self._cursor += 1
            self._active[account["id"]] += 1
            return account

    async def release(self, account_id: str) -> None:
        async with self._lock:
            self._active[account_id] = max(0, self._active[account_id] - 1)

    def active_count(self, account_id: str) -> int:
        return self._active[account_id]

    async def mark_failure(self, account: dict[str, Any], status_code: int, message: str) -> None:
        cooldown = 0.0
        status = "error"
        if status_code == 429:
            cooldown = time.time() + 60
            status = "rate_limited"
        elif status_code in {401, 403}:
            cooldown = time.time() + 300
            status = "unauthorized"
        elif status_code >= 500:
            cooldown = time.time() + 20
        await self.database.update_account(
            account["id"], status=status, last_error=message[:1000], cooldown_until=cooldown
        )

    async def mark_success(self, account_id: str) -> None:
        await self.database.update_account(
            account_id, status="active", last_error=None, cooldown_until=0
        )

    async def public_accounts(self) -> list[dict[str, Any]]:
        accounts = await self.database.list_accounts()
        return [self.public_account(account) for account in accounts]

    def public_account(self, account: dict[str, Any]) -> dict[str, Any]:
        hidden = {"token", "endpoints", "cooldown_until"}
        result = {key: value for key, value in account.items() if key not in hidden}
        result["active_requests"] = self._active[account["id"]]
        return result

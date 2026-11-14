from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    token TEXT NOT NULL,
    login TEXT,
    avatar_url TEXT,
    plan TEXT,
    sku TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_used_at TEXT,
    last_error TEXT,
    cooldown_until REAL NOT NULL DEFAULT 0,
    request_count INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    quotas_json TEXT NOT NULL DEFAULT '{}',
    quota_reset_date TEXT,
    endpoints_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT,
    created_at TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    success INTEGER NOT NULL,
    error TEXT,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_request_logs_created_at ON request_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_accounts_enabled ON accounts(enabled, status);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    async def initialize(self) -> None:
        def init() -> None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(SCHEMA)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

        await asyncio.to_thread(init)

    async def create_account(self, token: str, name: str, enabled: bool, profile: dict[str, Any] | None = None) -> dict[str, Any]:
        account_id = uuid.uuid4().hex
        now = utc_now()
        profile = profile or {}

        def create() -> dict[str, Any]:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO accounts
                    (id, name, token, login, avatar_url, plan, sku, enabled, created_at, updated_at,
                     quotas_json, quota_reset_date, endpoints_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        account_id, name, token, profile.get("login"), profile.get("avatar_url"),
                        profile.get("copilot_plan"), profile.get("access_type_sku"), int(enabled), now, now,
                        json.dumps(profile.get("quota_snapshots", {})), profile.get("quota_reset_date_utc") or profile.get("quota_reset_date"),
                        json.dumps(profile.get("endpoints", {})),
                    ),
                )
            return self.get_account_sync(account_id)

        return await asyncio.to_thread(create)

    def get_account_sync(self, account_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError(account_id)
        return self._account_dict(row)

    async def get_account(self, account_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self.get_account_sync, account_id)

    async def list_accounts(self) -> list[dict[str, Any]]:
        def list_all() -> list[dict[str, Any]]:
            with self._connect() as connection:
                rows = connection.execute("SELECT * FROM accounts ORDER BY created_at").fetchall()
            return [self._account_dict(row) for row in rows]

        return await asyncio.to_thread(list_all)

    async def update_account(self, account_id: str, **values: Any) -> dict[str, Any]:
        allowed = {
            "name", "token", "enabled", "login", "avatar_url", "plan", "sku", "status",
            "last_used_at", "last_error", "cooldown_until", "request_count", "total_tokens",
            "quotas_json", "quota_reset_date", "endpoints_json",
        }
        values = {key: value for key, value in values.items() if key in allowed}
        values["updated_at"] = utc_now()

        def update() -> dict[str, Any]:
            assignments = ", ".join(f"{key}=?" for key in values)
            with self._connect() as connection:
                cursor = connection.execute(
                    f"UPDATE accounts SET {assignments} WHERE id=?",
                    (*values.values(), account_id),
                )
                if cursor.rowcount == 0:
                    raise KeyError(account_id)
            return self.get_account_sync(account_id)

        return await asyncio.to_thread(update)

    async def delete_account(self, account_id: str) -> None:
        def delete() -> None:
            with self._connect() as connection:
                cursor = connection.execute("DELETE FROM accounts WHERE id=?", (account_id,))
                if cursor.rowcount == 0:
                    raise KeyError(account_id)

        await asyncio.to_thread(delete)

    async def record_request(
        self,
        account_id: str,
        model: str,
        usage: dict[str, Any] | None,
        success: bool,
        error: str | None = None,
    ) -> None:
        usage = usage or {}
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or prompt + completion)
        now = utc_now()

        def record() -> None:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO request_logs
                    (account_id, created_at, model, prompt_tokens, completion_tokens, total_tokens, success, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (account_id, now, model, prompt, completion, total, int(success), error),
                )
                connection.execute(
                    """UPDATE accounts SET request_count=request_count+1, total_tokens=total_tokens+?,
                    last_used_at=?, updated_at=? WHERE id=?""",
                    (total, now, now, account_id),
                )

        await asyncio.to_thread(record)

    async def overview(self) -> dict[str, Any]:
        def read() -> dict[str, Any]:
            with self._connect() as connection:
                totals = connection.execute(
                    "SELECT COUNT(*) requests, COALESCE(SUM(total_tokens),0) tokens FROM request_logs WHERE success=1"
                ).fetchone()
                today = datetime.now(timezone.utc).date().isoformat()
                today_requests = connection.execute(
                    "SELECT COUNT(*) count FROM request_logs WHERE created_at>=? AND success=1", (today,)
                ).fetchone()["count"]
                recent = connection.execute(
                    """SELECT l.id, l.created_at, l.model, l.total_tokens, l.success, l.error,
                    COALESCE(a.name, a.login, '已删除账号') account_name
                    FROM request_logs l LEFT JOIN accounts a ON a.id=l.account_id
                    ORDER BY l.id DESC LIMIT 12"""
                ).fetchall()
            return {
                "total_requests": totals["requests"],
                "total_tokens": totals["tokens"],
                "today_requests": today_requests,
                "recent_requests": [dict(row) for row in recent],
            }

        return await asyncio.to_thread(read)

    @staticmethod
    def _account_dict(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["enabled"] = bool(result["enabled"])
        result["quotas"] = json.loads(result.pop("quotas_json") or "{}")
        result["endpoints"] = json.loads(result.pop("endpoints_json") or "{}")
        return result

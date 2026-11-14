from __future__ import annotations

from typing import Any


class CopilotError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 502,
        code: str = "copilot_error",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


def openai_error(message: str, status_code: int, code: str = "copilot_error") -> dict[str, Any]:
    return {
        "error": {
            "message": message,
            "type": "invalid_request_error" if status_code < 500 else "api_error",
            "param": None,
            "code": code,
        }
    }

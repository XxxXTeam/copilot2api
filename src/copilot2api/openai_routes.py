from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .auth import require_api_key
from .copilot import available_chat_models
from .errors import CopilotError
from .schemas import ChatCompletionRequest, EmbeddingRequest

router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
RETRYABLE_STATUSES = {401, 403, 408, 409, 429, 500, 502, 503, 504}


async def _account_attempts(request: Request) -> int:
    accounts = await request.app.state.database.list_accounts()
    return min(max(len(accounts), 1), 6)


@router.get("/models")
async def list_models(request: Request) -> dict[str, Any]:
    pool = request.app.state.pool
    client = request.app.state.copilot
    last_error: CopilotError | None = None
    for _ in range(await _account_attempts(request)):
        account = await pool.acquire()
        try:
            models = available_chat_models(await client.fetch_models(account))
            await pool.mark_success(account["id"])
            return {
                "object": "list",
                "data": [
                    {
                        "id": model["id"],
                        "object": "model",
                        "created": 0,
                        "owned_by": model.get("vendor", "github-copilot").lower().replace(" ", "-"),
                    }
                    for model in models
                ],
            }
        except CopilotError as error:
            last_error = error
            await pool.mark_failure(account, error.status_code, error.message)
        finally:
            await pool.release(account["id"])
    raise last_error or CopilotError("无法获取模型列表", 503, "models_unavailable")


@router.post("/chat/completions")
async def chat_completions(body: ChatCompletionRequest, request: Request) -> Any:
    pool = request.app.state.pool
    client = request.app.state.copilot
    database = request.app.state.database
    payload = body.model_dump(exclude_none=True)
    if body.stream:
        payload.setdefault("stream_options", {})["include_usage"] = True
    last_error: CopilotError | None = None

    for _ in range(await _account_attempts(request)):
        account = await pool.acquire()
        response = None
        try:
            response = await client.chat_completions(account, payload, body.stream)
            if response.status_code != 200:
                await response.aread()
                message = client.error_message(response)
                await response.aclose()
                await pool.mark_failure(account, response.status_code, message)
                await database.record_request(account["id"], body.model, None, False, message)
                last_error = CopilotError(message, response.status_code, "upstream_chat_error")
                if response.status_code not in RETRYABLE_STATUSES:
                    raise last_error
                await pool.release(account["id"])
                continue

            await pool.mark_success(account["id"])
            if not body.stream:
                content = await response.aread()
                await response.aclose()
                result = json.loads(content)
                await database.record_request(account["id"], body.model, result.get("usage"), True)
                await pool.release(account["id"])
                return JSONResponse(result)

            async def stream_response() -> AsyncGenerator[str, None]:
                usage = None
                buffer = ""
                succeeded = False
                try:
                    async for chunk in response.aiter_text():
                        yield chunk
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if data == "[DONE]":
                                succeeded = True
                            elif data.startswith("{"):
                                try:
                                    event = json.loads(data)
                                    usage = event.get("usage") or usage
                                except json.JSONDecodeError:
                                    pass
                    succeeded = True
                finally:
                    await response.aclose()
                    await database.record_request(account["id"], body.model, usage, succeeded)
                    await pool.release(account["id"])

            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        except CopilotError as error:
            await pool.release(account["id"])
            if response is None:
                await pool.mark_failure(account, error.status_code, error.message)
                if error.status_code in RETRYABLE_STATUSES:
                    last_error = error
                    continue
            raise
        except (OSError, ValueError) as error:
            if response is not None:
                await response.aclose()
            await pool.release(account["id"])
            await pool.mark_failure(account, 502, str(error))
            last_error = CopilotError(f"Copilot 响应处理失败：{error}", 502, "invalid_upstream_response")
        except Exception:
            if response is not None:
                await response.aclose()
            await pool.release(account["id"])
            raise

    raise last_error or CopilotError("所有 Copilot 账号均不可用", 503, "all_accounts_unavailable")


@router.post("/embeddings")
async def embeddings(body: EmbeddingRequest, request: Request) -> dict[str, Any]:
    pool = request.app.state.pool
    account = await pool.acquire()
    try:
        result = await request.app.state.copilot.embeddings(account, body.model_dump(exclude_none=True))
        await pool.mark_success(account["id"])
        usage = result.get("usage", {})
        await request.app.state.database.record_request(
            account["id"], body.model,
            {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            True,
        )
        return result
    except CopilotError as error:
        await pool.mark_failure(account, error.status_code, error.message)
        raise
    finally:
        await pool.release(account["id"])

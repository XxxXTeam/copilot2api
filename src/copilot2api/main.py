from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from .admin_routes import router as admin_router
from .config import Settings
from .copilot import CopilotClient
from .database import Database
from .errors import CopilotError, openai_error
from .openai_routes import router as openai_router
from .pool import AccountPool


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(settings.database_path)
        await database.initialize()
        copilot = CopilotClient(settings.request_timeout)
        app.state.settings = settings
        app.state.database = database
        app.state.copilot = copilot
        app.state.pool = AccountPool(database, settings.pool_strategy)
        try:
            yield
        finally:
            await copilot.close()

    app = FastAPI(
        title="copilot2api",
        version="0.1.0",
        description="GitHub Copilot 账号池与 OpenAI 兼容接口",
        docs_url="/docs" if settings.expose_docs else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    @app.exception_handler(CopilotError)
    async def handle_copilot_error(request: Request, error: CopilotError) -> JSONResponse:
        return JSONResponse(openai_error(error.message, error.status_code, error.code), error.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            openai_error("请求参数无效", 422, "validation_error") | {"details": error.errors()},
            422,
        )

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "copilot2api"}

    app.include_router(admin_router)
    app.include_router(openai_router)

    @app.get("/{path:path}", include_in_schema=False, response_model=None)
    async def frontend(path: str):
        dist = settings.web_dist.resolve()
        index = dist / "index.html"
        if not index.is_file():
            if path:
                return JSONResponse(openai_error("页面不存在", 404, "not_found"), 404)
            return JSONResponse(
                {
                    "name": "copilot2api",
                    "version": "0.1.0",
                    "message": "管理界面尚未构建，请运行 cd web && bun install && bun run build",
                    "docs": "/docs" if settings.expose_docs else None,
                }
            )
        requested = (dist / path).resolve() if path else index
        if path and requested.is_file() and dist in requested.parents:
            return FileResponse(requested)
        return FileResponse(index)

    return app


app = create_app()

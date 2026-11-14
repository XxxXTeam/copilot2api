__version__ = "0.1.0"


def main() -> None:
    import uvicorn

    from .config import settings

    uvicorn.run(
        "copilot2api.main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )

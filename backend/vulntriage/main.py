"""VulnTriage FastAPI application entry point.

``create_app`` wires the database, the GitHub reader and the scan worker. Tests
pass their own session factory and reader (and ``run_worker=False``); the
module-level ``app`` opens nothing until the server starts (lifespan).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.assets import router as assets_router
from vulntriage.db.session import create_db_engine, create_session_factory
from vulntriage.ingest.github import GitHubReader, RepositoryReader
from vulntriage.worker import ScanWorker


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """The contract ``Error`` shape. Nothing the client sent is echoed back."""
    return JSONResponse(
        status_code=422,
        content={"code": "validation", "message": "The request is invalid."},
    )


def create_app(
    session_factory: sessionmaker[Session] | None = None,
    reader: RepositoryReader | None = None,
    run_worker: bool = True,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = None
        factory = session_factory
        if factory is None:
            engine = create_db_engine()
            factory = create_session_factory(engine)
        app.state.session_factory = factory
        worker: ScanWorker | None = None
        if run_worker:
            worker = ScanWorker(factory, reader or GitHubReader())
            worker.start()
        app.state.worker = worker
        try:
            yield
        finally:
            if worker is not None:
                worker.stop()
            if engine is not None:
                engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.session_factory = session_factory
    app.state.worker = None
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(assets_router)
    return app


app = create_app()

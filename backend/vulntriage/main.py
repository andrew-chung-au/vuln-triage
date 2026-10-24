"""VulnTriage FastAPI application entry point.

``create_app`` wires the database, the GitHub reader and the scan worker. Tests
pass their own session factory and reader (and ``run_worker=False``); the
module-level ``app`` opens nothing until the server starts (lifespan).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy.orm import Session, sessionmaker

from vulntriage.api.assets import router as assets_router
from vulntriage.api.auth import router as auth_router
from vulntriage.api.findings import router as findings_router
from vulntriage.api.security import LoginThrottle
from vulntriage.api.service import router as service_router
from vulntriage.db.session import create_db_engine, create_session_factory
from vulntriage.ingest.github import GitHubReader, RepositoryReader
from vulntriage.observability.metrics import setup_metrics
from vulntriage.observability.tracing import setup_tracing
from vulntriage.scheduler import Scheduler
from vulntriage.worker import ScanWorker


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """The contract ``Error`` shape. Nothing the client sent is echoed back."""
    return JSONResponse(
        status_code=422,
        content={"code": "validation", "message": "The request is invalid."},
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render HTTPException as the contract ``Error`` shape ``{code, message}``.

    A route raises ``HTTPException(detail={"code", "message"})``; a bare string
    detail (or any non-dict) falls back to a generic message for that status.
    """
    assert isinstance(exc, HTTPException)
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        content = {"code": detail["code"], "message": detail["message"]}
    else:
        content = {"code": _CODE_FOR_STATUS.get(exc.status_code, "error"),
                   "message": "The request could not be completed."}
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)


_CODE_FOR_STATUS = {
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation",
}


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
            # SQLAlchemy auto-instrumentation: DB spans nested under the journey.
            # db.statement is NOT on the allowlist, so it is dropped in code and
            # again at the Collector (task 24), so raw SQL never leaves telemetry.
            SQLAlchemyInstrumentor().instrument(engine=engine)
            factory = create_session_factory(engine)
        app.state.session_factory = factory
        worker: ScanWorker | None = None
        scheduler: Scheduler | None = None
        if run_worker:
            worker = ScanWorker(factory, reader or GitHubReader())
            worker.start()
            # The daily refresh + re-scan (task 38). It runs catch-up at start
            # then ticks on a cadence; it uses app.state's feed clients when set.
            scheduler = Scheduler(
                factory,
                worker=worker,
                kev_client=getattr(app.state, "kev_client", None),
                epss_client=getattr(app.state, "epss_client", None),
            )
            scheduler.start()
        app.state.worker = worker
        app.state.scheduler = scheduler
        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.stop()
            if worker is not None:
                worker.stop()
            if engine is not None:
                engine.dispose()

    # OpenTelemetry (task 23): install the SDK providers before the app is
    # built. Export is a no-op without a Collector endpoint (A40), but real span
    # contexts are always created, so the journey trace, metrics and the
    # notification.enqueue traceparent work in every configuration.
    setup_tracing()
    setup_metrics()

    # The app is served behind a reverse proxy at /api, which strips the prefix,
    # so routes stay mounted at /findings, /assets, etc. and the tests are
    # unaffected. The /api base lives in openapi.yaml's servers.url; the
    # FastAPI(root_path=...) constructor arg is deprecated in this version, so
    # it is not set here (it was only cosmetic for the self-served /docs).
    app = FastAPI(lifespan=lifespan)
    # FastAPI auto-instrumentation: HTTP spans with the allowlisted http.* attrs.
    FastAPIInstrumentor.instrument_app(app)
    app.state.session_factory = session_factory
    app.state.worker = None
    app.state.scheduler = None
    app.state.login_throttle = LoginThrottle()
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.include_router(auth_router)
    app.include_router(assets_router)
    app.include_router(findings_router)
    app.include_router(service_router)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        """Infrastructure liveness probe, outside the OpenAPI contract.

        Mounted at ``/health`` on the app. The container health check calls it
        directly (``:8000/health``); through the reverse proxy it is reached at
        ``/api/health`` (the proxy strips ``/api``). It needs no credential and
        returns no VulnTriage data. The task-14 conformance test excludes
        ``/health`` by name (``_docs/api.md``).
        """
        return {"status": "ok"}

    return app


app = create_app()

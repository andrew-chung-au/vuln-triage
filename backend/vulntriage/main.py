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
from vulntriage.ingest.feeds import build_feed_clients
from vulntriage.ingest.github import RepositoryReader
from vulntriage.ingest.settings import get_feeds_mode, require_feeds_allowed
from vulntriage.mail.delivery import DeliveryWorker
from vulntriage.observability.logs import setup_logging
from vulntriage.observability.metrics import set_overdue_source, setup_metrics
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
        # Wire the US-14 overdue gauge (task 26) to the live session factory.
        # setup_metrics ran at app construction (below), before the DB existed,
        # so the gauge emitted only the heartbeat until now. From here it reads
        # stored job state each time Prometheus scrapes.
        set_overdue_source(factory)
        # Feed clients (task 40 / #172): build OSV/KEV/EPSS/GitHub from VT_FEEDS
        # (live by default; fixtures replays the committed fixtures for Compose/
        # CI). require_feeds_allowed validated the config at create_app time and
        # fails closed outside dev/test, so this just reads the mode. A test that
        # injected its own reader keeps it; otherwise the feeds' reader is used,
        # so a deployed scan actually matches/enriches/ranks (the gap #172 fixes).
        feeds = build_feed_clients(get_feeds_mode())
        app.state.kev_client = feeds.kev
        app.state.epss_client = feeds.epss
        worker: ScanWorker | None = None
        scheduler: Scheduler | None = None
        delivery: DeliveryWorker | None = None
        if run_worker:
            worker = ScanWorker(
                factory,
                reader or feeds.reader,
                osv_client=feeds.osv,
                kev_client=feeds.kev,
                epss_client=feeds.epss,
            )
            worker.start()
            # The daily refresh + re-scan (task 38). It runs catch-up at start
            # then ticks on a cadence; it uses app.state's feed clients.
            scheduler = Scheduler(
                factory,
                worker=worker,
                kev_client=getattr(app.state, "kev_client", None),
                epss_client=getattr(app.state, "epss_client", None),
            )
            scheduler.start()
            # The owner-notification delivery worker (task 37). It builds its
            # transport from the mail settings on first use, so a missing
            # MAIL_SENDER holds the job rather than crashing the worker.
            delivery = DeliveryWorker(factory)
            delivery.start()
        app.state.worker = worker
        app.state.scheduler = scheduler
        app.state.delivery_worker = delivery
        try:
            yield
        finally:
            # Stop the gauge reading a factory whose engine is about to be
            # disposed; it falls back to the heartbeat-only series.
            set_overdue_source(None)
            if delivery is not None:
                delivery.stop()
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
    setup_logging()

    # Validate the feed-source configuration at construction (task 40 / #172):
    # VT_FEEDS must be live/fixtures (unknown value errors, no silent fall-back),
    # and fixtures mode is refused unless DEPLOYMENT_ENVIRONMENT is explicitly
    # dev/test (fail closed). A misconfiguration stops start-up here rather than
    # quietly hitting live feeds or shipping fixtures to production.
    require_feeds_allowed()

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
    app.state.delivery_worker = None
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

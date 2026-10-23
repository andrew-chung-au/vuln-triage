# Backend image (issue #137, task 15): multi-stage, non-root.
#
# Stage 1 builds the locked virtual environment with uv; stage 2 is a slim
# runtime that copies the venv and the app, runs as a non-root user, and serves
# uvicorn on 0.0.0.0. The same image runs the migrations step in Compose
# (command override: `alembic upgrade head`).

# --- build stage -----------------------------------------------------------
FROM python:3.12-slim AS build

# uv, pinned to the project's version (matches .devcontainer/setup.sh).
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Install dependencies first (cached layer), then the project. Only the files
# the resolver needs are copied in this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

# The application code and the Alembic config/migrations.
COPY vulntriage ./vulntriage
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --locked --no-dev

# --- runtime stage ---------------------------------------------------------
FROM python:3.12-slim AS runtime

# Non-root user.
RUN useradd --create-home --uid 10001 appuser

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/vulntriage /app/vulntriage
COPY --from=build /app/alembic.ini /app/alembic.ini
COPY --from=build /app/migrations /app/migrations

USER appuser

EXPOSE 8000

# Listens on 0.0.0.0 so the frontend container and the host can reach it.
CMD ["uvicorn", "vulntriage.main:app", "--host", "0.0.0.0", "--port", "8000"]

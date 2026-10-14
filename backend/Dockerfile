# syntax=docker/dockerfile:1
# Backend image — the single Section 16.1 "backend image" behind the
# `backend`, `migrate`, `worker` and `beat` Compose services (WP-1.1,
# MT-1.1-05). One image, configured only by environment (NFR-06): the
# dev/prod split lives in settings selection, never in the image.
#
# Layering (Section 16.1 image basis; cached manifests first):
#   1. uv (pinned to the CI toolchain version — RISK-15 cross-host drift)
#   2. dependency install from the lockfile (changes rarely)
#   3. application source
#
# `UV_PROJECT_ENVIRONMENT=/opt/venv` keeps the virtualenv OUTSIDE /app: the
# compose dev overlay bind-mounts the repo's backend/ at /app (hot reload),
# which would otherwise mask the installed environment.
FROM ghcr.io/astral-sh/uv:0.12.10 AS uv-bin
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=apps.core.settings.prod

WORKDIR /app

COPY --from=uv-bin /uv /usr/local/bin/uv

# Dependency layer: only the lockfile matters here, so source edits reuse it.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# pg_dump for the Section 9.9 backup trigger (WP-6.2). The dump runs in the
# worker container against the Postgres 16 service, and pg_dump's major must
# be >= the server's — Debian's own repository ships an older client, so the
# client comes from the PGDG apt repository pinned to the server major.
# Installed in the shared backend image (one image per Section 16.1) so any
# backend-family container can take or restore a dump.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg; \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg; \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt trixie-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends postgresql-client-16; \
    rm -rf /var/lib/apt/lists/*

# Application source (a .dockerignore keeps caches, venvs and env files out —
# Section 20.4 item 3: no secrets or host paths enter the image).
COPY . .

# The project itself is not packaged (no build backend); this is a no-op now
# and stays correct if a build backend is added later.
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Section 6.6: ASGI via Uvicorn. `--no-access-log`: request lines are the
# backend's structured JSON pipeline (Section 17; MT-1.1-02).
CMD ["python", "-m", "uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

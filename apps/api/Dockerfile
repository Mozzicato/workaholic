# syntax=docker/dockerfile:1.7
# One image, two services: the API (default CMD) and the Celery worker (command override).

FROM python:3.12.14-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

# Dependencies first, so source changes don't invalidate the dependency layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# Chromium prints the PDFs (PRD section 21). Baked into the image, so a starting container
# never downloads a browser on its way up.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN /app/.venv/bin/playwright install --only-shell chromium

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app


FROM python:3.12.14-slim-trixie AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# Chromium's shared libraries, and real font faces: without fonts a PDF renders as empty boxes.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends \
      fonts-dejavu-core \
      fonts-liberation2 \
      libasound2 \
      libatk-bridge2.0-0 \
      libatk1.0-0 \
      libatspi2.0-0 \
      libcairo2 \
      libcups2 \
      libdbus-1-3 \
      libdrm2 \
      libgbm1 \
      libglib2.0-0 \
      libnspr4 \
      libnss3 \
      libpango-1.0-0 \
      libx11-6 \
      libxcb1 \
      libxcomposite1 \
      libxdamage1 \
      libxext6 \
      libxfixes3 \
      libxkbcommon0 \
      libxrandr2 \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 workaholic \
 && useradd --system --uid 10001 --gid workaholic --no-create-home --shell /usr/sbin/nologin workaholic

WORKDIR /app
COPY --from=builder --chown=root:root /app /app
COPY --from=builder --chown=root:root /opt/playwright /opt/playwright

USER workaholic
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

# Worker: celery -A app.workers.celery_app worker --loglevel INFO
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

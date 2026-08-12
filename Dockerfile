FROM node:24-bookworm-slim@sha256:03eae3ef7e88a9de535496fb488d67e02b9d96a063a8967bae657744ecd513f2 AS frontend-builder

WORKDIR /build/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


FROM python:3.12-slim@sha256:520153e2deb359602c9cffd84e491e3431d76e7bf95a3255c9ce9433b76ab99a AS python-builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_NO_CACHE=1
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY config ./config
COPY main.py README.md .env.example ./
COPY docker ./docker
COPY --from=frontend-builder /build/web/dist ./web/dist


FROM python:3.12-slim@sha256:520153e2deb359602c9cffd84e491e3431d76e7bf95a3255c9ce9433b76ab99a AS runtime

ARG APP_UID=1000
ARG APP_GID=1000
ARG APP_VERSION=1.0.2
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="Material Bin" \
    org.opencontainers.image.description="An open-source Pastebin with Material Design, encrypted storage, file upload, and sharing." \
    org.opencontainers.image.source="https://github.com/FIFCOM/MaterialBin" \
    org.opencontainers.image.version="${APP_VERSION}" \
    org.opencontainers.image.revision="${VCS_REF}" \
    org.opencontainers.image.created="${BUILD_DATE}"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=false
ENV VERSION="${APP_VERSION}"
ENV PATH="/app/.venv/bin:${PATH}"
ENV HOME="/app"

RUN groupadd --gid "${APP_GID}" appuser \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --home-dir /app --shell /usr/sbin/nologin --no-create-home appuser

WORKDIR /app

COPY --from=python-builder --chown=appuser:appuser /app /app

RUN chown appuser:appuser /app \
    && mkdir -p /app/data \
    && chmod +x /app/docker/entrypoint.sh \
    && chmod +x /app/docker/cleanup-runner.sh \
    && chmod +x /app/docker/runtime-common.sh

EXPOSE 8000

USER appuser

ENTRYPOINT ["/app/docker/entrypoint.sh"]

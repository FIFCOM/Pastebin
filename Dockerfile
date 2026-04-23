FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /build/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY config ./config
COPY web ./web
COPY main.py README.md .env.example ./
COPY docker ./docker
COPY --from=frontend-builder /build/web/dist ./web/dist

RUN chmod +x /app/docker/entrypoint.sh
RUN chmod +x /app/docker/cleanup-runner.sh
RUN chmod +x /app/docker/runtime-common.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]

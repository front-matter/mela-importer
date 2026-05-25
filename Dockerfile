# syntax=docker/dockerfile:1.5
FROM python:3.14-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.10.10 /uv /uvx /bin/

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv venv $VIRTUAL_ENV
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

FROM python:3.14-slim-trixie AS runtime

LABEL maintainer="Front Matter <info@front-matter.de>"
LABEL org.opencontainers.image.source="https://github.com/front-matter/mela-importer"
LABEL org.opencontainers.image.licenses="AGPL-3.0"
LABEL org.opencontainers.image.title="Mela → Mealie bulk importer"
LABEL org.opencontainers.image.description="Import recipes from Mela to Mealie."

WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY app/mela_importer.py ./

ENTRYPOINT ["python", "mela_importer.py"]

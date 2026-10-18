FROM python:3.12-slim AS base

WORKDIR /app

# System deps for chromadb (sqlite3, build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --no-dev --frozen 2>/dev/null || uv pip install --system -r <(uv pip compile pyproject.toml)

# Copy config and templates
COPY config.example.yaml ./config.yaml
COPY templates/ ./templates/

# Data volumes for persistence
VOLUME ["/app/data"]

ENV PYTHONUNBUFFERED=1
ENV BOBOT_DATA_DIR=/app/data

ENTRYPOINT ["uv", "run", "python", "-m", "src.main"]

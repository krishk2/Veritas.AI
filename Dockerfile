# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

# System dependencies for OpenCV headless and multimedia processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory and non-root user (Hugging Face Spaces default UID 1000)
WORKDIR /app
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/app/.venv/bin:/home/user/.local/bin:$PATH \
    PYTHONPATH=/app/src:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Copy project specification, source code, and application entrypoint
COPY --chown=user:user pyproject.toml uv.lock* README.md ./
COPY --chown=user:user src/ ./src/
COPY --chown=user:user app.py ./

# Install project and all dependencies into virtual environment
USER user
RUN uv venv && uv sync --no-dev

# Expose default port (7860 for Hugging Face Spaces, or override via $PORT on Render/Railway)
EXPOSE 7860

# Start FastAPI application via uvicorn inside the uv environment
CMD ["sh", "-c", "uvicorn veritas.api:app --host 0.0.0.0 --port ${PORT:-7860}"]

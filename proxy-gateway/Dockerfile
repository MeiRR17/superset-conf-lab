# =============================================================================
# Proxy Gateway - Dockerfile
# =============================================================================
# Production-ready Docker image for the FastAPI proxy gateway.
# Uses Python 3.11 slim base with PostgreSQL client libraries.
# =============================================================================

FROM python:3.11-slim-bookworm

# =============================================================================
# Set environment variables
# =============================================================================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# =============================================================================
# Install system dependencies
# =============================================================================
# libpq-dev: PostgreSQL client library for psycopg2
# gcc: Required for compiling Python packages with C extensions
# libc-dev: C library headers
# =============================================================================
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        libc-dev \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Create non-root user for security
# =============================================================================
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# =============================================================================
# Set working directory
# =============================================================================
WORKDIR /app

# =============================================================================
# Install Python dependencies
# =============================================================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Copy application code
# =============================================================================
COPY main.py .
COPY models.py .

# =============================================================================
# Change ownership to non-root user
# =============================================================================
RUN chown -R appuser:appgroup /app

# =============================================================================
# Switch to non-root user
# =============================================================================
USER appuser

# =============================================================================
# Expose the application port
# =============================================================================
EXPOSE 8000

# =============================================================================
# Health check
# =============================================================================
# Verifies the application is responding to requests
# =============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# =============================================================================
# Run the application
# =============================================================================
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info", "--proxy-headers"]

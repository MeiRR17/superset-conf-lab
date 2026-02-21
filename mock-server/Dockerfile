# =============================================================================
# Mock Cisco Server - Dockerfile
# =============================================================================
# Production-ready Docker image for the FastAPI mock server.
# Uses Python 3.11 slim base for optimal size/performance balance.
# =============================================================================

FROM python:3.11-slim-bookworm

# =============================================================================
# Set environment variables
# =============================================================================
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disk
# PYTHONUNBUFFERED: Ensures Python output is sent straight to terminal (no buffering)
# PYTHONFAULTHANDLER: Dump Python traceback on segfault
# PIP_NO_CACHE_DIR: Disable pip cache to reduce image size
# PIP_DISABLE_PIP_VERSION_CHECK: Suppress pip upgrade warnings
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
# gcc and libc-dev may be needed for some Python packages with C extensions
# (though FastAPI/uvicorn typically don't need them, we include for safety)
# =============================================================================
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libc-dev \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Create non-root user for security
# =============================================================================
# Running as non-root is a Docker security best practice
# =============================================================================
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# =============================================================================
# Set working directory
# =============================================================================
WORKDIR /app

# =============================================================================
# Install Python dependencies
# =============================================================================
# Copy only requirements first to leverage Docker layer caching
# This prevents re-installing dependencies when code changes
# =============================================================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Copy application code
# =============================================================================
COPY main.py .

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
EXPOSE 8001

# =============================================================================
# Health check
# =============================================================================
# Verifies the application is responding to requests
# --start-period gives time for the app to initialize
# =============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# =============================================================================
# Run the application
# =============================================================================
# Use uvicorn with multiple workers for production load handling
# --host 0.0.0.0: Bind to all interfaces (required for Docker)
# --port 8001: Match the EXPOSE directive
# --workers: Multiple workers for concurrent request handling
# --log-level info: Appropriate for production visibility
# =============================================================================
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2", "--log-level", "info", "--proxy-headers"]

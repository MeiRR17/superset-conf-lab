# =============================================================================
# Telephony Load Monitoring System - Dockerfile
# =============================================================================
# Production-ready Docker image for the telephony monitoring system.
# Uses Python 3.11 slim base for optimal size/performance balance.
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
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libc-dev \
        libpq-dev \
        curl \
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
# Copy and install Python dependencies
# =============================================================================
# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Copy application code
# =============================================================================
COPY . .

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
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# =============================================================================
# Run the application
# =============================================================================
# Use uvicorn with multiple workers for production load handling
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info", "--proxy-headers"]

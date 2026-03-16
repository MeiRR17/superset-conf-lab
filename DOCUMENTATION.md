# Telephony Load Monitoring System - Complete Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [File-by-File Documentation](#file-by-file-documentation)
   - [Root Files](#root-files)
   - [Mock Server](#mock-server)
   - [Proxy Gateway](#proxy-gateway)
   - [Superset](#superset)
   - [Nginx](#nginx)
   - [PostgreSQL](#postgresql)
4. [Data Flow](#data-flow)
5. [Deployment Guide](#deployment-guide)
6. [API Reference](#api-reference)

---

## Project Overview

The Telephony Load Monitoring System is a production-grade MVP for monitoring telephony load from Cisco servers (CUCM, UCCX, CMS, IMP, Meeting Place). This microservices setup includes:

- **Mock Server** - Simulates Cisco UCCX and CUCM endpoints with realistic metrics
- **Proxy Gateway** - Collects metrics and stores in PostgreSQL
- **PostgreSQL** - Time-series metrics storage
- **Apache Superset** - Dashboards and visualization
- **Redis** - Caching layer for Superset
- **Nginx** - Reverse proxy and single entry point

---

## Architecture

```
┌─────────────┐
│   Nginx     │  Port 80 (Single Entry Point)
│  (Proxy)    │
└──────┬──────┘
       │
       ├──────────┬──────────┐
       ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Superset │ │  Proxy   │ │  Mock    │
│  Port    │ │ Gateway  │ │ Server   │
│  8088    │ │ Port     │ │ Port     │
│          │ │ 8000     │ │ 8001     │
└──────────┘ └────┬─────┘ └──────────┘
                  │
                  ▼
           ┌──────────┐
           │  PostgreSQL │ Port 5432
           │  (telephony_db + superset_db)
           └──────────┘
                  ▲
           ┌──────────┐
           │   Redis   │ Port 6379
           │  (Cache)  │
           └──────────┘
```

---

## File-by-File Documentation

### Root Files

#### `docker-compose.yml`
**Purpose**: Orchestrates all 6 microservices with proper networking, volumes, and health checks.

```yaml
# =============================================================================
# Telephony Load Monitoring System - Docker Compose Configuration
# =============================================================================
# This file orchestrates all 6 services of the Telephony Load Monitoring System:
#   1. PostgreSQL - Database for metrics and Superset metadata
#   2. Redis - Caching layer for Superset
#   3. Mock Server - Simulates Cisco UCCX and CUCM endpoints
#   4. Proxy Gateway - Collects metrics and stores in PostgreSQL
#   5. Superset - Apache Superset for dashboards and visualization
#   6. Nginx - Reverse proxy and single entry point
# =============================================================================
# =============================================================================
# Services Definition
# =============================================================================
services:

  # ===========================================================================
  # Service 1: PostgreSQL Database
  # ===========================================================================
  postgres:
    image: postgres:15-alpine
    container_name: telephony-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: telephony_db
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - telephony-network

  # ===========================================================================
  # Service 2: Redis Cache
  # ===========================================================================
  redis:
    image: redis:7-alpine
    container_name: telephony-redis
    restart: unless-stopped
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks:
      - telephony-network

  # ===========================================================================
  # Service 3: Mock Cisco Server
  # ===========================================================================
  mock-server:
    build:
      context: ./mock-server
      dockerfile: Dockerfile
    container_name: telephony-mock-server
    restart: unless-stopped
    environment:
      PYTHONUNBUFFERED: 1
      LOG_LEVEL: info
    ports:
      - "8001:8001"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    networks:
      - telephony-network

  # ===========================================================================
  # Service 4: Proxy Gateway
  # ===========================================================================
  proxy-gateway:
    build:
      context: ./proxy-gateway
      dockerfile: Dockerfile
    container_name: telephony-proxy-gateway
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/telephony_db
      MOCK_SERVER_URL: http://mock-server:8001
      ENABLE_POLLING: "true"
      POLLING_INTERVAL: "60"
      REQUEST_TIMEOUT: "10"
      PYTHONUNBUFFERED: 1
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      mock-server:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - telephony-network

  # ===========================================================================
  # Service 5: Apache Superset
  # ===========================================================================
  superset:
    build: ./superset
    container_name: telephony-superset
    restart: unless-stopped
    environment:
      SUPERSET_CONFIG_PATH: /app/pythonpath/superset_config.py
      DATABASE_URL: postgresql://postgres:password@postgres:5432/telephony_db
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: your-super-secret-key-change-in-production
    volumes:
      - ./superset/superset_config.py:/app/pythonpath/superset_config.py:ro
      - ./superset/superset-init.sh:/app/superset-init.sh:ro
      - superset_data:/app/superset_home
    command: ["/app/superset-init.sh"]
    ports:
      - "8088:8088"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - telephony-network

  # ===========================================================================
  # Service 6: Nginx Reverse Proxy (Optional but enabled)
  # ===========================================================================
  nginx:
    image: nginx:alpine
    container_name: telephony-nginx
    restart: unless-stopped
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      superset:
        condition: service_started
      proxy-gateway:
        condition: service_healthy
      mock-server:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost/nginx-health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - telephony-network

# =============================================================================
# Named Volumes for Data Persistence
# =============================================================================
volumes:
  # PostgreSQL data directory
  postgres_data:
    driver: local
  
  # Redis data directory
  redis_data:
    driver: local
  
  # Superset home directory (uploads, exports)
  superset_data:
    driver: local

# =============================================================================
# Docker Networks
# =============================================================================
networks:
  # Custom bridge network for service communication
  telephony-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

#### `README.md`
**Purpose**: Project overview, quick start, and usage instructions.

```markdown
# Telephony Load Monitoring System

A complete, production-grade local MVP for monitoring telephony load from Cisco servers using a microservices setup: a FastAPI mock server, a FastAPI proxy gateway collector, PostgreSQL for metrics storage, Apache Superset for dashboards, Redis for caching, and Nginx as a single entry reverse proxy.

## Architecture Overview

```
┌─────────────┐
│   Nginx     │  Port 80 (Single Entry Point)
│  (Proxy)    │
└──────┬──────┘
       │
       ├──────────┬──────────┐
       ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Superset │ │  Proxy   │ │  Mock    │
│  Port    │ │ Gateway  │ │ Server   │
│  8088    │ │ Port     │ │ Port     │
│          │ │ 8000     │ │ 8001     │
└──────────┘ └────┬─────┘ └──────────┘
                  │
                  ▼
           ┌──────────┐
           │  PostgreSQL │ Port 5432
           │  (telephony_db + superset_db)
           └──────────┘
                  ▲
           ┌──────────┐
           │   Redis   │ Port 6379
           │  (Cache)  │
           └──────────┘
```

## Tech Stack

- **Python 3.11** - FastAPI applications (Mock Server & Proxy Gateway)
- **PostgreSQL 15** - Time-series metrics and metadata storage
- **Apache Superset** - Business intelligence and visualization
- **Redis 7** - Caching and async task broker
- **Nginx** - Reverse proxy and load balancer
- **Docker & Docker Compose** - Container orchestration

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Ports 80, 5432, 6379, 8000, 8001, 8088 available

### Start the System

```bash
# Build and start all services
docker-compose up -d --build

# Wait for all services to be healthy
docker-compose ps

# View logs
docker-compose logs -f
```

### Access the Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Superset (Direct) | http://localhost:8088 | admin/admin |
| Proxy Gateway (Direct) | http://localhost:8000 | - |
| Mock Server (Direct) | http://localhost:8001 | - |
| Nginx (Single Entry) | http://localhost | - |
| PostgreSQL | localhost:5432 | postgres/password |
| Redis | localhost:6379 | - |

### Direct Port Access (for testing)

- Superset: http://localhost:8088
- Proxy Gateway: http://localhost:8000
- Mock Server: http://localhost:8001

## Project Structure

```
.
├── docker-compose.yml          # Orchestrates the microservices
├── README.md
├── .env.example                # Env template (optional)
├── postgres/
│   └── init.sql                # Creates telephony_db + superset_db + telephony_metrics
├── nginx/
│   └── nginx.conf               # Reverse proxy routes (/ -> superset, /api -> gateway, /mock -> mock)
├── mock-server/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                  # FastAPI mock endpoints
├── proxy-gateway/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── models.py                # TelephonyMetric -> telephony_metrics
│   └── main.py                  # Collector + polling
└── superset/
    ├── Dockerfile
    ├── superset_config.py
    └── superset-init.sh
```

## API Endpoints

### Proxy Gateway (Port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/collect` | Trigger manual metrics collection |
| GET | `/api/metrics/recent` | Get recent metrics from database |
| GET | `/api/metrics/summary` | Get metrics statistics |

### Mock Server (Port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/uccx/stats` | UCCX call center metrics |
| GET | `/api/cucm/system/stats` | CUCM system metrics |

## Database Schema

### telephony_metrics Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-incrementing ID |
| timestamp | TIMESTAMP WITH TIME ZONE | When metric was recorded |
| server_type | VARCHAR(50) | 'uccx' or 'cucm' |
| metric_name | VARCHAR(100) | e.g., 'active_agents', 'cpu_usage_percent' |
| metric_value | DOUBLE PRECISION | The measurement value |
| unit | VARCHAR(20) | 'count', 'percent', 'seconds', etc. |

## Configuration

### Environment Variables

All services can be configured via environment variables defined in `docker-compose.yml`:

#### PostgreSQL
- `POSTGRES_USER` - Database superuser (default: postgres)
- `POSTGRES_PASSWORD` - Database password (default: password)

#### Proxy Gateway
- `DATABASE_URL` - PostgreSQL connection string
- `MOCK_SERVER_URL` - URL of mock server
- `ENABLE_POLLING` - Enable automatic collection (true/false)
- `POLLING_INTERVAL` - Collection interval in seconds (default: 60)

#### Superset
- `DB_*` - Database connection settings
- `REDIS_*` - Redis connection settings
- `SUPERSET_SECRET_KEY` - Encryption key (change in production!)

## Usage

### Automatic Collection

The proxy-gateway automatically collects metrics every 60 seconds (configurable via `POLLING_INTERVAL`). No manual intervention required.

### Manual Collection

```bash
# Trigger immediate collection via API
curl http://localhost/api/collect

# Or using the direct port
curl http://localhost:8000/api/collect
```

### View Recent Metrics

```bash
# Get last 100 metrics
curl "http://localhost/api/metrics/recent?limit=100"

# Filter by server type
curl "http://localhost/api/metrics/recent?server_type=uccx"
```

### Create Superset Dashboards

1. Log in to Superset at http://localhost (admin/admin)
2. Navigate to **Data → Databases** → "Telephony Metrics" should be pre-configured
3. Go to **SQL Lab** to explore the `telephony_metrics` table
4. Create datasets and charts
5. Build dashboards with real-time telephony metrics

## Monitoring

### Health Checks

All services include Docker health checks:

```bash
# View service health
docker-compose ps

# Check individual service
docker-compose exec <service> <health-command>
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f <service-name>

# Example: proxy-gateway logs
docker-compose logs -f proxy-gateway
```

## Troubleshooting

### Services Not Starting

```bash
# Check for port conflicts
netstat -tlnp | grep -E '80|5432|6379|8000|8001|8088'

# View detailed logs
docker-compose logs --tail=100 <service-name>

# Restart specific service
docker-compose restart <service-name>
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose exec postgres pg_isready -U postgres

# Check proxy-gateway database connection
docker-compose exec proxy-gateway python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:password@postgres:5432/telephony_db')
print(engine.connect().execute('SELECT 1').fetchone())
"
```

### Reset Everything

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

## Production Considerations

### Security

1. **Change default passwords** - Update all `password` values in `docker-compose.yml`
2. **Generate new secret key** - Run `openssl rand -base64 42` for Superset
3. **Enable HTTPS** - Configure SSL certificates in Nginx
4. **Restrict ports** - Remove direct port mappings (5432, 6379, 8000-8088)
5. **Use Docker secrets** - Move sensitive data to Docker secrets

### Performance

1. **Add PostgreSQL connection pooling** - Configure PgBouncer
2. **Enable Superset query caching** - Already configured via Redis
3. **Scale horizontally** - Run multiple Superset and gateway instances
4. **Add monitoring** - Prometheus/Grafana for infrastructure metrics

### Backups

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres telephony_db > backup.sql

# Backup Superset metadata
docker-compose exec postgres pg_dump -U postgres superset_db > superset_backup.sql
```

## Development

### Adding New Metrics

1. Add new endpoint in `mock-server/main.py`
2. Update `proxy-gateway/main.py` to fetch and parse the new endpoint
3. The database schema is flexible - new metrics are stored automatically

### Modifying Database Schema

1. Edit `postgres/init.sql`
2. For existing databases, use migrations or manual ALTER TABLE commands

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues and questions:
- Open a GitHub issue
- Check existing troubleshooting section
- Review service logs with `docker-compose logs`
```

#### `.env.example`
**Purpose**: Template for environment variables (optional, not used by current compose setup).

```bash
# =============================================================================
# Telephony Load Monitoring System - Environment Variables Template
# =============================================================================
# Copy this file to .env and modify values as needed.
# Note: Current docker-compose.yml uses inline environment variables.
# =============================================================================

# =============================================================================
# Database Configuration
# =============================================================================
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=telephony_db

# =============================================================================
# Proxy Gateway Configuration
# =============================================================================
DATABASE_URL=postgresql://postgres:password@postgres:5432/telephony_db
MOCK_SERVER_URL=http://mock-server:8001
ENABLE_POLLING=true
POLLING_INTERVAL=60
REQUEST_TIMEOUT=10

# =============================================================================
# Superset Configuration
# =============================================================================
SUPERSET_SECRET_KEY=your-super-secret-key-change-in-production
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=postgres
DB_PORT=5432
DB_NAME=superset_db

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# =============================================================================
# Mock Server Configuration
# =============================================================================
PYTHONUNBUFFERED=1
LOG_LEVEL=info

# =============================================================================
# API Configuration
# =============================================================================
API_CORS_ORIGINS=["*"]
API_HOST=0.0.0.0
API_PORT=8000

# =============================================================================
# Feature Toggles (for future real API integration)
# =============================================================================
USE_REAL_CUCM=false
USE_REAL_UCCX=false
USE_REAL_CMS=false
USE_REAL_IMP=false
USE_REAL_MEETING_PLACE=false

# =============================================================================
# Real API Credentials (for future use)
# =============================================================================
CUCM_WSDL_URL=
CUCM_USERNAME=
CUCM_PASSWORD=

UCCX_WSDL_URL=
UCCX_USERNAME=
UCCX_PASSWORD=

CMS_REST_URL=
CMS_USERNAME=
CMS_PASSWORD=

IMP_REST_URL=
IMP_USERNAME=
IMP_PASSWORD=

MEETING_PLACE_REST_URL=
MEETING_PLACE_USERNAME=
MEETING_PLACE_PASSWORD=

# =============================================================================
# Scheduler Configuration
# =============================================================================
SCHEDULER_ENABLED=true
SCHEDULER_TIMEZONE=UTC
COLLECTION_INTERVAL_MINUTES=1

# =============================================================================
# Logging Configuration
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

### Mock Server

#### `mock-server/main.py`
**Purpose**: FastAPI application that simulates Cisco UCCX and CUCM endpoints with realistic, fluctuating metrics.

```python
# =============================================================================
# Mock Cisco Server - FastAPI Application
# =============================================================================
# This module simulates a Cisco telephony environment by providing mock endpoints
# that return realistic fluctuating metrics for:
#   - UCCX (Unified Contact Center Express) - Call center statistics
#   - CUCM (Cisco Unified Communications Manager) - System statistics
#
# The data fluctuates over time to simulate real-world load variations.
# =============================================================================

import random
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# =============================================================================
# FastAPI Application Configuration
# =============================================================================

app = FastAPI(
    title="Mock Cisco Telephony Server",
    description="Simulates Cisco UCCX and CUCM endpoints for load testing",
    version="1.0.0",
)

# Enable CORS for cross-origin requests (useful for dashboard integration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Health Check Endpoint
# =============================================================================

@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for container orchestration.
    Returns 200 OK when the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "mock-cisco-server"
    }


# =============================================================================
# UCCX (Unified Contact Center Express) Endpoints
# =============================================================================

@app.get("/api/uccx/stats", tags=["uccx"])
async def get_uccx_stats() -> Dict[str, Any]:
    """
    Returns simulated UCCX call center statistics.
    
    Metrics returned:
    - active_agents: Number of agents currently logged in and ready
    - calls_in_queue: Number of calls waiting in queue
    - avg_handle_time: Average time to handle a call (seconds)
    - service_level_percent: Percentage of calls answered within SLA
    
    Data fluctuates based on a simulated sine wave pattern to mimic
    realistic daily call center traffic patterns.
    """
    # Get current minute of day to create a cyclical pattern
    # This simulates higher call volumes during business hours
    minute_of_day = datetime.now().hour * 60 + datetime.now().minute
    
    # Create a cyclical pattern (sine wave) for realistic fluctuation
    # Peak activity at midday, lower in morning/evening
    daily_cycle = (1 + (minute_of_day % 480) / 480) * 0.5  # 8-hour cycle
    
    # Add randomness for realistic variation
    random_factor = random.uniform(0.7, 1.3)
    
    # Calculate fluctuating metrics
    base_agents = 50
    active_agents = int(base_agents * daily_cycle * random_factor)
    active_agents = max(10, min(100, active_agents))  # Clamp between 10-100
    
    base_queue = 25
    calls_in_queue = int(base_queue * daily_cycle * random.uniform(0.5, 1.5))
    calls_in_queue = max(0, min(50, calls_in_queue))  # Clamp between 0-50
    
    # Service level inversely correlates with queue depth
    service_level = max(70, 95 - (calls_in_queue * 0.5) + random.uniform(-5, 5))
    service_level = min(100, service_level)
    
    return {
        "server_type": "uccx",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "active_agents": {
                "value": active_agents,
                "unit": "count",
                "description": "Number of agents currently logged in"
            },
            "calls_in_queue": {
                "value": calls_in_queue,
                "unit": "count",
                "description": "Number of calls waiting in queue"
            },
            "avg_handle_time": {
                "value": round(random.uniform(120, 300), 1),  # 2-5 minutes
                "unit": "seconds",
                "description": "Average call handling time"
            },
            "service_level_percent": {
                "value": round(service_level, 1),
                "unit": "percent",
                "description": "Percentage of calls answered within SLA"
            },
            "abandoned_calls": {
                "value": int(calls_in_queue * random.uniform(0.05, 0.15)),
                "unit": "count",
                "description": "Calls abandoned while in queue"
            }
        }
    }


# =============================================================================
# CUCM (Cisco Unified Communications Manager) Endpoints
# =============================================================================

@app.get("/api/cucm/system/stats", tags=["cucm"])
async def get_cucm_stats() -> Dict[str, Any]:
    """
    Returns simulated CUCM system statistics.
    
    Metrics returned:
    - cpu_usage_percent: System CPU utilization
    - memory_usage_percent: System memory utilization
    - active_calls: Number of active voice calls
    - registered_phones: Number of registered endpoints
    - failed_calls: Number of failed call attempts
    
    CPU and memory usage fluctuate based on call volume to simulate
    real system resource correlation.
    """
    # Generate correlated metrics
    # More active calls = higher resource usage
    base_calls = 500
    active_calls = int(base_calls + random.uniform(-200, 300))
    active_calls = max(50, active_calls)
    
    # CPU correlates with call volume plus some baseline
    cpu_usage = 15 + (active_calls / 1000 * 30) + random.uniform(-5, 10)
    cpu_usage = max(5, min(95, cpu_usage))
    
    # Memory has a baseline plus call-dependent component
    memory_usage = 40 + (active_calls / 1000 * 20) + random.uniform(-3, 5)
    memory_usage = max(25, min(90, memory_usage))
    
    # Registered phones is relatively stable
    registered_phones = int(800 + random.uniform(-50, 50))
    
    # Failed calls correlate with load (higher load = slightly more failures)
    failure_rate = 0.01 + (cpu_usage / 1000)  # 1-10% based on load
    failed_calls = int(active_calls * failure_rate * random.uniform(0.5, 1.5))
    
    return {
        "server_type": "cucm",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "cpu_usage_percent": {
                "value": round(cpu_usage, 1),
                "unit": "percent",
                "description": "System CPU utilization"
            },
            "memory_usage_percent": {
                "value": round(memory_usage, 1),
                "unit": "percent",
                "description": "System memory utilization"
            },
            "active_calls": {
                "value": active_calls,
                "unit": "count",
                "description": "Number of active voice calls"
            },
            "registered_phones": {
                "value": registered_phones,
                "unit": "count",
                "description": "Registered IP phones/endpoints"
            },
            "failed_calls": {
                "value": failed_calls,
                "unit": "count",
                "description": "Failed call attempts in last interval"
            },
            "total_call_volume": {
                "value": int(active_calls * random.uniform(1.2, 2.0)),
                "unit": "count",
                "description": "Total calls processed (includes completed)"
            }
        }
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler to ensure all errors return JSON.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn when executed directly
    # In production, use: uvicorn main:app --host 0.0.0.0 --port 8001
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Disable reload in container environments
        log_level="info"
    )
```

#### `mock-server/requirements.txt`
**Purpose**: Python dependencies for the mock server FastAPI application.

```txt
# =============================================================================
# Mock Cisco Server - Python Dependencies
# =============================================================================
# These are the required packages for the FastAPI mock server that simulates
# Cisco UCCX and CUCM endpoints.
# =============================================================================

# FastAPI - Modern, fast web framework for building APIs
fastapi==0.104.1

# Uvicorn - ASGI server to run FastAPI
# Standard package includes uvloop and httptools for better performance
uvicorn[standard]==0.24.0

# Pydantic - Data validation using Python type hints (included with FastAPI)
# Used for request/response models
pydantic==2.5.2

# Python-dateutil - Useful for timestamp manipulation
python-dateutil==2.8.2
```

#### `mock-server/Dockerfile`
**Purpose**: Production-ready Docker image for the mock server with security best practices.

```dockerfile
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
```

---

### Proxy Gateway

#### `proxy-gateway/main.py`
**Purpose**: FastAPI application that collects metrics from mock server, transforms data, and persists to PostgreSQL with background polling.

```python
# =============================================================================
# Proxy Gateway - FastAPI Application
# =============================================================================
# This module serves as the central data collection gateway for the Telephony
# Load Monitoring System. It:
#   - Collects metrics from the mock Cisco servers (UCCX and CUCM)
#   - Transforms and normalizes the data
#   - Persists metrics to PostgreSQL via SQLAlchemy
#   - Provides a background polling mechanism for automatic collection
#   - Exposes REST API endpoints for manual collection and status checks
# =============================================================================

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Import our database models and utilities
from models import (
    TelephonyMetric,
    get_engine,
    get_session_maker,
    init_database,
    DatabaseSession
)

# =============================================================================
# Logging Configuration
# =============================================================================
# Configure structured logging for production observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration from Environment Variables
# =============================================================================
# These settings can be overridden via environment variables for flexibility
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/telephony_db"
)

MOCK_SERVER_URL = os.getenv(
    "MOCK_SERVER_URL",
    "http://mock-server:8001"  # Docker service name
)

# Polling interval in seconds (default: 60 seconds = 1 minute)
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))

# Enable/disable automatic background polling
ENABLE_POLLING = os.getenv("ENABLE_POLLING", "true").lower() == "true"

# Request timeout for mock server calls (seconds)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

# =============================================================================
# Global State
# =============================================================================
# These are initialized during application startup
engine = None
SessionLocal = None
polling_task = None
last_collection_time = None
metrics_collected_count = 0

# =============================================================================
# Application Lifespan (Startup/Shutdown Events)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle.
    
    Startup:
        - Initialize database engine
        - Create tables if they don't exist
        - Start background polling task (if enabled)
    
    Shutdown:
        - Cancel background polling task
        - Close database connections
    """
    global engine, SessionLocal, polling_task
    
    # ===========================
    # STARTUP
    # ===========================
    logger.info("=" * 60)
    logger.info("Proxy Gateway Starting Up")
    logger.info("=" * 60)
    
    # Initialize database connection
    logger.info(f"Connecting to database: {DATABASE_URL.replace('password', '***')}")
    engine = get_engine(DATABASE_URL)
    SessionLocal = get_session_maker(engine)
    
    # Initialize database schema
    logger.info("Initializing database schema...")
    init_database(engine)
    logger.info("Database schema ready")
    
    # Start background polling if enabled
    if ENABLE_POLLING:
        logger.info(f"Starting background polling (interval: {POLLING_INTERVAL}s)")
        polling_task = asyncio.create_task(polling_loop())
        logger.info("Background polling started")
    else:
        logger.info("Background polling is disabled")
    
    logger.info("Proxy Gateway is ready")
    logger.info("=" * 60)
    
    yield  # Application runs here
    
    # ===========================
    # SHUTDOWN
    # ===========================
    logger.info("=" * 60)
    logger.info("Proxy Gateway Shutting Down")
    logger.info("=" * 60)
    
    # Cancel polling task
    if polling_task:
        logger.info("Stopping background polling...")
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        logger.info("Background polling stopped")
    
    # Close database connections
    if engine:
        logger.info("Closing database connections...")
        engine.dispose()
        logger.info("Database connections closed")
    
    logger.info("Proxy Gateway shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Telephony Metrics Proxy Gateway",
    description="Collects metrics from Cisco servers and persists to PostgreSQL",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Database Dependency
# =============================================================================

def get_db() -> Session:
    """
    FastAPI dependency that provides a database session.
    Automatically closes session after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Data Collection Functions
# =============================================================================

def fetch_uccx_metrics() -> List[Dict[str, Any]]:
    """
    Fetch metrics from the mock UCCX server.
    
    Returns:
        List of metric dictionaries ready for database insertion.
    
    Raises:
        requests.RequestException: If API call fails.
    """
    url = f"{MOCK_SERVER_URL}/api/uccx/stats"
    logger.debug(f"Fetching UCCX metrics from: {url}")
    
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    
    server_type = data.get("server_type", "uccx")
    metrics_data = data.get("metrics", {})
    
    # Transform nested metrics into flat records
    metrics = []
    for metric_name, metric_info in metrics_data.items():
        metrics.append({
            "server_type": server_type,
            "metric_name": metric_name,
            "metric_value": metric_info["value"],
            "unit": metric_info["unit"]
        })
    
    logger.debug(f"Fetched {len(metrics)} UCCX metrics")
    return metrics


def fetch_cucm_metrics() -> List[Dict[str, Any]]:
    """
    Fetch metrics from the mock CUCM server.
    
    Returns:
        List of metric dictionaries ready for database insertion.
    
    Raises:
        requests.RequestException: If API call fails.
    """
    url = f"{MOCK_SERVER_URL}/api/cucm/system/stats"
    logger.debug(f"Fetching CUCM metrics from: {url}")
    
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    
    server_type = data.get("server_type", "cucm")
    metrics_data = data.get("metrics", {})
    
    # Transform nested metrics into flat records
    metrics = []
    for metric_name, metric_info in metrics_data.items():
        metrics.append({
            "server_type": server_type,
            "metric_name": metric_name,
            "metric_value": metric_info["value"],
            "unit": metric_info["unit"]
        })
    
    logger.debug(f"Fetched {len(metrics)} CUCM metrics")
    return metrics


def save_metrics_to_database(metrics: List[Dict[str, Any]]) -> int:
    """
    Save a list of metrics to PostgreSQL database.
    
    Args:
        metrics: List of metric dictionaries with keys:
                 server_type, metric_name, metric_value, unit
    
    Returns:
        Number of metrics saved.
    
    Raises:
        SQLAlchemyError: If database operation fails.
    """
    count = 0
    with DatabaseSession(SessionLocal) as db:
        for metric_data in metrics:
            metric = TelephonyMetric(
                server_type=metric_data["server_type"],
                metric_name=metric_data["metric_name"],
                metric_value=metric_data["metric_value"],
                unit=metric_data["unit"]
            )
            db.add(metric)
            count += 1
    
    logger.debug(f"Saved {count} metrics to database")
    return count


def collect_all_metrics() -> Dict[str, Any]:
    """
    Collect metrics from all sources and save to database.
    
    This is the main collection orchestrator that:
    1. Fetches UCCX metrics
    2. Fetches CUCM metrics
    3. Saves all metrics to database
    4. Returns summary of collection results
    
    Returns:
        Dictionary with collection results including:
        - success: Boolean indicating overall success
        - uccx_metrics_count: Number of UCCX metrics collected
        - cucm_metrics_count: Number of CUCM metrics collected
        - total_saved: Total metrics saved to database
        - errors: List of any errors encountered
        - timestamp: ISO format timestamp of collection
    """
    global last_collection_time, metrics_collected_count
    
    errors = []
    all_metrics = []
    uccx_count = 0
    cucm_count = 0
    
    logger.info("Starting metrics collection cycle...")
    
    # Collect UCCX metrics
    try:
        uccx_metrics = fetch_uccx_metrics()
        all_metrics.extend(uccx_metrics)
        uccx_count = len(uccx_metrics)
        logger.info(f"Collected {uccx_count} UCCX metrics")
    except requests.RequestException as e:
        error_msg = f"Failed to fetch UCCX metrics: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    # Collect CUCM metrics
    try:
        cucm_metrics = fetch_cucm_metrics()
        all_metrics.extend(cucm_metrics)
        cucm_count = len(cucm_metrics)
        logger.info(f"Collected {cucm_count} CUCM metrics")
    except requests.RequestException as e:
        error_msg = f"Failed to fetch CUCM metrics: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    # Save to database if we have any metrics
    total_saved = 0
    if all_metrics:
        try:
            total_saved = save_metrics_to_database(all_metrics)
            metrics_collected_count += total_saved
            logger.info(f"Saved {total_saved} metrics to database")
        except Exception as e:
            error_msg = f"Failed to save metrics to database: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    last_collection_time = datetime.utcnow()
    
    return {
        "success": len(errors) == 0,
        "uccx_metrics_count": uccx_count,
        "cucm_metrics_count": cucm_count,
        "total_saved": total_saved,
        "errors": errors,
        "timestamp": last_collection_time.isoformat()
    }


# =============================================================================
# Background Polling Task
# =============================================================================

async def polling_loop():
    """
    Background task that continuously collects metrics at fixed intervals.
    
    This runs indefinitely until cancelled. Each iteration:
    1. Collects metrics from all sources
    2. Waits for polling interval
    3. Repeats
    
    The asyncio.sleep allows other tasks to run during the wait period.
    """
    logger.info(f"Polling loop started (interval: {POLLING_INTERVAL} seconds)")
    
    while True:
        try:
            # Run blocking collection in a thread pool
            result = await asyncio.to_thread(collect_all_metrics)
            
            if result["success"]:
                logger.info(
                    f"Collection cycle complete: {result['total_saved']} metrics saved"
                )
            else:
                logger.warning(
                    f"Collection cycle had errors: {len(result['errors'])} errors"
                )
        
        except asyncio.CancelledError:
            # Graceful shutdown
            logger.info("Polling loop cancelled")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in polling loop: {str(e)}")
        
        # Wait for next collection cycle
        logger.debug(f"Waiting {POLLING_INTERVAL} seconds until next collection...")
        await asyncio.sleep(POLLING_INTERVAL)


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for container orchestration.
    Returns service status and basic statistics.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "proxy-gateway",
        "polling_enabled": ENABLE_POLLING,
        "polling_interval_seconds": POLLING_INTERVAL,
        "last_collection": last_collection_time.isoformat() if last_collection_time else None,
        "total_metrics_collected": metrics_collected_count
    }


@app.get("/api/collect", tags=["collection"])
async def trigger_collection(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Manually trigger a metrics collection cycle.
    
    This endpoint can be called to force immediate collection, independent
    of the background polling schedule. Useful for:
    - On-demand data refresh
    - Testing collection pipeline
    - Recovery from failures
    
    Returns:
        Collection result summary
    """
    logger.info("Manual collection triggered via API")
    result = collect_all_metrics()
    
    if not result["success"]:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Collection completed with errors",
                "errors": result["errors"],
                "partial_results": {
                    "uccx_metrics_count": result["uccx_metrics_count"],
                    "cucm_metrics_count": result["cucm_metrics_count"],
                    "total_saved": result["total_saved"]
                }
            }
        )
    
    return result


@app.get("/api/metrics/recent", tags=["metrics"])
async def get_recent_metrics(
    limit: int = 100,
    server_type: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve recently collected metrics from the database.
    
    Args:
        limit: Maximum number of records to return (default: 100)
        server_type: Optional filter by server type ('uccx' or 'cucm')
    
    Returns:
        List of recent metrics with metadata
    """
    query = db.query(TelephonyMetric)
    
    if server_type:
        query = query.filter(TelephonyMetric.server_type == server_type)
    
    metrics = (
        query.order_by(TelephonyMetric.timestamp.desc())
        .limit(limit)
        .all()
    )
    
    return {
        "count": len(metrics),
        "limit": limit,
        "server_type_filter": server_type,
        "metrics": [m.to_dict() for m in metrics]
    }


@app.get("/api/metrics/summary", tags=["metrics"])
async def get_metrics_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get a summary of collected metrics statistics.
    
    Returns:
        Aggregate statistics about metrics in the database
    """
    from sqlalchemy import func
    
    # Get counts by server type
    server_counts = (
        db.query(
            TelephonyMetric.server_type,
            func.count(TelephonyMetric.id).label("count")
        )
        .group_by(TelephonyMetric.server_type)
        .all()
    )
    
    # Get total count
    total_count = db.query(TelephonyMetric).count()
    
    # Get time range
    oldest = db.query(TelephonyMetric).order_by(TelephonyMetric.timestamp.asc()).first()
    newest = db.query(TelephonyMetric).order_by(TelephonyMetric.timestamp.desc()).first()
    
    return {
        "total_metrics": total_count,
        "by_server_type": {s[0]: s[1] for s in server_counts},
        "time_range": {
            "oldest": oldest.timestamp.isoformat() if oldest else None,
            "newest": newest.timestamp.isoformat() if newest else None
        }
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler to ensure all errors return JSON.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        proxy_headers=True
    )
```

#### `proxy-gateway/models.py`
**Purpose**: SQLAlchemy ORM model and database utilities for the telephony metrics table.

```python
# =============================================================================
# Proxy Gateway - SQLAlchemy Database Models
# =============================================================================
# This module defines the database schema for the telephony metrics system.
# Uses SQLAlchemy ORM for database abstraction and connection management.
# =============================================================================

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    create_engine,
    Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

# =============================================================================
# SQLAlchemy Base Class
# =============================================================================
# All models inherit from this base class which provides:
# - Table metadata management
# - ORM mapping functionality
# - Query interface
# =============================================================================
Base = declarative_base()


# =============================================================================
# Telephony Metrics Model
# =============================================================================
class TelephonyMetric(Base):
    """
    SQLAlchemy model for telephony_metrics table.
    
    This model represents a single time-series data point from any telephony
    server (UCCX or CUCM). Each record captures:
    - When metric was recorded (timestamp)
    - Which server type produced it (server_type)
    - What was being measured (metric_name)
    - The numeric value (metric_value)
    - The unit of measurement (unit)
    
    Attributes:
        id: Primary key, auto-incrementing integer
        timestamp: UTC timestamp when metric was recorded
        server_type: Type of server ('uccx' or 'cucm')
        metric_name: Name of metric being measured
        metric_value: Numeric value of measurement
        unit: Unit of measurement ('count', 'percent', 'seconds', etc.)
    """
    
    # Table name in PostgreSQL
    __tablename__ = "telephony_metrics"
    
    # Primary key - auto-incrementing integer
    id = Column(Integer, primary_key=True, index=True)
    
    # Timestamp - stored with timezone awareness for proper UTC handling
    # Default to current UTC time on insert
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()  # Database-side default
    )
    
    # Server type - identifies which Cisco product generated the metric
    # Examples: 'uccx', 'cucm', 'unity', 'expressway'
    server_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of telephony server (uccx, cucm, etc.)"
    )
    
    # Metric name - specific KPI being measured
    # Examples: 'active_agents', 'calls_in_queue', 'cpu_usage_percent'
    metric_name = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Name of metric (active_agents, cpu_usage_percent, etc.)"
    )
    
    # Metric value - actual measurement as a float
    # Using Double Precision for accurate storage of decimal values
    metric_value = Column(
        Float,
        nullable=False,
        comment="Numeric value of measurement"
    )
    
    # Unit of measurement - describes what value represents
    # Examples: 'count', 'percent', 'seconds', 'milliseconds'
    unit = Column(
        String(20),
        nullable=False,
        comment="Unit of measurement"
    )
    
    # =============================================================================
    # SQLAlchemy Table Configuration
    # =============================================================================
    __table_args__ = (
        # Composite index for efficient time-series queries by server
        Index(
            'idx_metrics_server_timestamp',
            'server_type',
            'timestamp'
        ),
        # Composite index for metric-specific time queries
        Index(
            'idx_metrics_name_timestamp',
            'metric_name',
            'timestamp'
        ),
        # Table comment for documentation
        {'comment': 'Time-series storage for telephony metrics'}
    )
    
    def __repr__(self) -> str:
        """
        String representation for debugging and logging.
        """
        return (
            f"<TelephonyMetric("
            f"id={self.id}, "
            f"server_type='{self.server_type}', "
            f"metric_name='{self.metric_name}', "
            f"value={self.metric_value}, "
            f"unit='{self.unit}', "
            f"timestamp='{self.timestamp}')>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert model instance to a dictionary.
        Useful for JSON serialization.
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "server_type": self.server_type,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "unit": self.unit
        }


# =============================================================================
# Database Connection Management
# =============================================================================

def get_engine(database_url: str):
    """
    Create and configure a SQLAlchemy database engine.
    
    Args:
        database_url: PostgreSQL connection string
                   Format: postgresql://user:password@host:port/database
    
    Returns:
        SQLAlchemy Engine instance
    
    Example:
        engine = get_engine("postgresql://postgres:password@localhost:5432/telephony_db")
    """
    return create_engine(
        database_url,
        # Connection pool settings for production
        pool_size=10,              # Number of connections to maintain
        max_overflow=20,           # Extra connections if pool is exhausted
        pool_pre_ping=True,        # Verify connection validity before use
        pool_recycle=3600,         # Recycle connections after 1 hour
        # Echo SQL for debugging (disable in production)
        echo=False
    )


def get_session_maker(engine):
    """
    Create a session factory bound to the given engine.
    
    Args:
        engine: SQLAlchemy Engine instance
    
    Returns:
        Session maker class
    
    Usage:
        SessionLocal = get_session_maker(engine)
        db = SessionLocal()
    """
    return sessionmaker(
        autocommit=False,    # Manual commit required
        autoflush=False,     # Manual flush required
        bind=engine
    )


def init_database(engine):
    """
    Initialize the database by creating all tables.
    
    This should be called on application startup to ensure the schema
    is created if it doesn't exist.
    
    Args:
        engine: SQLAlchemy Engine instance
    
    Note:
        In production, use proper migrations (Alembic) instead of create_all.
    """
    Base.metadata.create_all(bind=engine)


# =============================================================================
# Database Context Manager
# =============================================================================

class DatabaseSession:
    """
    Context manager for database sessions.
    
    Provides automatic commit/rollback handling and proper resource cleanup.
    
    Usage:
        with DatabaseSession(session_maker) as db:
            metric = TelephonyMetric(...)
            db.add(metric)
            # Automatic commit on success, rollback on exception
    
    Attributes:
        session_maker: SQLAlchemy sessionmaker instance
        db: Active database session
    """
    
    def __init__(self, session_maker):
        self.session_maker = session_maker
        self.db: Optional[Session] = None
    
    def __enter__(self) -> Session:
        self.db = self.session_maker()
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred - rollback changes
            self.db.rollback()
        else:
            # No exception - commit changes
            self.db.commit()
        # Always close session
        self.db.close()
```

#### `proxy-gateway/requirements.txt`
**Purpose**: Python dependencies for the proxy gateway including PostgreSQL client and FastAPI.

```txt
# =============================================================================
# Proxy Gateway - Python Dependencies
# =============================================================================
# These are required packages for the FastAPI proxy gateway that collects
# metrics from mock Cisco servers and persists to PostgreSQL.
# =============================================================================

# FastAPI - Modern, fast web framework for building APIs
fastapi==0.104.1

# Uvicorn - ASGI server to run FastAPI
uvicorn[standard]==0.24.0

# SQLAlchemy - SQL toolkit and ORM for PostgreSQL
# asyncpg is included as an extra for async PostgreSQL support
sqlalchemy[asyncpg]==2.0.23

# Psycopg2-binary - PostgreSQL adapter for Python
# Used by SQLAlchemy as the default synchronous driver
psycopg2-binary==2.9.9

# Requests - HTTP library for calling mock server APIs
requests==2.31.0

# Pydantic - Data validation using Python type hints
pydantic==2.5.2

# Python-dateutil - Useful for timestamp manipulation
python-dateutil==2.8.2
```

#### `proxy-gateway/Dockerfile`
**Purpose**: Production-ready Docker image for the proxy gateway with PostgreSQL client libraries.

```dockerfile
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
```

---

### Superset

#### `superset/Dockerfile`
**Purpose**: Customizes the official Apache Superset image with PostgreSQL driver and initialization script.

```dockerfile
FROM apache/superset:latest

USER root

# Install PostgreSQL driver directly into Superset's Python path
# to bypass virtual environment issues
RUN pip install --target /app/pythonpath --no-cache-dir psycopg2-binary==2.9.9

COPY superset_config.py /app/pythonpath/superset_config.py
COPY superset-init.sh /app/superset-init.sh
RUN chmod +x /app/superset-init.sh

USER superset

# The magic line that was missing - forces Docker to run our init script!
CMD ["/app/superset-init.sh"]
```

#### `superset/superset_config.py`
**Purpose**: Comprehensive Superset configuration for PostgreSQL, Redis, security, and features.

```python
# =============================================================================
# Apache Superset Configuration File
# =============================================================================
# This configuration file customizes Apache Superset for the Telephony Load
# Monitoring System. It configures:
#   - PostgreSQL metadata database
#   - Redis caching backend
#   - Security settings
#   - Feature flags
# =============================================================================

import os

# =============================================================================
# Database Configuration
# =============================================================================
# Superset stores all metadata (dashboards, charts, users, queries) in PostgreSQL.
# This is separate from telephony_db that stores actual metrics data.
# =============================================================================

# Get database connection from environment variables with defaults
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "superset_db")

# SQLAlchemy connection string for PostgreSQL
# Format: postgresql://user:password@host:port/database
SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Enable tracking of database query times (useful for debugging)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Echo SQL queries to logs (disable in production)
SQLALCHEMY_ECHO = False


# =============================================================================
# Redis Cache Configuration
# =============================================================================
# Redis is used as a caching backend to improve dashboard and chart performance.
# Cache keys include query results, filter options, and chart data.
# =============================================================================

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Cache configuration dictionary
# Supports multiple cache types: Redis, Memcached, filesystem, etc.
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,  # 5 minutes default cache
    "CACHE_KEY_PREFIX": "superset_cache_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_DB,
    "CACHE_REDIS_URL": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
}

# Dataset cache (for table metadata)
DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 600,  # 10 minutes for dataset metadata
    "CACHE_KEY_PREFIX": "superset_data_cache_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_DB,
    "CACHE_REDIS_URL": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
}

# Query results cache (for SQL query results)
QUERY_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 60,  # 1 minute for query results (real-time data)
    "CACHE_KEY_PREFIX": "superset_query_cache_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_DB,
    "CACHE_REDIS_URL": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
}


# =============================================================================
# Celery Configuration (for async tasks)
# =============================================================================
# Celery is used for background tasks like scheduled reports, email alerts,
# and async query execution. Redis serves as both broker and backend.
# =============================================================================

class CeleryConfig:
    """Celery configuration for async task processing."""
    
    # Redis as message broker
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    
    # Redis as result backend
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    
    # Task serialization
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    
    # Import paths for task modules
    imports = (
        "superset.sql_lab",
        "superset.scheduled_reports",
        )
    
    # Task routing (optional optimization)
    task_routes = {
        "sql_lab.get_sql_results": {"queue": "sql_lab"},
        "email_reports.send": {"queue": "email_reports"},
    }

# Assign Celery config to Superset
CELERY_CONFIG = CeleryConfig


# =============================================================================
# Security Configuration
# =============================================================================
# WARNING: These are development-friendly settings. Review before production use!
# =============================================================================

# Secret key for session management and encryption
# IMPORTANT: Change this in production! Generate with: openssl rand -base64 42
SECRET_KEY = os.getenv(
    "SUPERSET_SECRET_KEY",
    "your-super-secret-key-change-in-production-1234567890abcdef"
)

# Enable CSRF protection (disable only for testing)
WTF_CSRF_ENABLED = False
TALISMAN_ENABLED = False
# Timezone for application
# Use 'UTC' for consistency across distributed systems
DEFAULT_TIMEZONE = "UTC"


# =============================================================================
# Feature Flags
# =============================================================================
# Enable or disable specific Superset features.
# =============================================================================

FEATURE_FLAGS = {
    # Enable new Explore UI
    "ENABLE_EXPLORE_DRAG_AND_DROP": True,
    
    # Enable dashboard native filters
    "DASHBOARD_NATIVE_FILTERS": True,
    
    # Enable cross-filtering between charts
    "DASHBOARD_CROSS_FILTERS": True,
    
    # Enable alert/reporting features
    "ALERT_REPORTS": True,
    
    # Enable template parameters in SQL queries
    "ENABLE_TEMPLATE_PROCESSING": True,
    
    # Enable dashboard cache warming
    "DASHBOARD_CACHE_WARMUP": True,
    
    # Enable chart caching
    "CACHE_IMPERSONATION": True,
}


# =============================================================================
# Visualization and UI Configuration
# =============================================================================

# Default row limit for queries (prevent returning massive datasets)
DEFAULT_ROW_LIMIT = 10000

# Maximum rows allowed in a query result
MAX_SQL_ROW = 100000

# Default viz type when creating new charts
DEFAULT_VIZ_TYPE = "table"

# Time grainularity options
TIME_GRAIN_ADDON_FUNCTIONS = {
    "postgresql": {
        "PT1S": "DATE_TRUNC('second', {col})",
        "PT1M": "DATE_TRUNC('minute', {col})",
        "PT1H": "DATE_TRUNC('hour', {col})",
        "P1D": "DATE_TRUNC('day', {col})",
        "P1W": "DATE_TRUNC('week', {col})",
        "P1M": "DATE_TRUNC('month', {col})",
    }
}


# =============================================================================
# Logging Configuration
# =============================================================================

# Log level
LOG_LEVEL = "INFO"

# Enable query logging (useful for debugging)
QUERY_LOGGER = None  # Set to logging function if needed


# =============================================================================
# Custom Welcome Message
# =============================================================================

# Custom text displayed on the welcome page
WELCOME_MESSAGE = """
Welcome to Telephony Load Monitoring System!

Use navigation to:
- Create dashboards for real-time telephony metrics
- Explore data from UCCX and CUCM servers
- Set up alerts for threshold violations
- Generate reports on call center performance
"""


# =============================================================================
# Additional Database Connections
# =============================================================================
# Pre-configured database connections available in the UI.
# Users can add additional connections as needed.
# =============================================================================

# The telephony_db will be available as a connection option
# This allows Superset to query metrics data directly
DATABASE_CONNECTION_MAPPER = {
    "telephony_metrics": {
        "sqlalchemy_uri": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/telephony_db",
        "database_name": "Telephony Metrics DB",
        "expose_in_sqllab": True,
        "allow_ctas": True,  # Allow CREATE TABLE AS SELECT
        "allow_cvas": True,  # Allow CREATE VIEW AS SELECT
    }
}


# =============================================================================
# Web Server Configuration
# =============================================================================

# Enable proxy headers for correct IP logging behind nginx
ENABLE_PROXY_FIX = True

# Number of web server workers
# In Docker, we typically use 1 worker per container and scale horizontally
SUPERSET_WEBSERVER_WORKERS = 2

# Web server port
SUPERSET_WEBSERVER_PORT = 8088

# Web server timeout (seconds)
SUPERSET_WEBSERVER_TIMEOUT = 60


# =============================================================================
# Mapbox API (for geospatial visualizations)
# =============================================================================
# Optional: Add your Mapbox token for map visualizations
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY", "")
```

#### `superset/superset-init.sh`
**Purpose**: Initialization script that waits for dependencies, upgrades the database, creates admin user, and starts Superset.

```bash
#!/bin/bash
set -e

echo "============================================================================="
echo "Apache Superset Initialization Script"
echo "============================================================================="

echo "Step 1: Waiting for PostgreSQL database to be ready..."
python -c "
import socket, time
for _ in range(30):
    try:
        with socket.create_connection(('postgres', 5432), timeout=1):
            break
    except OSError:
        time.sleep(2)
"

echo "✓ PostgreSQL is ready!"

echo "Step 2: Upgrading Superset database schema..."
superset db upgrade

echo "Step 3: Creating admin user..."
superset fab create-admin \
              --username admin \
              --firstname Admin \
              --lastname User \
              --email admin@superset.com \
              --password admin || true

echo "Step 4: Initializing roles and permissions..."
superset init

echo "============================================================================="
echo "Initialization Complete! Starting Superset webserver..."
echo "============================================================================="

# Fix here: changed to gthread and added threads
exec gunicorn \
      -w 2 \
      --threads 4 \
      -k gthread \
      --timeout 120 \
      -b  0.0.0.0:8088 \
      --limit-request-line 0 \
      --limit-request-field_size 0 \
      "superset.app:create_app()"
```

---

### Nginx

#### `nginx/nginx.conf`
**Purpose**: Reverse proxy configuration that routes requests to appropriate backend services and provides a single entry point.

```nginx
# =============================================================================
# Nginx Reverse Proxy Configuration
# =============================================================================
# This configuration sets up Nginx as a single entry point for the entire
# Telephony Load Monitoring System. It routes requests to the appropriate
# backend service based on URL path:
#
#   /           -> Apache Superset (port 8088)
#   /api/       -> Proxy Gateway (port 8000)
#   /mock/      -> Mock Server (port 8001)
#
# Features:
# - Load balancing (ready for horizontal scaling)
# - WebSocket support for real-time dashboards
# - Request buffering for large payloads
# - Proper header forwarding for accurate client info
# - Health check endpoints
# =============================================================================

# =============================================================================
# Events Module Configuration
# =============================================================================
# Optimized for handling many concurrent connections typical in web applications
# =============================================================================
events {
    # Worker connections per process - increase for high-traffic environments
    worker_connections 1024;
    
    # Use epoll on Linux for efficient connection handling
    use epoll;
    
    # Accept multiple connections per worker cycle
    multi_accept on;
}

# =============================================================================
# HTTP Module Configuration
# =============================================================================
http {
    # =============================================================================
    # Basic Settings
    # =============================================================================
    
    # MIME type mappings
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Performance optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Hide nginx version for security
    server_tokens off;
    
    # =============================================================================
    # Logging Configuration
    # =============================================================================
    # Structured logging for debugging and monitoring
    # =============================================================================
    
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;
    
    # =============================================================================
    # Gzip Compression
    # =============================================================================
    # Compress responses to reduce bandwidth and improve load times
    # =============================================================================
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json 
               application/javascript application/rss+xml 
               application/atom+xml image/svg+xml;
    
    # =============================================================================
    # Upstream Backend Definitions
    # =============================================================================
    # Define backend server groups for load balancing (ready for scaling)
    # =============================================================================
    
    # Apache Superset upstream
    upstream superset_backend {
        server superset:8088;
        # Add more servers for load balancing:
        # server superset-2:8088;
        # server superset-3:8088;
    }
    
    # Proxy Gateway upstream
    upstream proxy_gateway_backend {
        server proxy-gateway:8000;
    }
    
    # Mock Server upstream
    upstream mock_server_backend {
        server mock-server:8001;
    }
    
    # =============================================================================
    # Main Server Block
    # =============================================================================
    # Listens on port 80 and routes to appropriate backend
    # =============================================================================
    server {
        listen 80;
        listen [::]:80;
        server_name localhost;
        
        # Maximum upload size (for large dashboard exports)
        client_max_body_size 50M;
        
        # =============================================================================
        # Health Check Endpoint
        # =============================================================================
        location /nginx-health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
        
        # =============================================================================
        # Proxy Gateway Routes (/api/*)
        # =============================================================================
        # Routes all /api/ requests to proxy-gateway service
        # =============================================================================
        location /api/ {
            # Remove /api prefix when forwarding
            rewrite ^/api/(.*) /$1 break;
            
            proxy_pass http://proxy_gateway_backend;
            proxy_http_version 1.1;
            
            # Header forwarding for accurate client info
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Prefix /api;
            
            # WebSocket support (for future real-time features)
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Timeouts for long-running operations
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            
            # Buffer settings for response optimization
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }
        
        # =============================================================================
        # Mock Server Routes (/mock/*)
        # =============================================================================
        # Routes all /mock/ requests to mock-server service
        # Useful for testing and development
        # =============================================================================
        location /mock/ {
            # Remove /mock prefix when forwarding
            rewrite ^/mock/(.*) /$1 break;
            
            proxy_pass http://mock_server_backend;
            proxy_http_version 1.1;
            
            # Header forwarding
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Prefix /mock;
            
            # Timeouts
            proxy_connect_timeout 10s;
            proxy_send_timeout 10s;
            proxy_read_timeout 10s;
            
            proxy_buffering on;
        }
        
        # =============================================================================
        # Apache Superset Routes (/)
        # =============================================================================
        # Default route - all requests go to Superset unless matched above
        # Handles static assets, dashboard requests, and Superset UI
        # =============================================================================
        location / {
            proxy_pass http://superset_backend;
            proxy_http_version 1.1;
            
            # Essential headers for Superset to work correctly
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            
            # WebSocket support (Superset uses WebSockets for async queries)
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            
            # Extended timeouts for query operations
            proxy_connect_timeout 60s;
            proxy_send_timeout 120s;
            proxy_read_timeout 120s;
            
            # Buffer settings
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
            
            # Handle large query results
            proxy_max_temp_file_size 1024m;
        }
        
        # =============================================================================
        # Static File Caching
        # =============================================================================
        # Optimize delivery of Superset's static assets
        # =============================================================================
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            proxy_pass http://superset_backend;
            
            # Aggressive caching for static assets
            expires 30d;
            add_header Cache-Control "public, immutable";
            add_header Vary Accept-Encoding;
            
            # Don't log static file requests
            access_log off;
        }
    }
    
    # =============================================================================
    # Map for WebSocket Connection header
    # =============================================================================
    # Required for proper WebSocket upgrade handling
    # =============================================================================
    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }
}
```

---

### PostgreSQL

#### `postgres/init.sql`
**Purpose**: Database initialization script that creates databases and the metrics table.

```sql
-- Create database for Superset
CREATE DATABASE superset_db;

-- Create database for telephony
CREATE DATABASE telephony_db;

-- Connect to the telephony database
\c telephony_db;

-- Create metrics table (removed NOT NULL and CHECK constraints to match Mock)
CREATE TABLE IF NOT EXISTS telephony_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    server_type VARCHAR(20) NOT NULL,
    server_name VARCHAR(100),
    metric_category VARCHAR(50),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    raw_data TEXT
);

CREATE INDEX idx_telephony_metrics_timestamp ON telephony_metrics (timestamp DESC);
CREATE INDEX idx_telephony_metrics_server_time ON telephony_metrics (server_type, timestamp DESC);
```

---

## Data Flow

### Collection Flow

1. **Mock Server** generates realistic metrics:
   - `GET /api/uccx/stats` - Call center metrics (agents, queue, service level)
   - `GET /api/cucm/system/stats` - System metrics (CPU, memory, calls)

2. **Proxy Gateway** collects and processes:
   - Polls mock server every 60 seconds (configurable)
   - Flattens nested JSON into database records
   - Stores in `telephony_metrics` table with timestamp

3. **PostgreSQL** stores time-series data:
   - Single table with composite indexes for performance
   - UTC timestamps for consistency
   - Flexible schema for any metric type

4. **Superset** visualizes data:
   - Connects to `telephony_db` for metrics
   - Uses Redis for caching query results
   - Creates dashboards and charts

5. **Nginx** provides single entry point:
   - Routes `/` → Superset (8088)
   - Routes `/api/` → Proxy Gateway (8000)
   - Routes `/mock/` → Mock Server (8001)

### Request Examples

```bash
# Manual collection trigger
curl http://localhost/api/collect

# Get recent metrics
curl "http://localhost/api/metrics/recent?limit=50"

# Direct mock server access
curl http://localhost/mock/api/uccx/stats

# Health checks
curl http://localhost/api/health
curl http://localhost/mock/health
```

---

## Deployment Guide

### Quick Start

```bash
# Clone and start
git clone <repository>
cd telephony-load-monitoring
docker-compose up -d --build

# Wait for healthy services
docker-compose ps

# Access
open http://localhost  # Nginx (Superset)
```

### Environment Configuration

Key environment variables in `docker-compose.yml`:

- `POSTGRES_PASSWORD` - Database password
- `SECRET_KEY` - Superset encryption key
- `POLLING_INTERVAL` - Collection frequency (seconds)
- `ENABLE_POLLING` - Enable/disable automatic collection

### Production Checklist

- [ ] Change all default passwords
- [ ] Generate new `SECRET_KEY` for Superset
- [ ] Configure SSL certificates in Nginx
- [ ] Remove direct port exposures (5432, 6379, 8000-8088)
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy
- [ ] Review resource limits and scaling

---

## API Reference

### Proxy Gateway API

#### Health Check
```
GET /health
```
Returns service status and statistics.

#### Manual Collection
```
GET /api/collect
```
Triggers immediate metrics collection.

#### Recent Metrics
```
GET /api/metrics/recent?limit=100&server_type=uccx
```
Returns recent metrics with optional filtering.

#### Metrics Summary
```
GET /api/metrics/summary
```
Returns aggregate statistics.

### Mock Server API

#### Health Check
```
GET /health
```
Returns service health status.

#### UCCX Metrics
```
GET /api/uccx/stats
```
Returns simulated call center metrics.

#### CUCM Metrics
```
GET /api/cucm/system/stats
```
Returns simulated system metrics.

---

## Troubleshooting

### Common Issues

1. **Services not starting**
   - Check port conflicts: `netstat -tlnp | grep -E '80|5432|6379|8000|8001|8088'`
   - View logs: `docker-compose logs <service>`

2. **Database connection errors**
   - Verify PostgreSQL health: `docker-compose exec postgres pg_isready -U postgres`
   - Check connection string in proxy-gateway environment

3. **Superset not showing data**
   - Confirm telephony_metrics has data: `docker-compose exec postgres psql -U postgres -d telephony_db -c "SELECT COUNT(*) FROM telephony_metrics;"`
   - Check database connection in Superset UI

### Reset Commands

```bash
# Full reset (removes all data)
docker-compose down -v
docker-compose up -d --build

# Service restart
docker-compose restart <service-name>

# View logs
docker-compose logs -f <service-name>
```

---

*This document provides a complete reference for the Telephony Load Monitoring System. For specific issues, check the service logs and refer to the troubleshooting section.*

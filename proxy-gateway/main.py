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
    Automatically closes the session after the request.
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
        requests.RequestException: If the API call fails.
    """
    url = f"{MOCK_SERVER_URL}/api/uccx/stats"
    logger.debug(f"Fetching UCCX metrics from: {url}")
    
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    
    server_type = data.get("server_type", "uccx")
    metrics_data = data.get("metrics", {})
    
    # Transform the nested metrics into flat records
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
        requests.RequestException: If the API call fails.
    """
    url = f"{MOCK_SERVER_URL}/api/cucm/system/stats"
    logger.debug(f"Fetching CUCM metrics from: {url}")
    
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    
    server_type = data.get("server_type", "cucm")
    metrics_data = data.get("metrics", {})
    
    # Transform the nested metrics into flat records
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
    Save a list of metrics to the PostgreSQL database.
    
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
    2. Waits for the polling interval
    3. Repeats
    
    The asyncio.sleep allows other tasks to run during the wait period.
    """
    logger.info(f"Polling loop started (interval: {POLLING_INTERVAL} seconds)")
    
    while True:
        try:
            # Run the blocking collection in a thread pool
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
    - Testing the collection pipeline
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
        Aggregate statistics about the metrics in the database
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

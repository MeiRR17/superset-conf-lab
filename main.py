# =============================================================================
# Telephony Load Monitoring System - Main Application
# =============================================================================
# This is the main application module that orchestrates the entire telephony
# monitoring system. It provides:
#   - APScheduler-based periodic data collection
#   - Modular architecture for easy extension
#   - REST API for manual collection and monitoring
#   - Database integration with SQLAlchemy
#   - Comprehensive logging and error handling
#
# The architecture is designed to be easily extensible - you can replace mock
# generators with real API calls by implementing the same interface.
# =============================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# Import application modules
from config import get_settings, get_database_url, is_development
from models import (
    get_engine, get_session_maker, init_database, DatabaseSession,
    METRIC_MODELS, CollectionJob
)
from mock_generators import (
    MockGeneratorFactory,
    UnifiedGeneratorFactory, get_default_server_configs,
    create_generators, generate_all_metrics
)

# =============================================================================
# Logging Configuration
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Global State
# =============================================================================
settings = get_settings()
engine = None
SessionLocal = None
scheduler = None
mock_generators = {}
collection_stats = {
    "total_collections": 0,
    "successful_collections": 0,
    "failed_collections": 0,
    "last_collection_time": None,
    "collection_errors": []
}

# =============================================================================
# Data Collection Service
# =============================================================================
class DataCollectionService:
    """
    Service for collecting metrics from various Cisco servers.
    Handles both mock and real API data collection.
    """
    
    def __init__(self, session_maker, generators: Dict[str, Any]):
        """
        Initialize the data collection service.
        
        Args:
            session_maker: SQLAlchemy session maker
            generators: Dictionary of data generators
        """
        self.session_maker = session_maker
        self.generators = generators
    
    async def collect_metrics(self, server_type: str, server_name: str = None) -> Dict[str, Any]:
        """
        Collect metrics from a specific server type.
        
        Args:
            server_type: Type of server (cucm, uccx, cms, imp, meeting_place)
            server_name: Optional specific server name
        
        Returns:
            Dict[str, Any]: Collection results
        """
        start_time = datetime.utcnow()
        
        # Create collection job record
        job_id = await self._create_collection_job(server_type, server_name)
        
        try:
            # Get the appropriate generator
            generator = self.generators.get(server_type)
            if not generator:
                raise ValueError(f"No generator found for server type: {server_type}")
            
            # Generate metrics
            metrics_data = generator.generate_metrics()
            
            # Save to database
            saved_count = await self._save_metrics(server_type, metrics_data)
            
            # Update job status
            await self._update_collection_job(job_id, "completed", saved_count, None)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "success": True,
                "server_type": server_type,
                "server_name": metrics_data.get("server_name", server_name),
                "metrics_collected": saved_count,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to collect {server_type} metrics: {str(e)}")
            
            # Update job status with error
            await self._update_collection_job(job_id, "failed", 0, str(e))
            
            return {
                "success": False,
                "server_type": server_type,
                "server_name": server_name,
                "error": str(e),
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "timestamp": start_time.isoformat()
            }
    
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect metrics from all configured server types.
        
        Returns:
            Dict[str, Any]: Collection results summary
        """
        start_time = datetime.utcnow()
        results = {}
        total_collected = 0
        errors = []
        
        for server_type in self.generators.keys():
            try:
                result = await self.collect_metrics(server_type)
                results[server_type] = result
                
                if result["success"]:
                    total_collected += result["metrics_collected"]
                else:
                    errors.append(f"{server_type}: {result['error']}")
            
            except Exception as e:
                error_msg = f"Unexpected error collecting {server_type}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                results[server_type] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": start_time.isoformat()
                }
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "success": len(errors) == 0,
            "total_metrics_collected": total_collected,
            "servers_processed": len(results),
            "successful_collections": len([r for r in results.values() if r["success"]]),
            "failed_collections": len(errors),
            "errors": errors,
            "duration_seconds": duration,
            "timestamp": start_time.isoformat(),
            "details": results
        }
    
    async def _create_collection_job(self, server_type: str, server_name: str = None) -> str:
        """Create a collection job record."""
        with DatabaseSession(self.session_maker) as session:
            job = CollectionJob(
                job_type=server_type,
                server_name=server_name or f"{server_type}-default",
                status="pending",
                started_at=datetime.utcnow()
            )
            session.add(job)
            session.flush()
            return str(job.id)
    
    async def _update_collection_job(self, job_id: str, status: str, metrics_count: int, error_msg: str = None):
        """Update collection job status."""
        with DatabaseSession(self.session_maker) as session:
            job = session.query(CollectionJob).filter(CollectionJob.id == job_id).first()
            if job:
                job.status = status
                job.completed_at = datetime.utcnow()
                job.duration_seconds = (job.completed_at - job.started_at.replace(tzinfo=None)).total_seconds() if job.completed_at and job.started_at else None
                job.metrics_collected = metrics_count
                job.error_message = error_msg
                session.commit()
    
    async def _save_metrics(self, server_type: str, metrics_data: Dict[str, Any]) -> int:
        """Save metrics to the database."""
        model_class = METRIC_MODELS[server_type]
        saved_count = 0
        
        with DatabaseSession(self.session_maker) as session:
            # Create metric record
            metric = model_class(
                timestamp=datetime.utcnow(),
                server_name=metrics_data.get("server_name"),
                server_ip=metrics_data.get("server_ip"),
                collection_method="mock",
                raw_data=str(metrics_data),
                is_success=True,
                **{k: v for k, v in metrics_data.items() 
                   if k not in ["server_name", "server_ip"] and v is not None}
            )
            
            session.add(metric)
            saved_count = 1
            
            # Update global stats
            collection_stats["total_collections"] += 1
            collection_stats["successful_collections"] += 1
            collection_stats["last_collection_time"] = datetime.utcnow()
        
        return saved_count


# =============================================================================
# Scheduler Management
# =============================================================================
class SchedulerManager:
    """
    Manages APScheduler for periodic data collection.
    """
    
    def __init__(self, collection_service: DataCollectionService):
        """
        Initialize the scheduler manager.
        
        Args:
            collection_service: Data collection service
        """
        self.collection_service = collection_service
        self.scheduler = None
    
    def start(self):
        """Start the scheduler."""
        self.scheduler = AsyncIOScheduler(
            timezone=settings.scheduler.timezone,
            job_defaults={
                'coalesce': settings.scheduler.job_defaults_coalesce,
                'max_instances': settings.scheduler.job_defaults_max_instances
            }
        )
        
        # Add periodic collection job
        self.scheduler.add_job(
            func=self._collect_all_metrics_job,
            trigger=IntervalTrigger(seconds=settings.scheduler.collection_interval),
            id='collect_all_metrics',
            name='Collect all telephony metrics',
            replace_existing=True
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
        
        self.scheduler.start()
        logger.info(f"Scheduler started with {settings.scheduler.collection_interval}s interval")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
    
    async def _collect_all_metrics_job(self):
        """Job function for collecting all metrics."""
        try:
            result = await self.collection_service.collect_all_metrics()
            logger.info(f"Scheduled collection completed: {result['total_metrics_collected']} metrics")
        except Exception as e:
            logger.error(f"Scheduled collection failed: {str(e)}")
            collection_stats["failed_collections"] += 1
            collection_stats["collection_errors"].append(str(e))
    
    def _job_executed_listener(self, event):
        """Handle successful job execution."""
        logger.debug(f"Job {event.job_id} executed successfully")
    
    def _job_error_listener(self, event):
        """Handle job execution errors."""
        logger.error(f"Job {event.job_id} failed: {event.exception}")
        collection_stats["failed_collections"] += 1
        collection_stats["collection_errors"].append(str(event.exception))


# =============================================================================
# Application Lifecycle
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    global engine, SessionLocal, scheduler, mock_generators, collection_service, scheduler_manager
    
    logger.info("=" * 60)
    logger.info("Telephony Load Monitoring System Starting Up")
    logger.info("=" * 60)
    
    # Initialize database
    logger.info("Initializing database connection...")
    engine = get_engine(
        get_database_url(),
        settings.database.pool_size,
        settings.database.max_overflow
    )
    SessionLocal = get_session_maker(engine)
    init_database(engine)
    logger.info("Database initialized successfully")
    
    # Initialize mock generators
    logger.info("Initializing data generators with feature toggles...")
    server_configs = get_default_server_configs()
    mock_generators = UnifiedGeneratorFactory.create_all_generators(server_configs)
    
    # Log generator status
    generator_status = UnifiedGeneratorFactory.get_generator_status()
    logger.info(f"Generator status: {generator_status}")
    logger.info(f"Initialized {len(mock_generators)} generators")
    
    # Initialize collection service
    collection_service = DataCollectionService(SessionLocal, mock_generators)
    
    # Initialize and start scheduler
    if settings.scheduler.enabled:
        logger.info("Starting scheduler...")
        scheduler_manager = SchedulerManager(collection_service)
        scheduler_manager.start()
    
    logger.info("Application startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("Telephony Load Monitoring System Shutting Down")
    logger.info("=" * 60)
    
    if scheduler_manager:
        logger.info("Stopping scheduler...")
        scheduler_manager.stop()
    
    if engine:
        logger.info("Closing database connections...")
        engine.dispose()
    
    logger.info("Application shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="Telephony Load Monitoring System",
    description="Comprehensive monitoring system for Cisco telephony infrastructure",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=settings.api.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Database Dependency
# =============================================================================
def get_db() -> Session:
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and orchestration.
    Returns system status and basic statistics.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "telephony-monitoring-system",
        "version": "2.0.0",
        "environment": settings.environment,
        "scheduler_enabled": settings.scheduler.enabled,
        "collection_interval": settings.scheduler.collection_interval,
        "supported_server_types": MockGeneratorFactory.get_supported_types(),
        "collection_stats": collection_stats
    }


@app.get("/api/collect", tags=["collection"])
async def trigger_collection(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Manually trigger a complete metrics collection cycle.
    
    This endpoint can be called to force immediate collection, independent
    of the scheduler schedule. Useful for:
    - Testing the collection pipeline
    - On-demand data refresh
    - Recovery from failures
    """
    logger.info("Manual collection triggered via API")
    
    if not collection_service:
        raise HTTPException(status_code=503, detail="Collection service not available")
    
    result = await collection_service.collect_all_metrics()
    
    if not result["success"]:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Collection completed with errors",
                "errors": result["errors"],
                "partial_results": {
                    "total_metrics_collected": result["total_metrics_collected"],
                    "successful_collections": result["successful_collections"],
                    "failed_collections": result["failed_collections"]
                }
            }
        )
    
    return result


@app.get("/api/collect/{server_type}", tags=["collection"])
async def trigger_server_collection(server_type: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Manually trigger collection for a specific server type.
    
    Args:
        server_type: Type of server to collect from (cucm, uccx, cms, imp, meeting_place)
    """
    if server_type not in MockGeneratorFactory.get_supported_types():
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported server type: {server_type}. Supported types: {MockGeneratorFactory.get_supported_types()}"
        )
    
    logger.info(f"Manual {server_type} collection triggered via API")
    
    if not collection_service:
        raise HTTPException(status_code=503, detail="Collection service not available")
    
    result = await collection_service.collect_metrics(server_type)
    
    if not result["success"]:
        raise HTTPException(
            status_code=502,
            detail={
                "message": f"{server_type.upper()} collection failed",
                "error": result["error"]
            }
        )
    
    return result


@app.get("/api/metrics/recent", tags=["metrics"])
async def get_recent_metrics(
    limit: int = 100,
    server_type: Optional[str] = None,
    hours: int = 24,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve recently collected metrics from the database.
    
    Args:
        limit: Maximum number of records to return
        server_type: Filter by server type
        hours: Limit to last N hours of data
    """
    since_time = datetime.utcnow() - timedelta(hours=hours)
    
    if server_type and server_type not in METRIC_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported server type: {server_type}"
        )
    
    metrics = []
    
    if server_type:
        # Query specific server type
        model_class = METRIC_MODELS[server_type]
        query = db.query(model_class).filter(
            model_class.timestamp >= since_time
        ).order_by(model_class.timestamp.desc()).limit(limit)
        
        for metric in query.all():
            metrics.append({
                "server_type": server_type,
                "data": metric.to_dict()
            })
    else:
        # Query all server types
        for st, model_class in METRIC_MODELS.items():
            query = db.query(model_class).filter(
                model_class.timestamp >= since_time
            ).order_by(model_class.timestamp.desc()).limit(limit // len(METRIC_MODELS))
            
            for metric in query.all():
                metrics.append({
                    "server_type": st,
                    "data": metric.to_dict()
                })
    
    return {
        "count": len(metrics),
        "limit": limit,
        "server_type_filter": server_type,
        "time_range_hours": hours,
        "since": since_time.isoformat(),
        "metrics": metrics
    }


@app.get("/api/metrics/summary", tags=["metrics"])
async def get_metrics_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get a summary of collected metrics statistics.
    """
    from sqlalchemy import func, text
    
    summary = {
        "by_server_type": {},
        "total_metrics": 0,
        "collection_jobs": {},
        "time_range": {}
    }
    
    # Get counts by server type
    for server_type, model_class in METRIC_MODELS.items():
        count = db.query(model_class).count()
        if count > 0:
            oldest = db.query(model_class).order_by(model_class.timestamp.asc()).first()
            newest = db.query(model_class).order_by(model_class.timestamp.desc()).first()
            
            summary["by_server_type"][server_type] = {
                "count": count,
                "oldest": oldest.timestamp.isoformat() if oldest else None,
                "newest": newest.timestamp.isoformat() if newest else None
            }
            
            summary["total_metrics"] += count
    
    # Get collection job statistics
    job_stats = db.query(
        CollectionJob.status,
        func.count(CollectionJob.id).label("count")
    ).group_by(CollectionJob.status).all()
    
    summary["collection_jobs"] = {status: count for status, count in job_stats}
    
    # Get overall time range
    if summary["total_metrics"] > 0:
        all_timestamps = []
        for server_data in summary["by_server_type"].values():
            if server_data["oldest"]:
                all_timestamps.append(server_data["oldest"])
            if server_data["newest"]:
                all_timestamps.append(server_data["newest"])
        
        if all_timestamps:
            summary["time_range"] = {
                "oldest": min(all_timestamps),
                "newest": max(all_timestamps)
            }
    
    return summary


@app.get("/api/jobs", tags=["jobs"])
async def get_collection_jobs(
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recent collection jobs with their status.
    
    Args:
        limit: Maximum number of jobs to return
        status: Filter by job status
    """
    query = db.query(CollectionJob)
    
    if status:
        query = query.filter(CollectionJob.status == status)
    
    jobs = query.order_by(CollectionJob.started_at.desc()).limit(limit).all()
    
    return {
        "count": len(jobs),
        "limit": limit,
        "status_filter": status,
        "jobs": [job.to_dict() for job in jobs]
    }


@app.get("/api/servers", tags=["servers"])
async def get_server_info() -> Dict[str, Any]:
    """
    Get information about configured servers and generators.
    """
    server_info = {}
    
    for server_type, generator in mock_generators.items():
        config = generator.server_config
        server_info[server_type] = {
            "name": config.name,
            "ip_address": config.ip_address,
            "server_type": config.server_type,
            "region": config.region,
            "capacity": config.capacity,
            "generator_class": generator.__class__.__name__,
            "generator_type": "Real" if "Real" in generator.__class__.__name__ else "Mock"
        }
    
    return {
        "supported_types": MockGeneratorFactory.get_supported_types(),
        "configured_servers": server_info,
        "mock_data_enabled": settings.mock_server.enabled,
        "data_fluctuation": settings.mock_server.data_fluctuation,
        "business_hours_only": settings.mock_server.business_hours_only,
        "feature_toggles": UnifiedGeneratorFactory.get_generator_status()
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
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level="info"
    )

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

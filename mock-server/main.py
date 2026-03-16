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
# TGW (Trunk Gateway) Endpoints
# =============================================================================

@app.get("/api/tgw/stats", tags=["tgw"])
async def get_tgw_stats() -> Dict[str, Any]:
    """
    Returns simulated TGW (Trunk Gateway) statistics.
    
    Metrics returned:
    - Active trunk utilization and status
    - Interface bandwidth and error counters
    - CPU and memory usage
    - Trunk registration status
    
    Data fluctuates based on business hour patterns to simulate
    realistic TGW router load patterns.
    """
    minute_of_day = datetime.now().hour * 60 + datetime.now().minute
    daily_cycle = (1 + (minute_of_day % 480) / 480) * 0.6  # 8-hour cycle
    
    random_factor = random.uniform(0.8, 1.2)
    
    # TGW-specific metrics
    active_tunnels = int(50 * daily_cycle * random_factor)
    active_tunnels = max(10, min(100, active_tunnels))
    
    # Interface metrics
    bandwidth_in = round(random.uniform(50, 500) * daily_cycle * random_factor, 2)
    bandwidth_out = round(random.uniform(40, 400) * daily_cycle * random_factor, 2)
    
    # System metrics (correlated with trunk usage)
    cpu_usage = round(20 + (active_tunnels / 100) * 30 + random.uniform(-5, 10), 1)
    cpu_usage = max(5, min(95, cpu_usage))
    
    memory_usage = round(30 + (active_tunnels / 100) * 25 + random.uniform(-3, 8), 1)
    memory_usage = max(10, min(90, memory_usage))
    
    # Error counters
    interface_errors = int(random.uniform(0, 5) * (1 if cpu_usage > 80 else 0.5))
    trunk_failures = int(random.uniform(0, 2) * (1 if cpu_usage > 85 else 0.2))
    
    return {
        "server_type": "tgw",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "active_tunnels": {
                "value": active_tunnels,
                "unit": "count",
                "description": "Number of active trunk connections"
            },
            "bandwidth_in_mbps": {
                "value": bandwidth_in,
                "unit": "mbps",
                "description": "Inbound bandwidth utilization"
            },
            "bandwidth_out_mbps": {
                "value": bandwidth_out,
                "unit": "mbps",
                "description": "Outbound bandwidth utilization"
            },
            "cpu_usage_percent": {
                "value": cpu_usage,
                "unit": "percent",
                "description": "Router CPU utilization"
            },
            "memory_usage_percent": {
                "value": memory_usage,
                "unit": "percent",
                "description": "Router memory utilization"
            },
            "interface_errors": {
                "value": interface_errors,
                "unit": "count",
                "description": "Interface error count"
            },
            "trunk_failures": {
                "value": trunk_failures,
                "unit": "count",
                "description": "Trunk failure count"
            }
        }
    }


# =============================================================================
# SBC (Session Border Controller) Endpoints
# =============================================================================

@app.get("/api/sbc/stats", tags=["sbc"])
async def get_sbc_stats() -> Dict[str, Any]:
    """
    Returns simulated SBC (Session Border Controller) statistics.
    
    Metrics returned:
    - Concurrent session statistics
    - Call rates and DSP utilization
    - CPU and memory usage
    - Call rejection and error rates
    
    Data fluctuates based on call center patterns to simulate
    realistic SBC load patterns.
    """
    minute_of_day = datetime.now().hour * 60 + datetime.now().minute
    daily_cycle = (1 + (minute_of_day % 480) / 480) * 0.7  # 8-hour cycle
    
    random_factor = random.uniform(0.7, 1.3)
    
    # SBC-specific metrics
    concurrent_sessions = int(200 * daily_cycle * random_factor)
    concurrent_sessions = max(50, min(500, concurrent_sessions))
    
    # Call rates
    calls_per_second = round(random.uniform(10, 50) * daily_cycle * random_factor, 2)
    
    # Resource utilization (correlated with sessions)
    dsp_utilization = round(40 + (concurrent_sessions / 500) * 30 + random.uniform(-5, 8), 1)
    dsp_utilization = max(15, min(95, dsp_utilization))
    
    cpu_usage = round(25 + (concurrent_sessions / 500) * 35 + random.uniform(-3, 7), 1)
    cpu_usage = max(10, min(90, cpu_usage))
    
    memory_usage = round(35 + (concurrent_sessions / 500) * 25 + random.uniform(-2, 6), 1)
    memory_usage = max(15, min(85, memory_usage))
    
    # Error rates
    rejected_calls = int(random.uniform(0, 10) * (1 if dsp_utilization > 80 else 0.3))
    rejected_calls = max(0, min(10, rejected_calls))
    
    failed_calls = int(random.uniform(0, 5) * (1 if cpu_usage > 85 else 0.2))
    failed_calls = max(0, min(5, failed_calls))
    
    return {
        "server_type": "sbc",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "concurrent_sessions": {
                "value": concurrent_sessions,
                "unit": "count",
                "description": "Concurrent active sessions"
            },
            "calls_per_second": {
                "value": calls_per_second,
                "unit": "cps",
                "description": "Calls per second rate"
            },
            "dsp_utilization_percent": {
                "value": dsp_utilization,
                "unit": "percent",
                "description": "DSP resource utilization"
            },
            "rejected_calls": {
                "value": rejected_calls,
                "unit": "count",
                "description": "Rejected call count"
            },
            "failed_calls": {
                "value": failed_calls,
                "unit": "count",
                "description": "Failed call count"
            },
            "cpu_usage_percent": {
                "value": cpu_usage,
                "unit": "percent",
                "description": "SBC CPU utilization"
            },
            "memory_usage_percent": {
                "value": memory_usage,
                "unit": "percent",
                "description": "SBC memory utilization"
            }
        }
    }


# =============================================================================
# Expressway Endpoints
# =============================================================================

@app.get("/api/expressway/stats", tags=["expressway"])
async def get_expressway_stats() -> Dict[str, Any]:
    """
    Returns simulated Expressway traversal server statistics.
    
    Metrics returned:
    - Traversal and non-traversal call statistics
    - Device registration status
    - TURN relay and media resource utilization
    - CPU and memory usage
    
    Data fluctuates based on security patterns to simulate
    realistic Expressway load patterns.
    """
    minute_of_day = datetime.now().hour * 60 + datetime.now().minute
    daily_cycle = (1 + (minute_of_day % 480) / 480) * 0.8  # 8-hour cycle
    
    random_factor = random.uniform(0.6, 1.4)
    
    # Expressway-specific metrics
    traversal_calls = int(100 * daily_cycle * random_factor)
    traversal_calls = max(20, min(300, traversal_calls))
    
    non_traversal_calls = int(random.uniform(5, 25) * daily_cycle * random_factor)
    registered_devices = int(150 + random.uniform(-20, 30))
    
    # Resource utilization
    turn_relays_active = int(10 * daily_cycle * random_factor)
    turn_relays_active = max(2, min(25, turn_relays_active))
    
    cpu_usage = round(20 + (traversal_calls / 300) * 25 + random.uniform(-4, 6), 1)
    cpu_usage = max(5, min(85, cpu_usage))
    
    memory_usage = round(25 + (traversal_calls / 300) * 20 + random.uniform(-3, 5), 1)
    memory_usage = max(10, min(80, memory_usage))
    
    return {
        "server_type": "expressway",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "traversal_calls": {
                "value": traversal_calls,
                "unit": "count",
                "description": "Successful traversal calls"
            },
            "non_traversal_calls": {
                "value": non_traversal_calls,
                "unit": "count",
                "description": "Non-traversal calls"
            },
            "registered_devices": {
                "value": registered_devices,
                "unit": "count",
                "description": "Registered devices"
            },
            "turn_relays_active": {
                "value": turn_relays_active,
                "unit": "count",
                "description": "Active TURN relays"
            },
            "cpu_usage_percent": {
                "value": cpu_usage,
                "unit": "percent",
                "description": "Expressway CPU utilization"
            },
            "memory_usage_percent": {
                "value": memory_usage,
                "unit": "percent",
                "description": "Expressway memory utilization"
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
    - abandoned_calls: Number of calls abandoned while in queue
    
    CPU and memory usage fluctuate based on call volume to simulate
    real system resource correlation.
    """
    minute_of_day = datetime.now().hour * 60 + datetime.now().minute
    daily_cycle = (1 + (minute_of_day % 480) / 480) * 0.7  # 8-hour cycle
    
    random_factor = random.uniform(0.7, 1.3)
    
    # Generate correlated metrics
    base_calls = 500
    active_calls = int(base_calls * daily_cycle * random_factor)
    active_calls = max(50, min(1000, active_calls))
    
    # CPU correlates with call volume
    cpu_usage = 15 + (active_calls / 1000) * 30 + random.uniform(-5, 10)
    cpu_usage = max(5, min(95, cpu_usage))
    
    # Memory has baseline plus call-dependent component
    memory_usage = 40 + (active_calls / 1000) * 25 + random.uniform(-3, 5)
    memory_usage = max(25, min(90, memory_usage))
    
    # Registered phones is relatively stable
    registered_phones = int(800 + random.uniform(-50, 50))
    
    # Failed calls correlate with load
    failure_rate = 0.01 + (cpu_usage / 1000)  # 1-10% based on load
    failure_rate = max(0.005, 0.02)  # 0.5-2% max
    failed_calls = int(active_calls * failure_rate * random.uniform(0.5, 1.5))
    failed_calls = max(0, min(25, failed_calls))
    
    # Abandoned calls increase with queue depth and CPU usage
    calls_in_queue = int(50 * random.uniform(0.05, 0.15))
    abandoned_calls = int(calls_in_queue * random.uniform(0.05, 0.15))
    abandoned_calls = max(0, min(50, abandoned_calls))
    
    return {
        "server_type": "cucm",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "cpu_usage_percent": {
                "value": cpu_usage,
                "unit": "percent",
                "description": "System CPU utilization"
            },
            "memory_usage_percent": {
                "value": memory_usage,
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
            "abandoned_calls": {
                "value": int(calls_in_queue * random.uniform(0.05, 0.15)),
                "unit": "count",
                "description": "Calls abandoned while in queue"
            },
            "total_call_volume": {
                "value": int(active_calls * random.uniform(1.2, 2.0)),
                "unit": "count",
                "description": "Total calls processed (includes completed)"
            }
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
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info",
        proxy_headers=True
    )

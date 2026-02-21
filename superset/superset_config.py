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
# This is separate from the telephony_db that stores the actual metrics data.
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
# Timezone for the application
# Use 'UTC' for consistency across distributed systems
DEFAULT_TIMEZONE = "UTC"


# =============================================================================
# Feature Flags
# =============================================================================
# Enable or disable specific Superset features.
# =============================================================================

FEATURE_FLAGS = {
    # Enable the new Explore UI
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
Welcome to the Telephony Load Monitoring System!

Use the navigation to:
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
# This allows Superset to query the metrics data directly
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

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
    SQLAlchemy model for the telephony_metrics table.
    
    This model represents a single time-series data point from any telephony
    server (UCCX or CUCM). Each record captures:
    - When the metric was recorded (timestamp)
    - Which server type produced it (server_type)
    - What was being measured (metric_name)
    - The numeric value (metric_value)
    - The unit of measurement (unit)
    
    Attributes:
        id: Primary key, auto-incrementing integer
        timestamp: UTC timestamp when metric was recorded
        server_type: Type of server ('uccx' or 'cucm')
        metric_name: Name of the metric being measured
        metric_value: Numeric value of the measurement
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
    
    # Metric name - the specific KPI being measured
    # Examples: 'active_agents', 'calls_in_queue', 'cpu_usage_percent'
    metric_name = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Name of the metric (active_agents, cpu_usage_percent, etc.)"
    )
    
    # Metric value - the actual measurement as a float
    # Using Double Precision for accurate storage of decimal values
    metric_value = Column(
        Float,
        nullable=False,
        comment="Numeric value of the measurement"
    )
    
    # Unit of measurement - describes what the value represents
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
        Convert the model instance to a dictionary.
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
        # Always close the session
        self.db.close()

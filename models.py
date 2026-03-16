# =============================================================================
# Telephony Load Monitoring System - SQLAlchemy Models
# =============================================================================
# This module defines all database models for storing telephony metrics from
# various Cisco server types. Each model is optimized for time-series data
# and includes appropriate indexes for efficient querying.
# =============================================================================

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, Index,
    ForeignKey, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

# =============================================================================
# SQLAlchemy Base Class
# =============================================================================
Base = declarative_base()


# =============================================================================
# Base Metrics Model
# =============================================================================
class BaseMetric(Base):
    """
    Abstract base class for all metrics models.
    Provides common fields and functionality.
    """
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="Timestamp when the metric was recorded (UTC)"
    )
    
    server_name = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Friendly name of the server"
    )
    
    server_ip = Column(
        String(45),  # IPv6 compatible
        nullable=True,
        index=True,
        comment="IP address of the server"
    )
    
    # Metadata fields
    collection_method = Column(
        String(50),
        nullable=False,
        default="api",
        comment="Method used to collect the metric (api, mock, snmp, etc.)"
    )
    
    raw_data = Column(
        Text,
        nullable=True,
        comment="Raw response data from the server"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if collection failed"
    )
    
    is_success = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the metric collection was successful"
    )
    
    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "server_name": self.server_name,
            "server_ip": self.server_ip,
            "collection_method": self.collection_method,
            "raw_data": self.raw_data,
            "error_message": self.error_message,
            "is_success": self.is_success
        }


# =============================================================================
# CUCM Metrics Model
# =============================================================================
class CUCMMetric(BaseMetric):
    """
    Cisco Unified Communications Manager metrics.
    Stores system performance and call statistics.
    """
    
    __tablename__ = "cucm_metrics"
    
    # Call Statistics
    active_calls = Column(
        Integer,
        nullable=True,
        comment="Number of currently active voice calls"
    )
    
    total_calls_today = Column(
        Integer,
        nullable=True,
        comment="Total number of calls processed today"
    )
    
    failed_calls = Column(
        Integer,
        nullable=True,
        comment="Number of failed call attempts"
    )
    
    # Device Statistics
    registered_phones = Column(
        Integer,
        nullable=True,
        comment="Number of registered IP phones/endpoints"
    )
    
    total_devices = Column(
        Integer,
        nullable=True,
        comment="Total number of configured devices"
    )
    
    # System Performance
    cpu_usage_percent = Column(
        Float,
        nullable=True,
        comment="CPU utilization percentage"
    )
    
    memory_usage_percent = Column(
        Float,
        nullable=True,
        comment="Memory utilization percentage"
    )
    
    disk_usage_percent = Column(
        Float,
        nullable=True,
        comment="Disk utilization percentage"
    )
    
    # Cluster Information
    cluster_status = Column(
        String(20),
        nullable=True,
        comment="Cluster status (healthy, degraded, failed)"
    )
    
    publisher_status = Column(
        String(20),
        nullable=True,
        comment="Publisher node status"
    )
    
    subscriber_count = Column(
        Integer,
        nullable=True,
        comment="Number of subscriber nodes"
    )
    
    # Trunk Statistics
    active_trunks = Column(
        Integer,
        nullable=True,
        comment="Number of active SIP trunks"
    )
    
    trunk_utilization_percent = Column(
        Float,
        nullable=True,
        comment="Average trunk utilization percentage"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("active_calls >= 0", name="check_cucm_active_calls_non_negative"),
        CheckConstraint("registered_phones >= 0", name="check_cucm_registered_phones_non_negative"),
        CheckConstraint("cpu_usage_percent >= 0 AND cpu_usage_percent <= 100", name="check_cucm_cpu_percent_range"),
        CheckConstraint("memory_usage_percent >= 0 AND memory_usage_percent <= 100", name="check_cucm_memory_percent_range"),
        Index("idx_cucm_timestamp_server", "timestamp", "server_name"),
        Index("idx_cucm_active_calls", "active_calls"),
        Index("idx_cucm_cpu_memory", "cpu_usage_percent", "memory_usage_percent"),
        {"comment": "CUCM system metrics and call statistics"}
    )
    
    def to_dict(self) -> dict:
        """Convert CUCM metric to dictionary."""
        base_dict = super().to_dict()
        cucm_dict = {
            "active_calls": self.active_calls,
            "total_calls_today": self.total_calls_today,
            "failed_calls": self.failed_calls,
            "registered_phones": self.registered_phones,
            "total_devices": self.total_devices,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "cluster_status": self.cluster_status,
            "publisher_status": self.publisher_status,
            "subscriber_count": self.subscriber_count,
            "active_trunks": self.active_trunks,
            "trunk_utilization_percent": self.trunk_utilization_percent
        }
        base_dict.update(cucm_dict)
        return base_dict


# =============================================================================
# UCCX Metrics Model
# =============================================================================
class UCCXMetric(BaseMetric):
    """
    Unified Contact Center Express metrics.
    Stores call center statistics and agent information.
    """
    
    __tablename__ = "uccx_metrics"
    
    # Agent Statistics
    logged_in_agents = Column(
        Integer,
        nullable=True,
        comment="Number of agents currently logged in"
    )
    
    available_agents = Column(
        Integer,
        nullable=True,
        comment="Number of agents available for calls"
    )
    
    talking_agents = Column(
        Integer,
        nullable=True,
        comment="Number of agents currently on calls"
    )
    
    not_ready_agents = Column(
        Integer,
        nullable=True,
        comment="Number of agents in not-ready state"
    )
    
    # Queue Statistics
    calls_in_queue = Column(
        Integer,
        nullable=True,
        comment="Number of calls currently waiting in queue"
    )
    
    longest_wait_time_seconds = Column(
        Integer,
        nullable=True,
        comment="Longest wait time for calls in queue"
    )
    
    average_wait_time_seconds = Column(
        Float,
        nullable=True,
        comment="Average wait time for calls in queue"
    )
    
    abandoned_calls = Column(
        Integer,
        nullable=True,
        comment="Number of abandoned calls"
    )
    
    # Service Level Metrics
    service_level_percent = Column(
        Float,
        nullable=True,
        comment="Service level percentage (calls answered within SLA)"
    )
    
    service_level_target_seconds = Column(
        Integer,
        nullable=True,
        comment="Service level target time in seconds"
    )
    
    # Contact Statistics
    contacts_handled_today = Column(
        Integer,
        nullable=True,
        comment="Total contacts handled today"
    )
    
    contacts_abandoned_today = Column(
        Integer,
        nullable=True,
        comment="Total contacts abandoned today"
    )
    
    average_handle_time_seconds = Column(
        Float,
        nullable=True,
        comment="Average handle time for contacts"
    )
    
    # Skill Group Statistics
    active_skill_groups = Column(
        Integer,
        nullable=True,
        comment="Number of active skill groups"
    )
    
    # System Performance
    cpu_usage_percent = Column(
        Float,
        nullable=True,
        comment="UCCX server CPU utilization"
    )
    
    memory_usage_percent = Column(
        Float,
        nullable=True,
        comment="UCCX server memory utilization"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("logged_in_agents >= 0", name="check_uccx_logged_in_agents_non_negative"),
        CheckConstraint("calls_in_queue >= 0", name="check_uccx_calls_in_queue_non_negative"),
        CheckConstraint("longest_wait_time_seconds >= 0", name="check_uccx_longest_wait_non_negative"),
        CheckConstraint("service_level_percent >= 0 AND service_level_percent <= 100", name="check_uccx_service_level_range"),
        Index("idx_uccx_timestamp_server", "timestamp", "server_name"),
        Index("idx_uccx_agents", "logged_in_agents", "available_agents"),
        Index("idx_uccx_queue", "calls_in_queue", "longest_wait_time_seconds"),
        Index("idx_uccx_service_level", "service_level_percent"),
        {"comment": "UCCX call center metrics and agent statistics"}
    )
    
    def to_dict(self) -> dict:
        """Convert UCCX metric to dictionary."""
        base_dict = super().to_dict()
        uccx_dict = {
            "logged_in_agents": self.logged_in_agents,
            "available_agents": self.available_agents,
            "talking_agents": self.talking_agents,
            "not_ready_agents": self.not_ready_agents,
            "calls_in_queue": self.calls_in_queue,
            "longest_wait_time_seconds": self.longest_wait_time_seconds,
            "average_wait_time_seconds": self.average_wait_time_seconds,
            "abandoned_calls": self.abandoned_calls,
            "service_level_percent": self.service_level_percent,
            "service_level_target_seconds": self.service_level_target_seconds,
            "contacts_handled_today": self.contacts_handled_today,
            "contacts_abandoned_today": self.contacts_abandoned_today,
            "average_handle_time_seconds": self.average_handle_time_seconds,
            "active_skill_groups": self.active_skill_groups,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent
        }
        base_dict.update(uccx_dict)
        return base_dict


# =============================================================================
# CMS Metrics Model
# =============================================================================
class CMSMetric(BaseMetric):
    """
    Cisco Meeting Server metrics.
    Stores video conferencing and meeting statistics.
    """
    
    __tablename__ = "cms_metrics"
    
    # Meeting Statistics
    active_meetings = Column(
        Integer,
        nullable=True,
        comment="Number of currently active meetings"
    )
    
    total_meetings_today = Column(
        Integer,
        nullable=True,
        comment="Total meetings conducted today"
    )
    
    scheduled_meetings_today = Column(
        Integer,
        nullable=True,
        comment="Number of scheduled meetings today"
    )
    
    # Participant Statistics
    total_participants = Column(
        Integer,
        nullable=True,
        comment="Total number of participants in all meetings"
    )
    
    unique_participants_today = Column(
        Integer,
        nullable=True,
        comment="Number of unique participants today"
    )
    
    # Resource Utilization
    audio_resource_utilization_percent = Column(
        Float,
        nullable=True,
        comment="Audio resource utilization percentage"
    )
    
    video_resource_utilization_percent = Column(
        Float,
        nullable=True,
        comment="Video resource utilization percentage"
    )
    
    screen_share_utilization_percent = Column(
        Float,
        nullable=True,
        comment="Screen sharing resource utilization percentage"
    )
    
    # Call Bridge Statistics
    active_call_bridges = Column(
        Integer,
        nullable=True,
        comment="Number of active call bridges"
    )
    
    total_call_bridges = Column(
        Integer,
        nullable=True,
        comment="Total number of configured call bridges"
    )
    
    # System Performance
    cpu_usage_percent = Column(
        Float,
        nullable=True,
        comment="CMS server CPU utilization"
    )
    
    memory_usage_percent = Column(
        Float,
        nullable=True,
        comment="CMS server memory utilization"
    )
    
    network_bandwidth_mbps = Column(
        Float,
        nullable=True,
        comment="Current network bandwidth usage in Mbps"
    )
    
    # Quality Metrics
    average_jitter_ms = Column(
        Float,
        nullable=True,
        comment="Average network jitter in milliseconds"
    )
    
    packet_loss_percent = Column(
        Float,
        nullable=True,
        comment="Average packet loss percentage"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("active_meetings >= 0", name="check_cms_active_meetings_non_negative"),
        CheckConstraint("total_participants >= 0", name="check_cms_total_participants_non_negative"),
        CheckConstraint("audio_resource_utilization_percent >= 0 AND audio_resource_utilization_percent <= 100", name="check_cms_audio_resource_range"),
        CheckConstraint("video_resource_utilization_percent >= 0 AND video_resource_utilization_percent <= 100", name="check_cms_video_resource_range"),
        Index("idx_cms_timestamp_server", "timestamp", "server_name"),
        Index("idx_cms_meetings", "active_meetings", "total_participants"),
        Index("idx_cms_resources", "audio_resource_utilization_percent", "video_resource_utilization_percent"),
        {"comment": "CMS video conferencing metrics and meeting statistics"}
    )
    
    def to_dict(self) -> dict:
        """Convert CMS metric to dictionary."""
        base_dict = super().to_dict()
        cms_dict = {
            "active_meetings": self.active_meetings,
            "total_meetings_today": self.total_meetings_today,
            "scheduled_meetings_today": self.scheduled_meetings_today,
            "total_participants": self.total_participants,
            "unique_participants_today": self.unique_participants_today,
            "audio_resource_utilization_percent": self.audio_resource_utilization_percent,
            "video_resource_utilization_percent": self.video_resource_utilization_percent,
            "screen_share_utilization_percent": self.screen_share_utilization_percent,
            "active_call_bridges": self.active_call_bridges,
            "total_call_bridges": self.total_call_bridges,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
            "average_jitter_ms": self.average_jitter_ms,
            "packet_loss_percent": self.packet_loss_percent
        }
        base_dict.update(cms_dict)
        return base_dict


# =============================================================================
# IMP Metrics Model
# =============================================================================
class IMPMetric(BaseMetric):
    """
    Instant Messaging & Presence metrics.
    Stores XMPP and presence service statistics.
    """
    
    __tablename__ = "imp_metrics"
    
    # Session Statistics
    active_xmpp_sessions = Column(
        Integer,
        nullable=True,
        comment="Number of active XMPP sessions"
    )
    
    total_sessions_today = Column(
        Integer,
        nullable=True,
        comment="Total XMPP sessions established today"
    )
    
    # User Statistics
    logged_in_users = Column(
        Integer,
        nullable=True,
        comment="Number of users currently logged in"
    )
    
    total_users = Column(
        Integer,
        nullable=True,
        comment="Total number of configured users"
    )
    
    # Presence Statistics
    users_available = Column(
        Integer,
        nullable=True,
        comment="Number of users with available status"
    )
    
    users_busy = Column(
        Integer,
        nullable=True,
        comment="Number of users with busy status"
    )
    
    users_away = Column(
        Integer,
        nullable=True,
        comment="Number of users with away status"
    )
    
    users_offline = Column(
        Integer,
        nullable=True,
        comment="Number of users with offline status"
    )
    
    # Message Statistics
    messages_sent_today = Column(
        Integer,
        nullable=True,
        comment="Number of messages sent today"
    )
    
    messages_received_today = Column(
        Integer,
        nullable=True,
        comment="Number of messages received today"
    )
    
    file_transfers_today = Column(
        Integer,
        nullable=True,
        comment="Number of file transfers today"
    )
    
    # Group Chat Statistics
    active_group_chats = Column(
        Integer,
        nullable=True,
        comment="Number of active group chat rooms"
    )
    
    total_group_chats = Column(
        Integer,
        nullable=True,
        comment="Total number of configured group chat rooms"
    )
    
    # System Performance
    cpu_usage_percent = Column(
        Float,
        nullable=True,
        comment="IMP server CPU utilization"
    )
    
    memory_usage_percent = Column(
        Float,
        nullable=True,
        comment="IMP server memory utilization"
    )
    
    # Federation Statistics
    federated_domains = Column(
        Integer,
        nullable=True,
        comment="Number of federated domains"
    )
    
    active_federated_sessions = Column(
        Integer,
        nullable=True,
        comment="Number of active federated sessions"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("active_xmpp_sessions >= 0", name="check_imp_active_sessions_non_negative"),
        CheckConstraint("logged_in_users >= 0", name="check_imp_logged_in_users_non_negative"),
        CheckConstraint("messages_sent_today >= 0", name="check_imp_messages_sent_non_negative"),
        CheckConstraint("cpu_usage_percent >= 0 AND cpu_usage_percent <= 100", name="check_imp_cpu_percent_range"),
        Index("idx_imp_timestamp_server", "timestamp", "server_name"),
        Index("idx_imp_sessions", "active_xmpp_sessions", "logged_in_users"),
        Index("idx_imp_presence", "users_available", "users_busy"),
        Index("idx_imp_messages", "messages_sent_today", "messages_received_today"),
        {"comment": "IMP XMPP and presence service metrics"}
    )
    
    def to_dict(self) -> dict:
        """Convert IMP metric to dictionary."""
        base_dict = super().to_dict()
        imp_dict = {
            "active_xmpp_sessions": self.active_xmpp_sessions,
            "total_sessions_today": self.total_sessions_today,
            "logged_in_users": self.logged_in_users,
            "total_users": self.total_users,
            "users_available": self.users_available,
            "users_busy": self.users_busy,
            "users_away": self.users_away,
            "users_offline": self.users_offline,
            "messages_sent_today": self.messages_sent_today,
            "messages_received_today": self.messages_received_today,
            "file_transfers_today": self.file_transfers_today,
            "active_group_chats": self.active_group_chats,
            "total_group_chats": self.total_group_chats,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "federated_domains": self.federated_domains,
            "active_federated_sessions": self.active_federated_sessions
        }
        base_dict.update(imp_dict)
        return base_dict


# =============================================================================
# Meeting Place Metrics Model
# =============================================================================
class MeetingPlaceMetric(BaseMetric):
    """
    Cisco Meeting Place (Legacy) metrics.
    Stores web conferencing and audio conference statistics.
    """
    
    __tablename__ = "meeting_place_metrics"
    
    # Conference Statistics
    active_conferences = Column(
        Integer,
        nullable=True,
        comment="Number of currently active conferences"
    )
    
    total_conferences_today = Column(
        Integer,
        nullable=True,
        comment="Total conferences conducted today"
    )
    
    scheduled_conferences_today = Column(
        Integer,
        nullable=True,
        comment="Number of scheduled conferences today"
    )
    
    # Participant Statistics
    total_participants = Column(
        Integer,
        nullable=True,
        comment="Total number of participants in all conferences"
    )
    
    unique_participants_today = Column(
        Integer,
        nullable=True,
        comment="Number of unique participants today"
    )
    
    # Audio Conference Statistics
    active_audio_conferences = Column(
        Integer,
        nullable=True,
        comment="Number of active audio conferences"
    )
    
    audio_participants = Column(
        Integer,
        nullable=True,
        comment="Number of audio conference participants"
    )
    
    # Web Conference Statistics
    active_web_conferences = Column(
        Integer,
        nullable=True,
        comment="Number of active web conferences"
    )
    
    web_participants = Column(
        Integer,
        nullable=True,
        comment="Number of web conference participants"
    )
    
    # Resource Utilization
    audio_resource_utilization_percent = Column(
        Float,
        nullable=True,
        comment="Audio resource utilization percentage"
    )
    
    web_resource_utilization_percent = Column(
        Float,
        nullable=True,
        comment="Web conferencing resource utilization percentage"
    )
    
    # System Performance
    cpu_usage_percent = Column(
        Float,
        nullable=True,
        comment="Meeting Place server CPU utilization"
    )
    
    memory_usage_percent = Column(
        Float,
        nullable=True,
        comment="Meeting Place server memory utilization"
    )
    
    # Bridge Statistics
    active_bridges = Column(
        Integer,
        nullable=True,
        comment="Number of active conference bridges"
    )
    
    total_bridges = Column(
        Integer,
        nullable=True,
        comment="Total number of configured conference bridges"
    )
    
    # Quality Metrics
    average_conference_duration_minutes = Column(
        Float,
        nullable=True,
        comment="Average conference duration in minutes"
    )
    
    dropped_calls = Column(
        Integer,
        nullable=True,
        comment="Number of dropped calls today"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("active_conferences >= 0", name="check_mp_active_conferences_non_negative"),
        CheckConstraint("total_participants >= 0", name="check_mp_total_participants_non_negative"),
        CheckConstraint("audio_resource_utilization_percent >= 0 AND audio_resource_utilization_percent <= 100", name="check_mp_audio_resource_range"),
        CheckConstraint("web_resource_utilization_percent >= 0 AND web_resource_utilization_percent <= 100", name="check_mp_web_resource_range"),
        Index("idx_mp_timestamp_server", "timestamp", "server_name"),
        Index("idx_mp_conferences", "active_conferences", "total_participants"),
        Index("idx_mp_resources", "audio_resource_utilization_percent", "web_resource_utilization_percent"),
        {"comment": "Meeting Place legacy web conferencing metrics"}
    )
    
    def to_dict(self) -> dict:
        """Convert Meeting Place metric to dictionary."""
        base_dict = super().to_dict()
        mp_dict = {
            "active_conferences": self.active_conferences,
            "total_conferences_today": self.total_conferences_today,
            "scheduled_conferences_today": self.scheduled_conferences_today,
            "total_participants": self.total_participants,
            "unique_participants_today": self.unique_participants_today,
            "active_audio_conferences": self.active_audio_conferences,
            "audio_participants": self.audio_participants,
            "active_web_conferences": self.active_web_conferences,
            "web_participants": self.web_participants,
            "audio_resource_utilization_percent": self.audio_resource_utilization_percent,
            "web_resource_utilization_percent": self.web_resource_utilization_percent,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "active_bridges": self.active_bridges,
            "total_bridges": self.total_bridges,
            "average_conference_duration_minutes": self.average_conference_duration_minutes,
            "dropped_calls": self.dropped_calls
        }
        base_dict.update(mp_dict)
        return base_dict


# =============================================================================
# Collection Job Model
# =============================================================================
class CollectionJob(Base):
    """
    Model to track metric collection jobs and their status.
    """
    
    __tablename__ = "collection_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    job_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of collection job (cucm, uccx, cms, imp, meeting_place)"
    )
    
    server_name = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Name of the server being collected"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Job status (pending, running, completed, failed)"
    )
    
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job started"
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job completed"
    )
    
    duration_seconds = Column(
        Float,
        nullable=True,
        comment="Job duration in seconds"
    )
    
    metrics_collected = Column(
        Integer,
        nullable=True,
        comment="Number of metrics collected"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if job failed"
    )
    
    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retry attempts"
    )
    
    next_retry_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When to retry the job"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="check_job_status"),
        CheckConstraint("metrics_collected >= 0", name="check_metrics_collected_non_negative"),
        CheckConstraint("retry_count >= 0", name="check_retry_count_non_negative"),
        Index("idx_jobs_status_server", "status", "server_name"),
        Index("idx_jobs_started_at", "started_at"),
        Index("idx_jobs_next_retry", "next_retry_at"),
        {"comment": "Metric collection job tracking"}
    )
    
    def to_dict(self) -> dict:
        """Convert collection job to dictionary."""
        return {
            "id": str(self.id),
            "job_type": self.job_type,
            "server_name": self.server_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "metrics_collected": self.metrics_collected,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None
        }


# =============================================================================
# Database Management Functions
# =============================================================================
def get_engine(database_url: str, pool_size: int = 10, max_overflow: int = 20):
    """
    Create and configure a SQLAlchemy database engine.
    
    Args:
        database_url: PostgreSQL connection string
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections
    
    Returns:
        SQLAlchemy Engine instance
    """
    from sqlalchemy import create_engine
    
    return create_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )


def get_session_maker(engine):
    """
    Create a session factory bound to the given engine.
    
    Args:
        engine: SQLAlchemy Engine instance
    
    Returns:
        Session maker class
    """
    from sqlalchemy.orm import sessionmaker
    
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )


def init_database(engine):
    """
    Initialize the database by creating all tables.
    
    Args:
        engine: SQLAlchemy Engine instance
    """
    Base.metadata.create_all(bind=engine)


# =============================================================================
# Database Context Manager
# =============================================================================
class DatabaseSession:
    """
    Context manager for database sessions with automatic commit/rollback.
    """
    
    def __init__(self, session_maker):
        self.session_maker = session_maker
        self.session = None
    
    def __enter__(self) -> Session:
        self.session = self.session_maker()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()


# =============================================================================
# Model Registry
# =============================================================================
METRIC_MODELS = {
    "cucm": CUCMMetric,
    "uccx": UCCXMetric,
    "cms": CMSMetric,
    "imp": IMPMetric,
    "meeting_place": MeetingPlaceMetric
}

ALL_MODELS = [
    CUCMMetric,
    UCCXMetric,
    CMSMetric,
    IMPMetric,
    MeetingPlaceMetric,
    CollectionJob
]

__all__ = [
    "Base",
    "BaseMetric",
    "CUCMMetric",
    "UCCXMetric",
    "CMSMetric",
    "IMPMetric",
    "MeetingPlaceMetric",
    "CollectionJob",
    "METRIC_MODELS",
    "ALL_MODELS",
    "get_engine",
    "get_session_maker",
    "init_database",
    "DatabaseSession"
]

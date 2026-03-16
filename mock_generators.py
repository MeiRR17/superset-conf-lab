# =============================================================================
# Telephony Load Monitoring System - Mock Data Generators
# =============================================================================
# This module provides realistic mock data generators for all Cisco server types.
# Each generator simulates real-world patterns including:
# - Business hour fluctuations
# - Random variations within realistic ranges
# - Correlated metrics (e.g., more calls = higher CPU usage)
# - Seasonal patterns and trends
#
# These generators can be easily replaced with real API calls while maintaining
# the same interface for seamless integration.
# =============================================================================

import random
import math
from datetime import datetime, time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from config import get_settings


# =============================================================================
# Base Classes and Utilities
# =============================================================================
@dataclass
class ServerConfig:
    """Configuration for a mock server instance."""
    name: str
    ip_address: str
    server_type: str
    region: str = "default"
    capacity: int = 1000  # Maximum capacity for scaling calculations


class MockDataGenerator(ABC):
    """
    Abstract base class for mock data generators.
    Provides common functionality for realistic data generation.
    """
    
    def __init__(self, server_config: ServerConfig):
        """
        Initialize the mock data generator.
        
        Args:
            server_config: Server configuration
        """
        self.server_config = server_config
        self.settings = get_settings()
        
        # Initialize random seed for reproducible results
        random.seed(self.settings.mock_server.seed)
        
        # Track historical data for trend simulation
        self.historical_data = []
        self.last_values = {}
    
    def _get_business_hour_multiplier(self) -> float:
        """
        Calculate business hour multiplier for realistic daily patterns.
        
        Returns:
            float: Multiplier between 0.3 and 1.0
        """
        if not self.settings.mock_server.business_hours_only:
            return 1.0
        
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        # Weekend - very low activity
        if current_day >= 5:  # Saturday, Sunday
            return 0.3
        
        # Weekday business hours (8 AM - 6 PM)
        if 8 <= current_hour <= 18:
            # Peak hours: 10 AM - 4 PM
            if 10 <= current_hour <= 16:
                return 1.0
            # Early morning and late afternoon
            else:
                return 0.7
        else:
            # Outside business hours
            return 0.4
    
    def _get_random_variation(self, base_value: float, variance_percent: float = 0.2) -> float:
        """
        Add realistic random variation to a base value.
        
        Args:
            base_value: Base value to vary
            variance_percent: Maximum variance percentage (0.0 to 1.0)
        
        Returns:
            float: Value with random variation applied
        """
        if not self.settings.mock_server.data_fluctuation:
            return base_value
        
        variation = base_value * variance_percent
        random_change = random.uniform(-variation, variation)
        return max(0, base_value + random_change)
    
    def _get_sine_wave_pattern(self, base_value: float, period_minutes: int = 60) -> float:
        """
        Generate a sine wave pattern for cyclical variations.
        
        Args:
            base_value: Base value for the pattern
            period_minutes: Period of the sine wave in minutes
        
        Returns:
            float: Value with sine wave pattern applied
        """
        if not self.settings.mock_server.data_fluctuation:
            return base_value
        
        # Convert current time to minutes since midnight
        now = datetime.now()
        minutes_since_midnight = now.hour * 60 + now.minute
        
        # Calculate sine wave value
        sine_value = math.sin(2 * math.pi * minutes_since_midnight / period_minutes)
        
        # Apply sine wave with 30% variation
        variation = base_value * 0.3 * sine_value
        return max(0, base_value + variation)
    
    def _get_correlated_value(self, primary_value: float, correlation_factor: float, 
                            base_secondary: float) -> float:
        """
        Generate a correlated value based on a primary metric.
        
        Args:
            primary_value: Primary metric value
            correlation_factor: Correlation factor (-1.0 to 1.0)
            base_secondary: Base value for the secondary metric
        
        Returns:
            float: Correlated secondary value
        """
        # Normalize primary value to 0-1 range (assuming max capacity)
        normalized_primary = min(1.0, primary_value / self.server_config.capacity)
        
        # Apply correlation
        correlated_change = normalized_primary * correlation_factor * base_secondary
        
        # Add some random variation
        return self._get_random_variation(base_secondary + correlated_change, 0.1)
    
    @abstractmethod
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate mock metrics for this server type.
        
        Returns:
            Dict[str, Any]: Generated metrics
        """
        pass
    
    @abstractmethod
    def get_metric_model_class(self):
        """
        Get the SQLAlchemy model class for this metric type.
        
        Returns:
            SQLAlchemy model class
        """
        pass


# =============================================================================
# CUCM Mock Generator
# =============================================================================
class CUCMMockGenerator(MockDataGenerator):
    """
    Mock data generator for Cisco Unified Communications Manager.
    Generates realistic call statistics and system performance metrics.
    """
    
    def generate_metrics(self) -> Dict[str, Any]:
        """Generate CUCM metrics."""
        business_multiplier = self._get_business_hour_multiplier()
        
        # Base values for different metrics
        base_active_calls = int(500 * business_multiplier)
        base_registered_phones = int(800 * business_multiplier)
        base_cpu_usage = 30 * business_multiplier
        base_memory_usage = 40 * business_multiplier
        
        # Generate call statistics
        active_calls = self._get_sine_wave_pattern(base_active_calls, 120)
        total_calls_today = int(active_calls * random.uniform(8, 12))  # 8-12x current rate
        failed_calls = int(active_calls * random.uniform(0.01, 0.05))  # 1-5% failure rate
        
        # Generate device statistics
        registered_phones = self._get_random_variation(base_registered_phones, 0.05)
        total_devices = int(registered_phones * random.uniform(1.1, 1.3))  # 10-30% more devices than registered
        
        # Generate system performance (correlated with call volume)
        cpu_usage = self._get_correlated_value(active_calls, 0.0001, base_cpu_usage)
        memory_usage = self._get_correlated_value(active_calls, 0.00005, base_memory_usage)
        disk_usage = self._get_random_variation(45, 0.1)  # Relatively stable
        
        # Generate cluster information
        cluster_statuses = ["healthy", "healthy", "healthy", "degraded", "failed"]
        cluster_status = random.choices(
            cluster_statuses, 
            weights=[85, 10, 4, 0.8, 0.2],  # Mostly healthy
            k=1
        )[0]
        
        publisher_status = "online" if cluster_status != "failed" else "offline"
        subscriber_count = random.randint(2, 4)
        
        # Generate trunk statistics
        active_trunks = int(registered_phones * random.uniform(0.1, 0.3))  # 10-30% of phones
        trunk_utilization = self._get_correlated_value(active_calls, 0.0002, 60)
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_calls": int(active_calls),
            "total_calls_today": total_calls_today,
            "failed_calls": failed_calls,
            "registered_phones": int(registered_phones),
            "total_devices": total_devices,
            "cpu_usage_percent": round(cpu_usage, 1),
            "memory_usage_percent": round(memory_usage, 1),
            "disk_usage_percent": round(disk_usage, 1),
            "cluster_status": cluster_status,
            "publisher_status": publisher_status,
            "subscriber_count": subscriber_count,
            "active_trunks": active_trunks,
            "trunk_utilization_percent": round(trunk_utilization, 1)
        }
    
    def get_metric_model_class(self):
        """Get CUCM metric model class."""
        from models import CUCMMetric
        return CUCMMetric


# =============================================================================
# UCCX Mock Generator
# =============================================================================
class UCCXMockGenerator(MockDataGenerator):
    """
    Mock data generator for Unified Contact Center Express.
    Generates realistic call center and agent statistics.
    """
    
    def generate_metrics(self) -> Dict[str, Any]:
        """Generate UCCX metrics."""
        business_multiplier = self._get_business_hour_multiplier()
        
        # Base values for contact center metrics
        base_logged_in_agents = int(100 * business_multiplier)
        base_calls_in_queue = int(25 * business_multiplier)
        base_service_level = 85  # Target service level
        
        # Generate agent statistics
        logged_in_agents = self._get_sine_wave_pattern(base_logged_in_agents, 90)
        available_agents = int(logged_in_agents * random.uniform(0.3, 0.7))  # 30-70% available
        talking_agents = int(logged_in_agents * random.uniform(0.2, 0.5))  # 20-50% talking
        not_ready_agents = logged_in_agents - available_agents - talking_agents
        
        # Generate queue statistics
        calls_in_queue = self._get_sine_wave_pattern(base_calls_in_queue, 45)
        longest_wait_time = int(calls_in_queue * random.uniform(30, 120))  # 30s-2min per call
        average_wait_time = longest_wait_time * random.uniform(0.3, 0.7)
        abandoned_calls = int(calls_in_queue * random.uniform(0.02, 0.15))  # 2-15% abandonment
        
        # Generate service level metrics (inverse correlation with queue depth)
        queue_factor = min(1.0, calls_in_queue / 50)  # Normalize queue depth
        service_level = base_service_level - (queue_factor * 20)  # Service level decreases with queue
        service_level = max(60, service_level)  # Minimum 60%
        service_level = self._get_random_variation(service_level, 0.05)
        
        service_level_target = 30  # 30 seconds target
        
        # Generate contact statistics
        contacts_handled_today = int(logged_in_agents * random.uniform(15, 25))
        contacts_abandoned_today = abandoned_calls * random.randint(8, 12)  # Throughout the day
        average_handle_time = random.uniform(180, 420)  # 3-7 minutes
        
        # Generate skill group statistics
        active_skill_groups = random.randint(5, 15)
        
        # Generate system performance
        cpu_usage = self._get_correlated_value(logged_in_agents, 0.001, 25)
        memory_usage = self._get_correlated_value(logged_in_agents, 0.0005, 35)
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "logged_in_agents": int(logged_in_agents),
            "available_agents": available_agents,
            "talking_agents": talking_agents,
            "not_ready_agents": not_ready_agents,
            "calls_in_queue": int(calls_in_queue),
            "longest_wait_time_seconds": longest_wait_time,
            "average_wait_time_seconds": round(average_wait_time, 1),
            "abandoned_calls": abandoned_calls,
            "service_level_percent": round(service_level, 1),
            "service_level_target_seconds": service_level_target,
            "contacts_handled_today": contacts_handled_today,
            "contacts_abandoned_today": contacts_abandoned_today,
            "average_handle_time_seconds": round(average_handle_time, 1),
            "active_skill_groups": active_skill_groups,
            "cpu_usage_percent": round(cpu_usage, 1),
            "memory_usage_percent": round(memory_usage, 1)
        }
    
    def get_metric_model_class(self):
        """Get UCCX metric model class."""
        from models import UCCXMetric
        return UCCXMetric


# =============================================================================
# CMS Mock Generator
# =============================================================================
class CMSMockGenerator(MockDataGenerator):
    """
    Mock data generator for Cisco Meeting Server.
    Generates realistic video conferencing metrics.
    """
    
    def generate_metrics(self) -> Dict[str, Any]:
        """Generate CMS metrics."""
        business_multiplier = self._get_business_hour_multiplier()
        
        # Base values for video conferencing
        base_active_meetings = int(20 * business_multiplier)
        base_participants_per_meeting = 8
        base_resource_utilization = 40 * business_multiplier
        
        # Generate meeting statistics
        active_meetings = self._get_sine_wave_pattern(base_active_meetings, 60)
        total_meetings_today = int(active_meetings * random.uniform(4, 8))  # 4-8x current rate
        scheduled_meetings_today = int(total_meetings_today * random.uniform(0.6, 0.9))  # 60-90% scheduled
        
        # Generate participant statistics
        total_participants = int(active_meetings * base_participants_per_meeting * random.uniform(0.8, 1.5))
        unique_participants_today = int(total_participants * random.uniform(2, 4))  # 2-4x current participants
        
        # Generate resource utilization (correlated with meetings and participants)
        audio_utilization = self._get_correlated_value(total_participants, 0.01, base_resource_utilization)
        video_utilization = self._get_correlated_value(total_participants, 0.015, base_resource_utilization * 1.2)
        screen_share_utilization = self._get_correlated_value(active_meetings, 0.02, base_resource_utilization * 0.8)
        
        # Generate call bridge statistics
        active_call_bridges = int(active_meetings * random.uniform(0.8, 1.2))  # Most meetings use bridges
        total_call_bridges = random.randint(10, 20)
        
        # Generate system performance
        cpu_usage = self._get_correlated_value(total_participants, 0.002, 30)
        memory_usage = self._get_correlated_value(total_participants, 0.001, 45)
        network_bandwidth = total_participants * random.uniform(0.5, 2.0)  # 0.5-2 Mbps per participant
        
        # Generate quality metrics
        average_jitter = random.uniform(2, 15)  # 2-15ms jitter
        packet_loss = random.uniform(0.01, 0.5)  # 0.01-0.5% packet loss
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_meetings": int(active_meetings),
            "total_meetings_today": total_meetings_today,
            "scheduled_meetings_today": scheduled_meetings_today,
            "total_participants": total_participants,
            "unique_participants_today": unique_participants_today,
            "audio_resource_utilization_percent": round(audio_utilization, 1),
            "video_resource_utilization_percent": round(video_utilization, 1),
            "screen_share_utilization_percent": round(screen_share_utilization, 1),
            "active_call_bridges": active_call_bridges,
            "total_call_bridges": total_call_bridges,
            "cpu_usage_percent": round(cpu_usage, 1),
            "memory_usage_percent": round(memory_usage, 1),
            "network_bandwidth_mbps": round(network_bandwidth, 2),
            "average_jitter_ms": round(average_jitter, 2),
            "packet_loss_percent": round(packet_loss, 3)
        }
    
    def get_metric_model_class(self):
        """Get CMS metric model class."""
        from models import CMSMetric
        return CMSMetric


# =============================================================================
# IMP Mock Generator
# =============================================================================
class IMPMockGenerator(MockDataGenerator):
    """
    Mock data generator for Instant Messaging & Presence.
    Generates realistic XMPP and presence service metrics.
    """
    
    def generate_metrics(self) -> Dict[str, Any]:
        """Generate IMP metrics."""
        business_multiplier = self._get_business_hour_multiplier()
        
        # Base values for IM and presence
        base_active_sessions = int(500 * business_multiplier)
        base_logged_in_users = int(800 * business_multiplier)
        base_messages_per_hour = 2000 * business_multiplier
        
        # Generate session statistics
        active_xmpp_sessions = self._get_sine_wave_pattern(base_active_sessions, 90)
        total_sessions_today = int(active_xmpp_sessions * random.uniform(8, 15))  # 8-15x current rate
        
        # Generate user statistics
        logged_in_users = self._get_random_variation(base_logged_in_users, 0.05)
        total_users = int(logged_in_users * random.uniform(1.1, 1.4))  # 10-40% more users than logged in
        
        # Generate presence distribution
        available_users = int(logged_in_users * random.uniform(0.3, 0.5))  # 30-50% available
        busy_users = int(logged_in_users * random.uniform(0.2, 0.4))  # 20-40% busy
        away_users = int(logged_in_users * random.uniform(0.1, 0.2))  # 10-20% away
        offline_users = total_users - logged_in_users  # Remaining users are offline
        
        # Generate message statistics
        messages_sent_today = int(base_messages_per_hour * random.uniform(6, 10))  # 6-10 hours of activity
        messages_received_today = int(messages_sent_today * random.uniform(0.9, 1.1))  # Roughly equal
        file_transfers_today = int(messages_sent_today * random.uniform(0.01, 0.05))  # 1-5% of messages
        
        # Generate group chat statistics
        active_group_chats = int(logged_in_users * random.uniform(0.05, 0.15))  # 5-15% of users in group chats
        total_group_chats = random.randint(20, 50)
        
        # Generate system performance
        cpu_usage = self._get_correlated_value(active_xmpp_sessions, 0.0002, 20)
        memory_usage = self._get_correlated_value(active_xmpp_sessions, 0.0001, 30)
        
        # Generate federation statistics
        federated_domains = random.randint(2, 8)
        active_federated_sessions = int(active_xmpp_sessions * random.uniform(0.05, 0.15))  # 5-15% federated
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_xmpp_sessions": int(active_xmpp_sessions),
            "total_sessions_today": total_sessions_today,
            "logged_in_users": logged_in_users,
            "total_users": total_users,
            "users_available": available_users,
            "users_busy": busy_users,
            "users_away": away_users,
            "users_offline": offline_users,
            "messages_sent_today": messages_sent_today,
            "messages_received_today": messages_received_today,
            "file_transfers_today": file_transfers_today,
            "active_group_chats": active_group_chats,
            "total_group_chats": total_group_chats,
            "cpu_usage_percent": round(cpu_usage, 1),
            "memory_usage_percent": round(memory_usage, 1),
            "federated_domains": federated_domains,
            "active_federated_sessions": active_federated_sessions
        }
    
    def get_metric_model_class(self):
        """Get IMP metric model class."""
        from models import IMPMetric
        return IMPMetric


# =============================================================================
# Meeting Place Mock Generator
# =============================================================================
class MeetingPlaceMockGenerator(MockDataGenerator):
    """
    Mock data generator for Cisco Meeting Place (Legacy).
    Generates realistic web conferencing metrics.
    """
    
    def generate_metrics(self) -> Dict[str, Any]:
        """Generate Meeting Place metrics."""
        business_multiplier = self._get_business_hour_multiplier()
        
        # Base values for legacy conferencing
        base_active_conferences = int(15 * business_multiplier)
        base_participants_per_conference = 6
        
        # Generate conference statistics
        active_conferences = self._get_sine_wave_pattern(base_active_conferences, 75)
        total_conferences_today = int(active_conferences * random.uniform(6, 10))  # 6-10x current rate
        scheduled_conferences_today = int(total_conferences_today * random.uniform(0.5, 0.8))  # 50-80% scheduled
        
        # Generate participant statistics
        total_participants = int(active_conferences * base_participants_per_conference * random.uniform(0.7, 1.3))
        unique_participants_today = int(total_participants * random.uniform(3, 6))  # 3-6x current participants
        
        # Generate audio conference statistics
        active_audio_conferences = int(active_conferences * random.uniform(0.8, 1.0))  # Most conferences have audio
        audio_participants = int(total_participants * random.uniform(0.9, 1.0))  # Most participants use audio
        
        # Generate web conference statistics
        active_web_conferences = int(active_conferences * random.uniform(0.3, 0.7))  # 30-70% have web
        web_participants = int(total_participants * random.uniform(0.2, 0.6))  # 20-60% use web features
        
        # Generate resource utilization
        audio_utilization = self._get_correlated_value(audio_participants, 0.01, 35)
        web_utilization = self._get_correlated_value(web_participants, 0.015, 40)
        
        # Generate system performance
        cpu_usage = self._get_correlated_value(total_participants, 0.003, 25)
        memory_usage = self._get_correlated_value(total_participants, 0.002, 35)
        
        # Generate bridge statistics
        active_bridges = int(active_conferences * random.uniform(0.6, 0.9))  # 60-90% of conferences use bridges
        total_bridges = random.randint(8, 15)
        
        # Generate quality metrics
        average_conference_duration = random.uniform(25, 75)  # 25-75 minutes
        dropped_calls = int(total_conferences_today * random.uniform(0.01, 0.05))  # 1-5% drop rate
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_conferences": int(active_conferences),
            "total_conferences_today": total_conferences_today,
            "scheduled_conferences_today": scheduled_conferences_today,
            "total_participants": total_participants,
            "unique_participants_today": unique_participants_today,
            "active_audio_conferences": active_audio_conferences,
            "audio_participants": audio_participants,
            "active_web_conferences": active_web_conferences,
            "web_participants": web_participants,
            "audio_resource_utilization_percent": round(audio_utilization, 1),
            "web_resource_utilization_percent": round(web_utilization, 1),
            "cpu_usage_percent": round(cpu_usage, 1),
            "memory_usage_percent": round(memory_usage, 1),
            "active_bridges": active_bridges,
            "total_bridges": total_bridges,
            "average_conference_duration_minutes": round(average_conference_duration, 1),
            "dropped_calls": dropped_calls
        }
    
    def get_metric_model_class(self):
        """Get Meeting Place metric model class."""
        from models import MeetingPlaceMetric
        return MeetingPlaceMetric


# =============================================================================
# Mock Generator Factory
# =============================================================================
class MockGeneratorFactory:
    """
    Factory class for creating mock data generators.
    Provides a clean interface for generator instantiation.
    """
    
    _generators = {
        "cucm": CUCMMockGenerator,
        "uccx": UCCXMockGenerator,
        "cms": CMSMockGenerator,
        "imp": IMPMockGenerator,
        "meeting_place": MeetingPlaceMockGenerator
    }
    
    @classmethod
    def create_generator(cls, server_type: str, server_config: ServerConfig) -> MockDataGenerator:
        """
        Create a mock data generator for the specified server type.
        
        Args:
            server_type: Type of server (cucm, uccx, cms, imp, meeting_place)
            server_config: Server configuration
        
        Returns:
            MockDataGenerator: Configured generator instance
        
        Raises:
            ValueError: If server type is not supported
        """
        if server_type not in cls._generators:
            raise ValueError(f"Unsupported server type: {server_type}")
        
        generator_class = cls._generators[server_type]
        return generator_class(server_config)
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """
        Get list of supported server types.
        
        Returns:
            List[str]: Supported server types
        """
        return list(cls._generators.keys())
    
    @classmethod
    def create_all_generators(cls, server_configs: Dict[str, ServerConfig]) -> Dict[str, MockDataGenerator]:
        """
        Create generators for all provided server configurations.
        
        Args:
            server_configs: Dictionary mapping server types to configurations
        
        Returns:
            Dict[str, MockDataGenerator]: Dictionary of generators
        """
        generators = {}
        for server_type, config in server_configs.items():
            if server_type in cls._generators:
                generators[server_type] = cls.create_generator(server_type, config)
        return generators


# =============================================================================
# Unified Generator Factory with Feature Toggle Support
# =============================================================================
class UnifiedGeneratorFactory:
    """
    Unified factory that creates either mock or real generators based on feature toggles.
    This is the main factory that should be used in the application.
    """
    
    @classmethod
    def create_generator(cls, server_type: str, server_config: ServerConfig, use_real: bool = False) -> MockDataGenerator:
        """
        Create a generator for the specified server type based on feature toggle.
        
        Args:
            server_type: Type of server (cucm, uccx, cms, imp, meeting_place)
            server_config: Server configuration
            use_real: Whether to use real API (from feature toggle)
        
        Returns:
            MockDataGenerator: Configured generator instance (mock or real)
        """
        if use_real:
            # Import here to avoid circular imports
            from real_generators import RealGeneratorFactory
            return RealGeneratorFactory.create_generator(server_type, server_config)
        else:
            return MockGeneratorFactory.create_generator(server_type, server_config)
    
    @classmethod
    def create_all_generators(cls, server_configs: Dict[str, ServerConfig]) -> Dict[str, MockDataGenerator]:
        """
        Create generators for all server types based on feature toggles.
        
        Args:
            server_configs: Dictionary mapping server types to configurations
        
        Returns:
            Dict[str, MockDataGenerator]: Dictionary of generators (mock or real)
        """
        settings = get_settings()
        generators = {}
        
        # Check each server type and create appropriate generator
        if "cucm" in server_configs:
            generators["cucm"] = cls.create_generator(
                "cucm", 
                server_configs["cucm"], 
                settings.cisco.use_real_cucm
            )
        
        if "uccx" in server_configs:
            generators["uccx"] = cls.create_generator(
                "uccx", 
                server_configs["uccx"], 
                settings.cisco.use_real_uccx
            )
        
        if "cms" in server_configs:
            generators["cms"] = cls.create_generator(
                "cms", 
                server_configs["cms"], 
                settings.cisco.use_real_cms
            )
        
        if "imp" in server_configs:
            generators["imp"] = cls.create_generator(
                "imp", 
                server_configs["imp"], 
                settings.cisco.use_real_imp
            )
        
        if "meeting_place" in server_configs:
            generators["meeting_place"] = cls.create_generator(
                "meeting_place", 
                server_configs["meeting_place"], 
                settings.cisco.use_real_meeting_place
            )
        
        return generators
    
    @classmethod
    def get_generator_status(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all generators (mock vs real).
        
        Returns:
            Dict[str, Dict[str, Any]]: Generator status information
        """
        settings = get_settings()
        
        return {
            "cucm": {
                "using_real_api": settings.cisco.use_real_cucm,
                "generator_type": "Real" if settings.cisco.use_real_cucm else "Mock"
            },
            "uccx": {
                "using_real_api": settings.cisco.use_real_uccx,
                "generator_type": "Real" if settings.cisco.use_real_uccx else "Mock"
            },
            "cms": {
                "using_real_api": settings.cisco.use_real_cms,
                "generator_type": "Real" if settings.cisco.use_real_cms else "Mock"
            },
            "imp": {
                "using_real_api": settings.cisco.use_real_imp,
                "generator_type": "Real" if settings.cisco.use_real_imp else "Mock"
            },
            "meeting_place": {
                "using_real_api": settings.cisco.use_real_meeting_place,
                "generator_type": "Real" if settings.cisco.use_real_meeting_place else "Mock"
            }
        }


# =============================================================================
# Default Server Configurations
# =============================================================================
def get_default_server_configs() -> Dict[str, ServerConfig]:
    """
    Get default server configurations for all supported types.
    
    Returns:
        Dict[str, ServerConfig]: Default configurations
    """
    settings = get_settings()
    
    return {
        "cucm": ServerConfig(
            name="CUCM-Primary",
            ip_address=settings.cisco.cucm_host,
            server_type="cucm",
            region="primary"
        ),
        "uccx": ServerConfig(
            name="UCCX-Primary",
            ip_address=settings.cisco.uccx_host,
            server_type="uccx",
            region="primary"
        ),
        "cms": ServerConfig(
            name="CMS-Primary",
            ip_address=settings.cisco.cms_host,
            server_type="cms",
            region="primary"
        ),
        "imp": ServerConfig(
            name="IMP-Primary",
            ip_address=settings.cisco.imp_host,
            server_type="imp",
            region="primary"
        ),
        "meeting_place": ServerConfig(
            name="MeetingPlace-Primary",
            ip_address=settings.cisco.meeting_place_host,
            server_type="meeting_place",
            region="primary"
        )
    }


# =============================================================================
# Convenience Functions
# =============================================================================
def create_mock_generators() -> Dict[str, MockDataGenerator]:
    """
    Create mock generators for all default server types.
    
    Returns:
        Dict[str, MockDataGenerator]: Dictionary of generators
    """
    configs = get_default_server_configs()
    return MockGeneratorFactory.create_all_generators(configs)


def create_generators() -> Dict[str, MockDataGenerator]:
    """
    Create generators for all default server types using feature toggles.
    This is the main function that should be used in the application.
    
    Returns:
        Dict[str, MockDataGenerator]: Dictionary of generators (mock or real based on toggles)
    """
    # =============================================================================
# TGW (Trunk Gateway) Mock Generator
# =============================================================================
class TGWMockGenerator(MockDataGenerator):
    """
    Mock data generator for TGW (Trunk Gateway) routers.
    
    Generates realistic SNMP-style metrics for:
    - Active trunk utilization and status
    - Interface bandwidth and error counters
    - CPU and memory usage
    - Trunk registration status
    """
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate realistic TGW metrics with business hour patterns.
        
        Returns:
            Dict with 'server_type': 'tgw' and 'metrics' dict
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
# SBC (Session Border Controller) Mock Generator
# =============================================================================
class SBCMockGenerator(MockDataGenerator):
    """
    Mock data generator for SBC (Session Border Controller) devices.
    
    Generates realistic REST API-style metrics for:
    - Concurrent session statistics
    - Call rates and DSP utilization
    - CPU and memory usage
    - Call rejection and error rates
    """
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate realistic SBC metrics with call center patterns.
        
        Returns:
            Dict with 'server_type': 'sbc' and 'metrics' dict
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
        failed_calls = int(random.uniform(0, 5) * (1 if cpu_usage > 85 else 0.2))
        
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
# Expressway Mock Generator
# =============================================================================
class ExpresswayMockGenerator(MockDataGenerator):
    """
    Mock data generator for Expressway traversal servers.
    
    Generates realistic REST API-style metrics for:
    - Traversal and non-traversal call statistics
    - Device registration status
    - Relay and media resource utilization
    - CPU and memory usage
    """
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate realistic Expressway metrics with security patterns.
        
        Returns:
            Dict with 'server_type': 'expressway' and 'metrics' dict
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
# Updated Mock Generator Factory
# =============================================================================
class MockGeneratorFactory:
    """
    Factory class for creating mock data generators.
    
    Supports all equipment types: uccx, cucm, cms, imp, meeting_place, tgw, sbc, expressway
    """
    
    _generators = {
        "uccx": lambda config: UCCXMockGenerator(config),
        "cucm": lambda config: CUCMMockGenerator(config),
        "cms": lambda config: CMSMockGenerator(config),
        "imp": lambda config: IMPMockGenerator(config),
        "meeting_place": lambda config: MeetingPlaceMockGenerator(config),
        "tgw": lambda config: TGWMockGenerator(config),
        "sbc": lambda config: SBCMockGenerator(config),
        "expressway": lambda config: ExpresswayMockGenerator(config),
    }
    
    @classmethod
    def create_generator(cls, server_type: str, config: CiscoServerConfig) -> MockDataGenerator:
        """
        Create mock generator for specified server type.
        """
        if server_type not in cls._generators:
            raise ValueError(f"Unknown server type: {server_type}")
        
        return cls._generators[server_type](config)
    
    @classmethod
    def create_all_generators(cls, configs: Dict[str, CiscoServerConfig]) -> Dict[str, MockDataGenerator]:
        """
        Create mock generators for all configured server types.
        """
        generators = {}
        for server_type, config in configs.items():
            try:
                generators[server_type] = cls.create_generator(server_type, config)
            except Exception as e:
                # Log error but continue with other generators
                generators[server_type] = None
        return generators
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """
        Get list of supported server types.
        """
        return list(cls._generators.keys())


def create_mock_generators() -> Dict[str, MockDataGenerator]:
    """
    Create mock generators using default configurations.
    """
    configs = get_default_server_configs()
    return MockGeneratorFactory.create_all_generators(configs)


def generate_all_mock_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Generate mock metrics for all server types.
    
    Returns:
        Dict[str, Dict[str, Any]]: Generated metrics by server type
    """
    generators = create_mock_generators()
    metrics = {}
    
    for server_type, generator in generators.items():
        try:
            metrics[server_type] = generator.generate_metrics()
        except Exception as e:
            metrics[server_type] = {
                "error": str(e),
                "server_name": generator.server_config.name,
                "server_ip": generator.server_config.ip_address
            }
    
    return metrics


def generate_all_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Generate metrics for all server types using feature toggles.
    This is the main function that should be used in the application.
    
    Returns:
        Dict[str, Dict[str, Any]]: Generated metrics by server type (mock or real based on toggles)
    """
    generators = create_generators()
    metrics = {}
    
    for server_type, generator in generators.items():
        try:
            metrics[server_type] = generator.generate_metrics()
        except Exception as e:
            metrics[server_type] = {
                "error": str(e),
                "server_name": generator.server_config.name,
                "server_ip": generator.server_config.ip_address,
                "generator_type": "Real" if isinstance(generator, RealDataGenerator) else "Mock"
            }
    
    return metrics


__all__ = [
    "ServerConfig",
    "MockDataGenerator",
    "CUCMMockGenerator",
    "UCCXMockGenerator",
    "CMSMockGenerator",
    "IMPMockGenerator",
    "MeetingPlaceMockGenerator",
    "MockGeneratorFactory",
    "UnifiedGeneratorFactory",
    "get_default_server_configs",
    "create_mock_generators",
    "create_generators",
    "generate_all_mock_metrics",
    "generate_all_metrics"
]

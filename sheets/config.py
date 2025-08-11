
"""
Configuration module for Google Sheets integration.

This module provides:
- Comprehensive configuration constants and mappings
- Rate limiting and API management settings
- Sheet template definitions and specifications
- Error handling configuration
- Performance optimization parameters
- Authentication and security settings

Features:
- Centralized configuration management
- Environment-specific settings
- Flexible rate limiting parameters
- Comprehensive sheet type definitions
- Color scheme and formatting constants
- API quota and usage tracking settings
"""

import os
from typing import Dict, List, Any, Optional
from datetime import timedelta

# === CORE CONFIGURATION ===

# Rate limiting configuration for Google Sheets API
DEFAULT_REQUEST_INTERVAL = 0.1  # 100ms between requests - prevents rate limiting
DEFAULT_MAX_RETRIES = 5  # Maximum number of retry attempts for failed requests
DEFAULT_BATCH_SIZE = 50  # Optimal batch size for bulk operations
DEFAULT_TIMEOUT = 30  # Request timeout in seconds

# Connection and authentication settings
CONNECTION_RETRY_DELAY = 2.0  # Base delay for exponential backoff
MAX_CONNECTION_ATTEMPTS = 3  # Maximum connection retry attempts
CREDENTIAL_REFRESH_INTERVAL = 3600  # Refresh credentials every hour

# === SHEET SPECIFICATIONS ===

# Supported sheet types with their configurations
SUPPORTED_SHEETS = {
    "Current Teams": {
        "rows": 100,
        "cols": 8,
        "description": "Active team signups and player assignments",
        "features": ["real_time_updates", "status_indicators", "auto_formatting"]
    },
    "Events History": {
        "rows": 200,
        "cols": 8,
        "description": "Historical record of all events and signups",
        "features": ["timestamp_tracking", "trend_analysis", "data_archival"]
    },
    "Player Stats": {
        "rows": 500,
        "cols": 21,
        "description": "Comprehensive player statistics and performance metrics",
        "features": ["advanced_calculations", "performance_tracking", "ranking_system"]
    },
    "Results History": {
        "rows": 300,
        "cols": 10,
        "description": "Match results and outcome tracking",
        "features": ["win_loss_tracking", "performance_analysis", "team_statistics"]
    },
    "Blocked Users": {
        "rows": 100,
        "cols": 6,
        "description": "User moderation and access control",
        "features": ["moderation_tracking", "reason_logging", "admin_oversight"]
    },
    "Discord Members": {
        "rows": 1000,
        "cols": 10,
        "description": "Complete Discord member directory and status",
        "features": ["member_sync", "role_tracking", "activity_monitoring"]
    },
    "Match Statistics": {
        "rows": 400,
        "cols": 15,
        "description": "Detailed match performance and analytics",
        "features": ["statistical_analysis", "performance_metrics", "trend_identification"]
    },
    "Alliance Tracking": {
        "rows": 200,
        "cols": 12,
        "description": "Alliance relationships and diplomatic status",
        "features": ["relationship_mapping", "diplomatic_tracking", "alliance_history"]
    }
}

# === SHEET CONFIGURATIONS (LEGACY COMPATIBILITY) ===
# These configurations are required by the template_creator and worksheet_handlers modules
# They provide specific header configurations and sheet specifications

SHEET_CONFIGS = {
    "Current Teams": {
        "headers": ["Timestamp", "Team", "Player Count", "Players", "Status"],
        "rows": 100,
        "cols": 5
    },
    "Player Stats": {
        "headers": [
            "User ID", "Name", "Main Wins", "Main Losses", "Team2 Wins", "Team2 Losses",
            "Team3 Wins", "Team3 Losses", "Total Wins", "Total Losses", "Absents", "Blocked",
            "Power Rating", "Cavalry", "Mages", "Archers", "Infantry", "Whale Status"
        ],
        "rows": 300,
        "cols": 20
    },
    "Results History": {
        "headers": ["Date", "Team", "Result", "Players", "By", "Total Wins", "Total Losses"],
        "rows": 1000,
        "cols": 7
    },
    "Match Statistics": {
        "headers": [
            "Match ID", "Date", "Team", "Result", "Enemy Alliance Name", "Enemy Alliance Tag",
            "Our Matchmaking Power", "Our Lifestone Points", "Our Occupation Points",
            "Our Gathering Points", "Our Total Kills", "Our Total Wounded", "Our Total Healed",
            "Our Lifestone Obtained", "Enemy Matchmaking Power", "Enemy Lifestone Points", 
            "Enemy Occupation Points", "Enemy Gathering Points", "Enemy Total Kills", 
            "Enemy Total Wounded", "Enemy Total Healed", "Enemy Lifestone Obtained", 
            "Players Participated", "Recorded By", "Notes"
        ],
        "rows": 500,
        "cols": 25
    },
    "Alliance Tracking": {
        "headers": [
            "Alliance Name", "Alliance Tag", "Matches Against", "Wins Against Them", 
            "Losses Against Them", "Win Rate vs Them", "Average Enemy Power",
            "Difficulty Rating", "Strategy Notes", "Last Fought", "Server/Kingdom",
            "Alliance Level", "Activity Level", "Threat Level", "Additional Notes"
        ],
        "rows": 200,
        "cols": 15
    },
    "Notification Preferences": {
        "headers": [
            "User ID", "Method", "Event Reminders", "Result Notifications", "Team Updates",
            "Reminder Times", "Quiet Start", "Quiet End", "Timezone Offset", "Last Updated"
        ],
        "rows": 300,
        "cols": 10
    },
    "Dashboard": {
        "headers": ["Component", "Value", "Last Updated"],
        "rows": 50,
        "cols": 10
    }
}

# Team mapping for display names and internal keys
TEAM_MAPPING = {
    "main_team": "Main Team", 
    "team_2": "Team 2", 
    "team_3": "Team 3"
}

# === FORMATTING AND STYLING ===

# Color schemes for different sheet types and elements
COLORS = {
    # Header colors for different sheet types
    "HEADER_PRIMARY": {"red": 0.2, "green": 0.6, "blue": 0.8},  # Blue header
    "HEADER_SUCCESS": {"red": 0.2, "green": 0.7, "blue": 0.3},  # Green header
    "HEADER_WARNING": {"red": 0.9, "green": 0.6, "blue": 0.2},  # Orange header
    "HEADER_DANGER": {"red": 0.8, "green": 0.2, "blue": 0.2},   # Red header
    
    # Status indicator colors
    "STATUS_ACTIVE": {"red": 0.2, "green": 0.8, "blue": 0.2},   # Active/Online
    "STATUS_READY": {"red": 0.3, "green": 0.7, "blue": 0.9},    # Ready/Available
    "STATUS_PARTIAL": {"red": 0.9, "green": 0.7, "blue": 0.2},  # Partial/Warning
    "STATUS_EMPTY": {"red": 0.9, "green": 0.3, "blue": 0.3},    # Empty/Error
    
    # Background colors for data cells
    "BG_LIGHT": {"red": 0.95, "green": 0.95, "blue": 0.95},     # Light gray
    "BG_WHITE": {"red": 1.0, "green": 1.0, "blue": 1.0},        # Pure white
    "BG_HIGHLIGHT": {"red": 0.9, "green": 0.95, "blue": 1.0},   # Light blue highlight
}

# Text formatting specifications
TEXT_FORMATS = {
    "HEADER": {
        "bold": True,
        "fontSize": 11,
        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}
    },
    "SUBHEADER": {
        "bold": True,
        "fontSize": 10,
        "foregroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2}
    },
    "NORMAL": {
        "bold": False,
        "fontSize": 9,
        "foregroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1}
    },
    "HIGHLIGHT": {
        "bold": True,
        "fontSize": 10,
        "foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.8}
    }
}

# === PERFORMANCE AND OPTIMIZATION ===

# Cache configuration for improved performance
CACHE_CONFIG = {
    "DEFAULT_EXPIRY": 300,      # 5 minutes default cache expiry
    "PLAYER_STATS_EXPIRY": 600, # 10 minutes for player stats
    "EVENTS_EXPIRY": 60,        # 1 minute for event data (real-time)
    "MEMBER_SYNC_EXPIRY": 1800, # 30 minutes for member sync
    "MAX_CACHE_SIZE": 100       # Maximum number of cached items
}

# Batch operation settings for optimal performance
BATCH_SETTINGS = {
    "MEMBER_SYNC_BATCH": 25,    # Members processed per batch
    "STATS_UPDATE_BATCH": 15,   # Stats updates per batch
    "HISTORY_ARCHIVE_BATCH": 50, # History entries per batch
    "FORMATTING_BATCH": 10      # Formatting operations per batch
}

# === DATA VALIDATION AND CONSTRAINTS ===

# Field validation rules and constraints
VALIDATION_RULES = {
    "USER_ID": {
        "type": "string",
        "pattern": r"^\d{17,19}$",  # Discord user ID format
        "required": True
    },
    "USERNAME": {
        "type": "string",
        "max_length": 32,
        "min_length": 1,
        "required": True
    },
    "TEAM_NAME": {
        "type": "string",
        "allowed_values": ["main_team", "team_2", "team_3"],
        "required": True
    },
    "TIMESTAMP": {
        "type": "datetime",
        "format": "ISO8601",
        "required": True
    }
}

# Data integrity constraints
INTEGRITY_CONSTRAINTS = {
    "MAX_PLAYERS_PER_TEAM": 8,      # Maximum players per team
    "MIN_TEAM_SIZE": 1,             # Minimum viable team size
    "MAX_HISTORY_ENTRIES": 1000,    # Maximum history entries to retain
    "MAX_USERNAME_LENGTH": 32,      # Discord username length limit
    "MAX_DISPLAY_NAME_LENGTH": 32   # Discord display name length limit
}

# === ERROR HANDLING AND RECOVERY ===

# Error handling configuration
ERROR_CONFIG = {
    "MAX_CONSECUTIVE_FAILURES": 5,   # Max failures before circuit breaker
    "FAILURE_RESET_TIME": 300,       # Time to reset failure counter (seconds)
    "CRITICAL_ERROR_THRESHOLD": 10,  # Threshold for critical error alerts
    "AUTO_RECOVERY_ATTEMPTS": 3      # Automatic recovery attempts
}

# Retry policies for different operation types
RETRY_POLICIES = {
    "READ_OPERATIONS": {
        "max_retries": 3,
        "base_delay": 1.0,
        "exponential_base": 2,
        "max_delay": 30.0
    },
    "WRITE_OPERATIONS": {
        "max_retries": 5,
        "base_delay": 2.0,
        "exponential_base": 2,
        "max_delay": 60.0
    },
    "BATCH_OPERATIONS": {
        "max_retries": 2,
        "base_delay": 5.0,
        "exponential_base": 1.5,
        "max_delay": 120.0
    }
}

# === MONITORING AND ANALYTICS ===

# Usage tracking configuration
USAGE_TRACKING = {
    "TRACK_API_CALLS": True,         # Enable API call tracking
    "TRACK_PERFORMANCE": True,       # Enable performance monitoring
    "TRACK_ERROR_RATES": True,       # Enable error rate monitoring
    "REPORTING_INTERVAL": 3600,      # Report interval in seconds (1 hour)
    "METRICS_RETENTION": 86400 * 7   # Keep metrics for 7 days
}

# Performance thresholds and alerts
PERFORMANCE_THRESHOLDS = {
    "MAX_REQUEST_TIME": 5.0,         # Maximum acceptable request time (seconds)
    "HIGH_ERROR_RATE": 0.1,          # High error rate threshold (10%)
    "RATE_LIMIT_WARNING": 0.8,       # Rate limit usage warning threshold (80%)
    "MEMORY_USAGE_WARNING": 0.9      # Memory usage warning threshold (90%)
}

# === ENVIRONMENT-SPECIFIC SETTINGS ===

def get_environment_config() -> Dict[str, Any]:
    """
    Get environment-specific configuration settings.
    
    Returns:
        dict: Environment-specific configuration
        
    Features:
    - Development vs production settings
    - Environment variable integration
    - Fallback configuration values
    - Security-conscious defaults
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    base_config = {
        "development": {
            "DEBUG_MODE": True,
            "VERBOSE_LOGGING": True,
            "RATE_LIMIT_STRICT": False,
            "CACHE_ENABLED": False,
            "AUTO_CREATE_SHEETS": True
        },
        "production": {
            "DEBUG_MODE": False,
            "VERBOSE_LOGGING": False,
            "RATE_LIMIT_STRICT": True,
            "CACHE_ENABLED": True,
            "AUTO_CREATE_SHEETS": False
        }
    }
    
    return base_config.get(env, base_config["development"])

# === AUTHENTICATION AND SECURITY ===

# Security configuration
SECURITY_CONFIG = {
    "REQUIRE_CREDENTIALS": True,      # Require valid credentials
    "VALIDATE_PERMISSIONS": True,     # Validate sheet permissions
    "ENCRYPT_SENSITIVE_DATA": True,   # Encrypt sensitive data in logs
    "AUDIT_OPERATIONS": True,         # Enable operation auditing
    "SESSION_TIMEOUT": 3600          # Session timeout in seconds
}

# Credential configuration
CREDENTIAL_CONFIG = {
    "SCOPES": [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ],
    "CREDENTIAL_SOURCES": [
        "GOOGLE_SHEETS_CREDENTIALS",  # Environment variable
        "credentials.json",           # Local file
        "service_account.json"        # Alternative local file
    ],
    "REFRESH_THRESHOLD": 300         # Refresh credentials 5 minutes before expiry
}

# === FEATURE FLAGS ===

# Feature toggles for experimental or optional functionality
FEATURE_FLAGS = {
    "ENABLE_ADVANCED_FORMATTING": True,    # Advanced sheet formatting
    "ENABLE_REAL_TIME_SYNC": True,         # Real-time data synchronization
    "ENABLE_PERFORMANCE_METRICS": True,    # Performance monitoring
    "ENABLE_AUTO_BACKUP": True,            # Automatic data backup
    "ENABLE_SMART_CACHING": True,          # Intelligent caching
    "ENABLE_BATCH_OPTIMIZATION": True,     # Batch operation optimization
    "ENABLE_ERROR_RECOVERY": True,         # Automatic error recovery
    "ENABLE_USAGE_ANALYTICS": True         # Usage analytics and reporting
}

# === EXPORT CONFIGURATION ===

# Make important configurations available for import
__all__ = [
    "SUPPORTED_SHEETS",
    "SHEET_CONFIGS",
    "TEAM_MAPPING",
    "COLORS", 
    "TEXT_FORMATS",
    "DEFAULT_REQUEST_INTERVAL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_BATCH_SIZE",
    "CACHE_CONFIG",
    "BATCH_SETTINGS",
    "VALIDATION_RULES",
    "INTEGRITY_CONSTRAINTS",
    "ERROR_CONFIG",
    "RETRY_POLICIES",
    "USAGE_TRACKING",
    "PERFORMANCE_THRESHOLDS",
    "SECURITY_CONFIG",
    "CREDENTIAL_CONFIG",
    "FEATURE_FLAGS",
    "get_environment_config"
]

# Module metadata
__version__ = "2.1.0"
__author__ = "RoW Bot Development Team"
__description__ = "Comprehensive configuration for Google Sheets integration"
__last_updated__ = "2024-01-15"

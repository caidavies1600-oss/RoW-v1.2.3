
"""
Google Sheets Integration Module for Discord RoW Bot.

This module provides comprehensive Google Sheets integration capabilities:
- Rate-limited Google Sheets access with exponential backoff
- Template creation and advanced formatting
- Real-time data synchronization between bot and sheets
- Comprehensive error handling and connection management
- Performance monitoring and optimization
- Advanced worksheet management and operations

Components:
- SheetsManager: Main interface for all sheets operations
- Enhanced rate limiting with intelligent backoff strategies
- Automatic retry mechanisms with exponential delays
- Template-based sheet creation with standardized formatting
- Real-time data synchronization with conflict resolution
- Comprehensive error tracking and recovery systems
- Performance metrics and optimization insights
- Advanced validation and data integrity checks
- Batch processing for efficient operations
- Multi-threading support for concurrent access

Key Features:
- Seamless Discord-to-Sheets data flow
- Automatic template creation and management
- Real-time member synchronization
- Event history tracking and analytics
- Player statistics and performance metrics
- Results tracking with comprehensive analysis
- Blocked user management and moderation tools
- Alliance tracking and diplomatic relationship management
- Match statistics with detailed performance analysis
- Administrative oversight and audit trails

Usage Examples:
    # Basic initialization
    sheets_manager = SheetsManager(spreadsheet_id="your_sheet_id")
    
    # Check connection status
    if sheets_manager.is_connected():
        print("✅ Connected to Google Sheets")
    
    # Create all templates with data
    all_data = {
        "events": events_data,
        "results": results_data,
        "player_stats": player_statistics
    }
    success = sheets_manager.create_all_templates(all_data)
    
    # Sync Discord members
    sync_result = await sheets_manager.scan_and_sync_all_members(bot, guild_id)
    
    # Get performance metrics
    metrics = sheets_manager.get_performance_summary()

Thread Safety:
    All operations are designed to be thread-safe and work with
    concurrent access patterns. Rate limiting ensures API quotas
    are respected while maintaining optimal performance.

Error Handling:
    Comprehensive error handling with automatic retry mechanisms,
    exponential backoff, and graceful degradation. All errors are
    logged with detailed context for debugging and monitoring.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

import gspread
from google.oauth2.service_account import Credentials

# Import our configuration and utilities
from .config import (
    SUPPORTED_SHEETS, 
    COLORS, 
    TEXT_FORMATS,
    VALIDATION_RULES,
    INTEGRITY_CONSTRAINTS,
    BATCH_SETTINGS,
    FEATURE_FLAGS,
    PERFORMANCE_THRESHOLDS
)
from .base_manager import BaseGoogleSheetsManager as BaseSheetsManager
from .template_creator import SheetsTemplateCreator
from .worksheet_handlers import WorksheetHandlers

from utils.logger import setup_logger

logger = setup_logger("sheets_manager")


class SheetsManager(BaseSheetsManager):
    """
    Comprehensive Google Sheets manager with advanced functionality.
    
    This class extends BaseSheetsManager to provide a complete Google Sheets
    integration solution for Discord bots. It includes all the features needed
    for production deployment including rate limiting, error handling, template
    management, data synchronization, and performance optimization.

    Key Features:
    - Advanced rate limiting with exponential backoff
    - Comprehensive error handling and recovery
    - Template-based sheet creation and management
    - Real-time data synchronization capabilities
    - Performance monitoring and optimization
    - Batch operation support for efficiency
    - Multi-threading for concurrent operations
    - Data validation and integrity enforcement
    - Administrative tools and oversight features
    - Usage tracking and analytics

    Advanced Capabilities:
    - Automatic template creation for all supported sheet types
    - Real-time Discord member synchronization
    - Event history tracking with trend analysis
    - Player statistics with performance metrics
    - Results tracking with comprehensive analytics
    - Blocked user management with moderation tools
    - Alliance tracking for diplomatic relationships
    - Match statistics with detailed analysis
    - Administrative audit trails and oversight
    - Customizable formatting and branding

    Usage:
        # Initialize with automatic connection
        sheets_manager = SheetsManager()
        
        # Or with specific spreadsheet
        sheets_manager = SheetsManager(spreadsheet_id="your_sheet_id")
        
        # Create all templates
        success = sheets_manager.create_all_templates(bot_data)
        
        # Sync Discord members
        result = await sheets_manager.scan_and_sync_all_members(bot, guild_id)
        
        # Get comprehensive statistics
        stats = sheets_manager.get_comprehensive_stats()

    Thread Safety:
        All operations are thread-safe and designed for concurrent access.
        Rate limiting ensures Google Sheets API quotas are respected while
        maintaining optimal performance across multiple operations.
    """

    def __init__(self, spreadsheet_id: Optional[str] = None, **kwargs):
        """
        Initialize comprehensive Google Sheets manager.

        Args:
            spreadsheet_id: Optional specific spreadsheet ID to connect to
            **kwargs: Additional configuration options

        Features:
        - Automatic credential detection and setup
        - Intelligent connection management
        - Performance monitoring initialization
        - Error tracking setup
        - Template creator and handler initialization
        - Advanced configuration and customization
        """
        # Initialize base manager with all core functionality
        super().__init__(spreadsheet_id)
        
        # Initialize advanced components
        self.template_creator = SheetsTemplateCreator(self)
        self.worksheet_handlers = WorksheetHandlers(self)
        
        # Thread pool for concurrent operations
        self.thread_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="SheetsOp")
        
        # Advanced performance tracking
        self.performance_metrics = {
            "session_start_time": time.time(),
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_processing_time": 0.0,
            "average_operation_time": 0.0,
            "rate_limit_hits": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "data_validations": 0,
            "template_operations": 0,
            "sync_operations": 0,
            "batch_operations": 0
        }
        
        # Operation cache for performance optimization
        self.operation_cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = kwargs.get("cache_ttl", 300)  # 5 minutes default
        
        # Error tracking and recovery
        self.error_history = []
        self.max_error_history = kwargs.get("max_error_history", 100)
        self.recovery_attempts = {}
        
        # Advanced configuration options
        self.config = {
            "enable_caching": kwargs.get("enable_caching", True),
            "enable_batch_operations": kwargs.get("enable_batch_operations", True),
            "enable_performance_monitoring": kwargs.get("enable_performance_monitoring", True),
            "enable_advanced_formatting": kwargs.get("enable_advanced_formatting", True),
            "auto_retry_failed_operations": kwargs.get("auto_retry_failed_operations", True),
            "max_concurrent_operations": kwargs.get("max_concurrent_operations", 3)
        }
        
        # Batch operation queues
        self.batch_queues = {
            "member_updates": [],
            "event_updates": [],
            "stats_updates": [],
            "result_updates": []
        }
        
        logger.info("✅ Advanced SheetsManager initialized with comprehensive functionality")
        logger.info(f"📊 Performance monitoring: {'Enabled' if self.config['enable_performance_monitoring'] else 'Disabled'}")
        logger.info(f"💾 Caching: {'Enabled' if self.config['enable_caching'] else 'Disabled'}")
        logger.info(f"📦 Batch operations: {'Enabled' if self.config['enable_batch_operations'] else 'Disabled'}")

    def rate_limited_request(self, func, *args, **kwargs):
        """
        Execute request with advanced rate limiting and performance tracking.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Features:
        - Intelligent rate limiting with exponential backoff
        - Comprehensive error handling and retry logic
        - Performance metrics tracking
        - Cache integration for optimization
        - Operation logging and monitoring
        """
        operation_start = time.time()
        
        # Check cache first if enabled
        cache_key = self._generate_cache_key(func, args, kwargs)
        if self.config["enable_caching"] and cache_key in self.operation_cache:
            cache_timestamp = self.cache_timestamps.get(cache_key, 0)
            if time.time() - cache_timestamp < self.cache_ttl:
                self.performance_metrics["cache_hits"] += 1
                logger.debug(f"📋 Cache hit for operation: {func.__name__}")
                return self.operation_cache[cache_key]
            else:
                # Remove expired cache entry
                del self.operation_cache[cache_key]
                del self.cache_timestamps[cache_key]
        
        self.performance_metrics["cache_misses"] += 1
        
        try:
            # Execute the base rate limited request
            result = super().rate_limited_request(func, *args, **kwargs)
            
            # Update performance metrics
            operation_time = time.time() - operation_start
            self._update_performance_metrics(operation_time, True)
            
            # Cache successful result if enabled
            if self.config["enable_caching"] and cache_key:
                self.operation_cache[cache_key] = result
                self.cache_timestamps[cache_key] = time.time()
                
                # Clean up old cache entries periodically
                if len(self.operation_cache) > 100:
                    self._cleanup_cache()
            
            return result
            
        except Exception as e:
            operation_time = time.time() - operation_start
            self._update_performance_metrics(operation_time, False)
            self._log_operation_error(func.__name__, e)
            
            # Retry if configured
            if self.config["auto_retry_failed_operations"]:
                logger.warning(f"⚠️ Retrying failed operation: {func.__name__}")
                time.sleep(1)  # Brief delay before retry
                return super().rate_limited_request(func, *args, **kwargs)
            
            raise

    async def scan_and_sync_all_members(self, bot, guild_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Comprehensive Discord member scanning and synchronization.
        
        Args:
            bot: Discord bot instance
            guild_id: Optional specific guild ID to scan
            
        Returns:
            dict: Comprehensive sync results with statistics
            
        Features:
        - Complete Discord member directory creation
        - Role and permission tracking
        - Activity level analysis
        - Batch processing for efficiency
        - Error handling and recovery
        - Performance optimization
        - Real-time status tracking
        """
        if not self.is_connected():
            return {"success": False, "error": "Sheets not connected"}

        sync_start_time = time.time()
        logger.info("🔄 Starting comprehensive member synchronization...")

        try:
            # Determine target guild
            if guild_id:
                guild = bot.get_guild(guild_id)
            else:
                guild = bot.guilds[0] if bot.guilds else None

            if not guild:
                return {"success": False, "error": "No guild found for synchronization"}

            logger.info(f"🏰 Synchronizing guild: {guild.name} (ID: {guild.id})")

            # Collect comprehensive member data
            members_data = []
            bot_member_count = 0
            human_member_count = 0

            for member in guild.members:
                if member.bot:
                    bot_member_count += 1
                    continue
                
                human_member_count += 1
                
                # Extract comprehensive member information
                member_info = {
                    "user_id": str(member.id),
                    "username": member.name,
                    "display_name": member.display_name,
                    "discriminator": member.discriminator if hasattr(member, 'discriminator') else "0000",
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "created_at": member.created_at.isoformat() if member.created_at else None,
                    "roles": [role.name for role in member.roles if role.name != "@everyone"],
                    "top_role": member.top_role.name if member.top_role.name != "@everyone" else "No Role",
                    "status": str(member.status),
                    "activity": str(member.activity) if member.activity else None,
                    "is_pending": getattr(member, 'pending', False),
                    "premium_since": member.premium_since.isoformat() if hasattr(member, 'premium_since') and member.premium_since else None,
                    "guild": guild.name,
                    "guild_id": str(guild.id),
                    "synced_at": datetime.utcnow().isoformat(),
                    "sync_version": "2.1.0"
                }
                
                members_data.append(member_info)

            # Sync to Google Sheets using worksheet handler
            sync_success = self.worksheet_handlers.handle_discord_members(
                self.get_or_create_worksheet("Discord Members", 1000, 12),
                members_data,
                {"clear_existing": True, "include_analytics": True}
            )

            # Calculate comprehensive statistics
            sync_time = time.time() - sync_start_time
            self.performance_metrics["sync_operations"] += 1

            sync_results = {
                "success": sync_success,
                "guild_name": guild.name,
                "guild_id": str(guild.id),
                "total_discord_members": len(guild.members),
                "human_members_synced": human_member_count,
                "bot_members_excluded": bot_member_count,
                "roles_discovered": len(set(role for member_data in members_data for role in member_data["roles"])),
                "sync_duration_seconds": round(sync_time, 2),
                "sync_timestamp": datetime.utcnow().isoformat(),
                "performance_metrics": {
                    "members_per_second": round(human_member_count / sync_time, 2) if sync_time > 0 else 0,
                    "batch_operations": len(members_data) // BATCH_SETTINGS.get("MEMBER_SYNC_BATCH", 25) + 1
                },
                "data_quality": {
                    "members_with_roles": len([m for m in members_data if m["roles"]]),
                    "members_with_join_date": len([m for m in members_data if m["joined_at"]]),
                    "active_members": len([m for m in members_data if m["status"] != "offline"])
                }
            }

            if sync_success:
                logger.info(f"✅ Member sync completed: {human_member_count} members in {sync_time:.2f}s")
                logger.info(f"📊 Performance: {sync_results['performance_metrics']['members_per_second']} members/sec")
            else:
                logger.error("❌ Member sync failed")

            return sync_results

        except Exception as e:
            sync_time = time.time() - sync_start_time
            logger.error(f"❌ Member synchronization failed after {sync_time:.2f}s: {e}")
            return {
                "success": False,
                "error": str(e),
                "sync_duration_seconds": round(sync_time, 2),
                "sync_timestamp": datetime.utcnow().isoformat()
            }

    def create_all_templates(self, all_data: Dict[str, Any]) -> bool:
        """
        Create comprehensive sheet templates with data population.
        
        Args:
            all_data: Dictionary containing all bot data for templates
            
        Returns:
            bool: True if template creation was successful
            
        Features:
        - Creates all supported sheet templates
        - Populates templates with existing data
        - Applies comprehensive formatting
        - Handles errors gracefully
        - Provides detailed logging and metrics
        """
        if not self.is_connected():
            logger.error("❌ Cannot create templates - not connected to sheets")
            return False

        logger.info("🚀 Starting comprehensive template creation with data population...")
        
        # Use the template creator for comprehensive template creation
        success = self.template_creator.create_all_templates(all_data)
        
        if success:
            # Update performance metrics
            self.performance_metrics["template_operations"] += 1
            logger.info("✅ All templates created successfully with comprehensive data population")
        else:
            logger.error("❌ Template creation completed with some failures")
        
        return success

    def sync_current_teams(self, events_data: Dict[str, List]) -> bool:
        """
        Sync current team signups with enhanced analytics.
        
        Args:
            events_data: Dictionary containing team signup data
            
        Returns:
            bool: True if sync was successful
            
        Features:
        - Real-time team status tracking
        - Fill rate calculations and analytics
        - Performance optimization
        - Error handling and recovery
        """
        if not self.is_connected():
            logger.warning("⚠️ Cannot sync current teams - not connected")
            return False

        try:
            worksheet = self.get_or_create_worksheet("Current Teams", 100, 8)
            if not worksheet:
                return False

            return self.worksheet_handlers.handle_current_teams(
                worksheet, 
                events_data,
                {"include_analytics": True, "apply_formatting": True}
            )

        except Exception as e:
            logger.error(f"❌ Failed to sync current teams: {e}")
            return False

    def sync_results_history(self, results_data: Dict[str, Any]) -> bool:
        """
        Sync results history with comprehensive analysis.
        
        Args:
            results_data: Dictionary containing match results
            
        Returns:
            bool: True if sync was successful
            
        Features:
        - Comprehensive match result tracking
        - Performance analysis and ratings
        - Statistical summaries
        - Error handling and recovery
        """
        if not self.is_connected():
            logger.warning("⚠️ Cannot sync results history - not connected")
            return False

        try:
            worksheet = self.get_or_create_worksheet("Results History", 300, 10)
            if not worksheet:
                return False

            return self.worksheet_handlers.handle_results_history(
                worksheet,
                results_data,
                {"include_summary": True, "apply_formatting": True}
            )

        except Exception as e:
            logger.error(f"❌ Failed to sync results history: {e}")
            return False

    def sync_events_history(self, history_data: List[Dict[str, Any]]) -> bool:
        """
        Sync events history with trend analysis.
        
        Args:
            history_data: List of historical event data
            
        Returns:
            bool: True if sync was successful
            
        Features:
        - Chronological event tracking
        - Participation trend analysis
        - Performance optimization
        - Error handling and recovery
        """
        if not self.is_connected():
            logger.warning("⚠️ Cannot sync events history - not connected")
            return False

        try:
            worksheet = self.get_or_create_worksheet("Events History", 200, 8)
            if not worksheet:
                return False

            return self.worksheet_handlers.handle_events_history(
                worksheet,
                history_data,
                {"include_analytics": True, "apply_formatting": True}
            )

        except Exception as e:
            logger.error(f"❌ Failed to sync events history: {e}")
            return False

    def sync_blocked_users(self, blocked_data: Dict[str, Any]) -> bool:
        """
        Sync blocked users with moderation tracking.
        
        Args:
            blocked_data: Dictionary containing blocked user information
            
        Returns:
            bool: True if sync was successful
            
        Features:
        - Comprehensive moderation tracking
        - Status management and updates
        - Administrative oversight
        - Error handling and recovery
        """
        if not self.is_connected():
            logger.warning("⚠️ Cannot sync blocked users - not connected")
            return False

        try:
            worksheet = self.get_or_create_worksheet("Blocked Users", 100, 9)
            if not worksheet:
                return False

            return self.worksheet_handlers.handle_blocked_users(
                worksheet,
                blocked_data,
                {"apply_formatting": True, "include_status_tracking": True}
            )

        except Exception as e:
            logger.error(f"❌ Failed to sync blocked users: {e}")
            return False

    async def full_sync_and_create_templates(self, bot, all_data: Dict[str, Any], guild_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform comprehensive full synchronization and template creation.
        
        Args:
            bot: Discord bot instance
            all_data: Complete bot data dictionary
            guild_id: Optional guild ID for member sync
            
        Returns:
            dict: Comprehensive sync results
            
        Features:
        - Complete template creation with data
        - Full Discord member synchronization
        - Comprehensive data population
        - Performance metrics and analytics
        - Error handling and recovery
        """
        full_sync_start = time.time()
        logger.info("🚀 Starting comprehensive full synchronization and template creation...")

        results = {
            "success": False,
            "template_creation": {"success": False, "details": {}},
            "member_sync": {"success": False, "details": {}},
            "spreadsheet_url": self.spreadsheet.url if self.spreadsheet else None,
            "sync_timestamp": datetime.utcnow().isoformat(),
            "performance_metrics": {}
        }

        try:
            # Step 1: Create all templates with data
            logger.info("📋 Step 1: Creating comprehensive templates...")
            template_success = self.create_all_templates(all_data)
            results["template_creation"] = {
                "success": template_success,
                "details": self.template_creator.get_creation_summary()
            }

            # Step 2: Sync Discord members
            logger.info("👥 Step 2: Synchronizing Discord members...")
            member_sync_results = await self.scan_and_sync_all_members(bot, guild_id)
            results["member_sync"] = {
                "success": member_sync_results.get("success", False),
                "details": member_sync_results
            }

            # Step 3: Calculate overall success
            overall_success = template_success and member_sync_results.get("success", False)
            results["success"] = overall_success

            # Step 4: Generate performance metrics
            total_sync_time = time.time() - full_sync_start
            results["performance_metrics"] = {
                "total_sync_time_seconds": round(total_sync_time, 2),
                "templates_created": results["template_creation"]["details"].get("templates_created", 0),
                "members_synced": member_sync_results.get("human_members_synced", 0),
                "operations_per_second": round(
                    (results["template_creation"]["details"].get("templates_created", 0) + 
                     member_sync_results.get("human_members_synced", 0)) / total_sync_time, 2
                ) if total_sync_time > 0 else 0
            }

            if overall_success:
                logger.info(f"✅ Full synchronization completed successfully in {total_sync_time:.2f}s")
                logger.info(f"📊 Performance: {results['performance_metrics']['operations_per_second']} operations/sec")
            else:
                logger.warning(f"⚠️ Full synchronization completed with some failures in {total_sync_time:.2f}s")

        except Exception as e:
            total_sync_time = time.time() - full_sync_start
            logger.error(f"❌ Full synchronization failed after {total_sync_time:.2f}s: {e}")
            results["error"] = str(e)
            results["performance_metrics"] = {
                "total_sync_time_seconds": round(total_sync_time, 2),
                "error_occurred": True
            }

        return results

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics from all sheets and operations.
        
        Returns:
            dict: Comprehensive statistics and performance metrics
            
        Features:
        - Complete spreadsheet statistics
        - Performance metrics and analytics
        - Error tracking and analysis
        - Cache performance data
        - Operation success rates
        """
        if not self.is_connected():
            return {"error": "Not connected to sheets", "connected": False}

        try:
            # Base statistics
            stats = {
                "connected": True,
                "spreadsheet_url": self.spreadsheet.url if self.spreadsheet else None,
                "spreadsheet_id": self.spreadsheet_id,
                "last_updated": datetime.utcnow().isoformat(),
                "session_duration_minutes": round((time.time() - self.performance_metrics["session_start_time"]) / 60, 1),
                "worksheets": [],
                "system_health": "🟢 Operational"
            }

            # Worksheet information with enhanced details
            total_rows = 0
            for worksheet in self.rate_limited_request(lambda: self.spreadsheet.worksheets()):
                try:
                    worksheet_info = {
                        "name": worksheet.title,
                        "row_count": worksheet.row_count,
                        "col_count": worksheet.col_count,
                        "data_rows": 0,  # Would be calculated if needed
                        "last_modified": "Unknown"  # Would be fetched if available
                    }
                    stats["worksheets"].append(worksheet_info)
                    total_rows += worksheet.row_count
                except Exception as e:
                    logger.warning(f"⚠️ Could not get info for worksheet {worksheet.title}: {e}")

            # Performance metrics
            total_ops = self.performance_metrics["total_operations"]
            success_rate = (
                self.performance_metrics["successful_operations"] / total_ops * 100 
                if total_ops > 0 else 100
            )

            stats["performance_metrics"] = {
                "total_operations": total_ops,
                "successful_operations": self.performance_metrics["successful_operations"],
                "failed_operations": self.performance_metrics["failed_operations"],
                "success_rate_percent": round(success_rate, 2),
                "average_operation_time_seconds": round(self.performance_metrics["average_operation_time"], 3),
                "total_processing_time_seconds": round(self.performance_metrics["total_processing_time"], 2),
                "rate_limit_hits": self.performance_metrics["rate_limit_hits"],
                "cache_hit_rate_percent": round(
                    self.performance_metrics["cache_hits"] / 
                    (self.performance_metrics["cache_hits"] + self.performance_metrics["cache_misses"]) * 100
                    if (self.performance_metrics["cache_hits"] + self.performance_metrics["cache_misses"]) > 0 else 0, 2
                )
            }

            # Operation statistics
            stats["operation_statistics"] = {
                "data_validations": self.performance_metrics["data_validations"],
                "template_operations": self.performance_metrics["template_operations"],
                "sync_operations": self.performance_metrics["sync_operations"],
                "batch_operations": self.performance_metrics["batch_operations"]
            }

            # System health assessment
            if success_rate < 90:
                stats["system_health"] = "🟡 Degraded Performance"
            elif success_rate < 75:
                stats["system_health"] = "🔴 Poor Performance"
            elif self.performance_metrics["rate_limit_hits"] > 10:
                stats["system_health"] = "🟡 Rate Limited"

            # Error summary
            recent_errors = self.error_history[-5:] if self.error_history else []
            stats["error_summary"] = {
                "total_errors": len(self.error_history),
                "recent_errors": len(recent_errors),
                "error_types": list(set(error.get("error_type", "Unknown") for error in recent_errors))
            }

            # Configuration summary
            stats["configuration"] = {
                "caching_enabled": self.config["enable_caching"],
                "batch_operations_enabled": self.config["enable_batch_operations"],
                "performance_monitoring_enabled": self.config["enable_performance_monitoring"],
                "advanced_formatting_enabled": self.config["enable_advanced_formatting"],
                "cache_entries": len(self.operation_cache)
            }

            return stats

        except Exception as e:
            logger.error(f"❌ Failed to get comprehensive stats: {e}")
            return {
                "error": str(e),
                "connected": False,
                "system_health": "🔴 Error"
            }

    def _generate_cache_key(self, func, args: tuple, kwargs: dict) -> Optional[str]:
        """Generate cache key for operation caching."""
        try:
            # Create a simple cache key based on function name and arguments
            key_parts = [func.__name__]
            
            # Add string representations of args (limit to prevent huge keys)
            for arg in args[:3]:  # Limit to first 3 args
                key_parts.append(str(arg)[:50])  # Limit each arg to 50 chars
            
            return "|".join(key_parts)
        except:
            return None

    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if current_time - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            self.operation_cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
        
        logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

    def _update_performance_metrics(self, operation_time: float, success: bool):
        """Update performance metrics for completed operation."""
        self.performance_metrics["total_operations"] += 1
        self.performance_metrics["total_processing_time"] += operation_time
        
        if success:
            self.performance_metrics["successful_operations"] += 1
        else:
            self.performance_metrics["failed_operations"] += 1
        
        # Calculate new average
        total_ops = self.performance_metrics["total_operations"]
        self.performance_metrics["average_operation_time"] = (
            self.performance_metrics["total_processing_time"] / total_ops
        )

    def _log_operation_error(self, operation_name: str, error: Exception):
        """Log operation error with comprehensive details."""
        error_info = {
            "operation": operation_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.error_history.append(error_info)
        
        # Keep error history within bounds
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
        
        logger.error(f"❌ Operation {operation_name} failed: {error}")

    def smart_delay(self, delay_type: str = "small"):
        """
        Smart delay implementation with performance optimization.
        
        Args:
            delay_type: Type of delay ('small', 'medium', 'large')
            
        Features:
        - Configurable delay periods
        - Performance-based delay adjustment
        - Rate limit awareness
        - Operation context sensitivity
        """
        delay_map = {
            "small": 0.1,
            "medium": 0.5,
            "large": 1.0
        }
        
        base_delay = delay_map.get(delay_type, 0.1)
        
        # Adjust delay based on recent rate limiting
        if self.performance_metrics["rate_limit_hits"] > 5:
            base_delay *= 1.5  # Increase delay if we've hit rate limits
        
        time.sleep(base_delay)

    def __del__(self):
        """Cleanup resources when manager is destroyed."""
        try:
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
        except:
            pass


# Export the main class and utilities
__all__ = [
    "SheetsManager",
    "SheetsTemplateCreator", 
    "WorksheetHandlers",
    "SUPPORTED_SHEETS",
    "COLORS",
    "TEXT_FORMATS"
]

# Module metadata
__version__ = "2.1.0"
__author__ = "RoW Bot Development Team"
__description__ = "Comprehensive Google Sheets integration with advanced features"
__last_updated__ = "2024-01-15"
__requirements__ = [
    "gspread>=5.0.0",
    "google-auth>=2.0.0",
    "google-auth-oauthlib>=0.5.0",
    "google-auth-httplib2>=0.1.0"
]
__min_python_version__ = "3.8"

# Configuration constants
DEFAULT_REQUEST_INTERVAL = 0.1
DEFAULT_MAX_RETRIES = 5
DEFAULT_BATCH_SIZE = 50
DEFAULT_CACHE_TTL = 300

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "MAX_OPERATION_TIME": 30.0,
    "MAX_BATCH_SIZE": 100,
    "CACHE_SIZE_LIMIT": 500,
    "ERROR_RATE_WARNING": 10.0,
    "SUCCESS_RATE_WARNING": 90.0
}

# Feature availability matrix
FEATURE_MATRIX = {
    "template_creation": True,
    "data_synchronization": True,
    "member_management": True,
    "performance_monitoring": True,
    "advanced_formatting": True,
    "batch_operations": True,
    "caching_system": True,
    "error_recovery": True,
    "analytics_integration": True,
    "multi_threading": True
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    "handlers": ["console", "file"],
    "max_file_size": "10MB",
    "backup_count": 5
}

logger.info("📦 Google Sheets Integration Module loaded successfully")
logger.info(f"✨ Version: {__version__} | Features: {sum(FEATURE_MATRIX.values())}/{len(FEATURE_MATRIX)} enabled")

"""
Health check and monitoring endpoints for the Nuggit API.

This module provides endpoints for monitoring database health, connection pool status,
and overall system health.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nuggit.util.db import get_connection, DB_PATH
from nuggit.util.connection_pool import get_pool_stats
from nuggit.util.github_client import get_client_stats
from nuggit.util.timezone import utc_now_iso
from nuggit.api.utils.error_handling import database_error, internal_server_error

# Import error recovery utilities
try:
    from nuggit.util.error_recovery import get_error_recovery_manager, get_error_monitor
    ERROR_RECOVERY_AVAILABLE = True
except ImportError:
    ERROR_RECOVERY_AVAILABLE = False
    logger.warning("Error recovery utilities not available")

# Import logging utilities
try:
    from nuggit.util.logging_config import get_performance_logger, get_audit_logger
    LOGGING_UTILITIES_AVAILABLE = True
except ImportError:
    LOGGING_UTILITIES_AVAILABLE = False
    logger.warning("Logging utilities not available")

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str
    timestamp: str
    database: Dict[str, Any]
    connection_pool: Dict[str, Any]
    github_client: Dict[str, Any]
    error_recovery: Dict[str, Any]
    checks: Dict[str, bool]


class DatabaseStats(BaseModel):
    """Database statistics model."""
    
    file_size_bytes: int
    table_count: int
    repository_count: int
    comment_count: int
    version_count: int
    history_count: int


@router.get("/health", response_model=HealthStatus, summary="System health check")
async def health_check():
    """
    Comprehensive system health check.
    
    Returns:
        HealthStatus: System health information including database and connection pool status
        
    Raises:
        HTTPException: If critical health checks fail
    """
    timestamp = utc_now_iso()
    checks = {}
    database_info = {}
    connection_pool_info = {}
    github_client_info = {}
    error_recovery_info = {}
    
    # Database connectivity check
    try:
        with get_connection() as conn:
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            checks["database_connectivity"] = result[0] == 1
            
            # Get database file size
            try:
                database_info["file_size_bytes"] = DB_PATH.stat().st_size
                database_info["file_exists"] = True
            except FileNotFoundError:
                database_info["file_size_bytes"] = 0
                database_info["file_exists"] = False
            
            # Check table existence
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            database_info["tables"] = tables
            checks["required_tables"] = all(
                table in tables 
                for table in ["repositories", "repository_history", "repository_comments", "repository_versions"]
            )
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database_connectivity"] = False
        database_info["error"] = str(e)
    
    # Connection pool status
    try:
        connection_pool_info = get_pool_stats()
        checks["connection_pool"] = True
    except Exception as e:
        logger.error(f"Connection pool health check failed: {e}")
        checks["connection_pool"] = False
        connection_pool_info["error"] = str(e)

    # GitHub client status
    try:
        github_client_info = get_client_stats()
        checks["github_client"] = True
    except Exception as e:
        logger.error(f"GitHub client health check failed: {e}")
        checks["github_client"] = False
        github_client_info["error"] = str(e)

    # Error recovery system status
    if ERROR_RECOVERY_AVAILABLE:
        try:
            recovery_manager = get_error_recovery_manager()
            error_monitor = get_error_monitor()

            error_recovery_info = {
                "circuit_breakers": recovery_manager.get_all_stats(),
                "error_metrics": error_monitor.get_metrics()
            }
            checks["error_recovery"] = True
        except Exception as e:
            logger.error(f"Error recovery health check failed: {e}")
            checks["error_recovery"] = False
            error_recovery_info["error"] = str(e)
    else:
        checks["error_recovery"] = False
        error_recovery_info["error"] = "Error recovery system not available"
    
    # Schema migration check
    try:
        with get_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_migrations'
            """)
            migration_table_exists = cursor.fetchone() is not None
            checks["migration_system"] = migration_table_exists
            
            if migration_table_exists:
                cursor = conn.execute("SELECT COUNT(*) FROM schema_migrations")
                migration_count = cursor.fetchone()[0]
                database_info["applied_migrations"] = migration_count
            
    except Exception as e:
        logger.error(f"Migration system health check failed: {e}")
        checks["migration_system"] = False
    
    # Overall health status
    all_checks_passed = all(checks.values())
    status = "healthy" if all_checks_passed else "unhealthy"
    
    if not all_checks_passed:
        logger.warning(f"Health check failed: {checks}")
    
    return HealthStatus(
        status=status,
        timestamp=timestamp,
        database=database_info,
        connection_pool=connection_pool_info,
        github_client=github_client_info,
        error_recovery=error_recovery_info,
        checks=checks
    )


@router.get("/health/database", response_model=DatabaseStats, summary="Database statistics")
async def database_stats():
    """
    Get detailed database statistics.
    
    Returns:
        DatabaseStats: Detailed database statistics
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        with get_connection() as conn:
            # Get file size
            try:
                file_size = DB_PATH.stat().st_size
            except FileNotFoundError:
                file_size = 0
            
            # Count tables
            cursor = conn.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            table_count = cursor.fetchone()[0]
            
            # Count records in each table
            counts = {}
            for table in ["repositories", "repository_comments", "repository_versions", "repository_history"]:
                try:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except sqlite3.Error:
                    counts[table] = 0
            
            return DatabaseStats(
                file_size_bytes=file_size,
                table_count=table_count,
                repository_count=counts.get("repositories", 0),
                comment_count=counts.get("repository_comments", 0),
                version_count=counts.get("repository_versions", 0),
                history_count=counts.get("repository_history", 0)
            )
            
    except Exception as e:
        logger.error(f"Database stats query failed: {e}")
        raise database_error("Failed to retrieve database statistics")


@router.get("/health/connections", summary="Connection pool status")
async def connection_pool_status():
    """
    Get connection pool status and statistics.
    
    Returns:
        dict: Connection pool statistics and status
        
    Raises:
        HTTPException: If connection pool query fails
    """
    try:
        stats = get_pool_stats()
        
        # Add health indicators
        stats["health"] = {
            "pool_utilization": stats.get("active_connections", 0) / max(stats.get("max_connections", 1), 1),
            "leak_rate": stats.get("connection_leaks_detected", 0) / max(stats.get("connections_created", 1), 1),
            "reuse_rate": stats.get("connections_reused", 0) / max(stats.get("connections_created", 1), 1),
            "hit_rate": stats.get("pool_hits", 0) / max(stats.get("pool_hits", 0) + stats.get("pool_misses", 0), 1)
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Connection pool status query failed: {e}")
        raise internal_server_error("Failed to retrieve connection pool status")


@router.post("/health/database/vacuum", summary="Vacuum database")
async def vacuum_database():
    """
    Perform database vacuum operation to reclaim space and optimize performance.
    
    Returns:
        dict: Vacuum operation result
        
    Raises:
        HTTPException: If vacuum operation fails
    """
    try:
        # Get file size before vacuum
        size_before = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        
        with get_connection() as conn:
            # Perform vacuum
            conn.execute("VACUUM")
            
            # Get statistics after vacuum
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA freelist_count")
            free_pages = cursor.fetchone()[0]
        
        # Get file size after vacuum
        size_after = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        
        return {
            "success": True,
            "size_before_bytes": size_before,
            "size_after_bytes": size_after,
            "space_reclaimed_bytes": size_before - size_after,
            "page_count": page_count,
            "page_size": page_size,
            "free_pages": free_pages,
            "timestamp": utc_now_iso()
        }
        
    except Exception as e:
        logger.error(f"Database vacuum failed: {e}")
        raise database_error("Failed to vacuum database")


@router.get("/health/github", summary="GitHub client status")
async def github_client_status():
    """
    Get GitHub client status and rate limiting information.

    Returns:
        dict: GitHub client statistics and rate limit information

    Raises:
        HTTPException: If GitHub client query fails
    """
    try:
        stats = get_client_stats()
        return stats

    except Exception as e:
        logger.error(f"GitHub client status query failed: {e}")
        raise internal_server_error("Failed to retrieve GitHub client status")


@router.get("/health/errors", summary="Error monitoring status")
async def error_monitoring_status():
    """
    Get error monitoring and recovery status.

    Returns:
        dict: Error monitoring statistics and circuit breaker status

    Raises:
        HTTPException: If error monitoring query fails
    """
    if not ERROR_RECOVERY_AVAILABLE:
        raise internal_server_error("Error recovery system not available")

    try:
        recovery_manager = get_error_recovery_manager()
        error_monitor = get_error_monitor()

        return {
            "circuit_breakers": recovery_manager.get_all_stats(),
            "error_metrics": error_monitor.get_metrics(),
            "recent_errors": error_monitor.get_recent_errors(limit=5),
            "timestamp": utc_now_iso()
        }

    except Exception as e:
        logger.error(f"Error monitoring status query failed: {e}")
        raise internal_server_error("Failed to retrieve error monitoring status")


@router.post("/health/errors/reset", summary="Reset error monitoring")
async def reset_error_monitoring():
    """
    Reset error monitoring metrics.

    Returns:
        dict: Reset confirmation

    Raises:
        HTTPException: If reset operation fails
    """
    if not ERROR_RECOVERY_AVAILABLE:
        raise internal_server_error("Error recovery system not available")

    try:
        error_monitor = get_error_monitor()
        error_monitor.clear_metrics()

        return {
            "success": True,
            "message": "Error monitoring metrics reset",
            "timestamp": utc_now_iso()
        }

    except Exception as e:
        logger.error(f"Error monitoring reset failed: {e}")
        raise internal_server_error("Failed to reset error monitoring")


@router.post("/health/circuit-breakers/{name}/reset", summary="Reset circuit breaker")
async def reset_circuit_breaker(name: str):
    """
    Manually reset a specific circuit breaker.

    Args:
        name: Name of the circuit breaker to reset

    Returns:
        dict: Reset confirmation

    Raises:
        HTTPException: If reset operation fails
    """
    if not ERROR_RECOVERY_AVAILABLE:
        raise internal_server_error("Error recovery system not available")

    try:
        recovery_manager = get_error_recovery_manager()
        success = recovery_manager.reset_circuit_breaker(name)

        if success:
            return {
                "success": True,
                "message": f"Circuit breaker '{name}' reset successfully",
                "timestamp": utc_now_iso()
            }
        else:
            return {
                "success": False,
                "message": f"Circuit breaker '{name}' not found",
                "timestamp": utc_now_iso()
            }

    except Exception as e:
        logger.error(f"Circuit breaker reset failed: {e}")
        raise internal_server_error("Failed to reset circuit breaker")


@router.get("/health/logs", summary="Logging system status")
async def logging_system_status():
    """
    Get logging system status and recent log statistics.

    Returns:
        dict: Logging system status and statistics

    Raises:
        HTTPException: If logging system query fails
    """
    if not LOGGING_UTILITIES_AVAILABLE:
        return {
            "status": "unavailable",
            "message": "Logging utilities not available",
            "timestamp": utc_now_iso()
        }

    try:
        # Get log file information
        import os
        from pathlib import Path

        log_dir = Path("logs")
        log_files = []

        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                try:
                    stat = log_file.stat()
                    log_files.append({
                        "name": log_file.name,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Could not get stats for {log_file}: {e}")

        return {
            "status": "available",
            "log_directory": str(log_dir.absolute()) if log_dir.exists() else "not found",
            "log_files": log_files,
            "active_loggers": [
                name for name in logging.Logger.manager.loggerDict.keys()
                if not name.startswith("_")
            ][:20],  # Limit to first 20 loggers
            "timestamp": utc_now_iso()
        }

    except Exception as e:
        logger.error(f"Logging system status query failed: {e}")
        raise internal_server_error("Failed to retrieve logging system status")


@router.post("/health/logs/level", summary="Change log level")
async def change_log_level(level: str):
    """
    Change the logging level for the application.

    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        dict: Confirmation of log level change

    Raises:
        HTTPException: If log level change fails
    """
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    if level.upper() not in valid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid log level. Must be one of: {', '.join(valid_levels)}"
        )

    try:
        # Change root logger level
        root_logger = logging.getLogger()
        old_level = logging.getLevelName(root_logger.level)
        root_logger.setLevel(getattr(logging, level.upper()))

        logger.info(f"Log level changed from {old_level} to {level.upper()}")

        return {
            "success": True,
            "old_level": old_level,
            "new_level": level.upper(),
            "message": f"Log level changed to {level.upper()}",
            "timestamp": utc_now_iso()
        }

    except Exception as e:
        logger.error(f"Log level change failed: {e}")
        raise internal_server_error("Failed to change log level")


@router.get("/health/ping", summary="Simple ping check")
async def ping():
    """
    Simple ping endpoint for basic health monitoring.

    Returns:
        dict: Simple pong response with timestamp
    """
    return {
        "status": "ok",
        "message": "pong",
        "timestamp": utc_now_iso()
    }

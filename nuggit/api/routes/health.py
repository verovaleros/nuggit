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
from nuggit.api.utils.error_handling import database_error, internal_server_error

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str
    timestamp: str
    database: Dict[str, Any]
    connection_pool: Dict[str, Any]
    github_client: Dict[str, Any]
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
    timestamp = datetime.utcnow().isoformat() + "Z"
    checks = {}
    database_info = {}
    connection_pool_info = {}
    github_client_info = {}
    
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
            "timestamp": datetime.utcnow().isoformat() + "Z"
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
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

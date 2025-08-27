"""
Enhanced database connection management with connection pooling and leak prevention.

This module provides improved database connection handling to prevent connection leaks,
implement connection pooling, and ensure proper cleanup in error scenarios.
"""

import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List
from queue import Queue, Empty, Full
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# SQLite configuration constants
SQLITE_CACHE_SIZE = -64 * 1024  # 64MB cache (negative value means KB)
SQLITE_MMAP_SIZE = 256 * 1024 * 1024  # 256MB memory-mapped I/O


@dataclass
class ConnectionInfo:
    """Information about a database connection."""
    connection: sqlite3.Connection
    created_at: datetime
    last_used: datetime
    thread_id: int
    in_use: bool = False


class ConnectionPool:
    """Thread-safe SQLite connection pool with leak detection.

    This pool manages SQLite connections with check_same_thread=False, which disables
    SQLite's built-in thread safety checks. The pool ensures thread safety by:
    1. Using locks to synchronize access to the connection pool
    2. Tracking which thread is using each connection
    3. Ensuring connections are properly returned to the pool
    4. Preventing connection sharing between threads

    WARNING: Each connection must only be used by one thread at a time.
    The pool enforces this constraint through careful connection management.
    """
    
    def __init__(
        self,
        db_path: Path,
        max_connections: int = 10,
        max_idle_time: int = 300,  # 5 minutes
        connection_timeout: int = 30
    ):
        self.db_path = db_path
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.connection_timeout = connection_timeout
        
        self._pool: Queue[ConnectionInfo] = Queue(maxsize=max_connections)
        self._active_connections: Dict[int, ConnectionInfo] = {}
        self._lock = threading.RLock()
        self._total_connections = 0
        self._connection_counter = 0
        
        # Statistics
        self._stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_reused': 0,
            'connection_leaks_detected': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_idle_connections, daemon=True)
        self._cleanup_thread.start()
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with optimal settings."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.connection_timeout,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False  # Allow connection sharing between threads
            # WARNING: Setting check_same_thread=False disables SQLite's thread safety.
            # The connection pool must ensure that each connection is only used by one
            # thread at a time.
        )
        
        # Configure connection for optimal performance and safety
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
        conn.execute("PRAGMA synchronous = NORMAL")  # Good balance of safety and performance
        conn.execute(f"PRAGMA cache_size = {SQLITE_CACHE_SIZE}")  # 64MB cache
        conn.execute("PRAGMA temp_store = MEMORY")  # Store temp tables in memory
        conn.execute(f"PRAGMA mmap_size = {SQLITE_MMAP_SIZE}")  # 256MB memory-mapped I/O
        
        self._stats['connections_created'] += 1
        logger.debug(f"Created new database connection (total: {self._total_connections + 1})")
        
        return conn
    
    def _get_connection_from_pool(self) -> Optional[ConnectionInfo]:
        """Get an available connection from the pool."""
        try:
            while True:
                try:
                    conn_info = self._pool.get_nowait()
                    
                    # Check if connection is still valid
                    try:
                        conn_info.connection.execute("SELECT 1")
                        conn_info.last_used = datetime.now()
                        self._stats['pool_hits'] += 1
                        self._stats['connections_reused'] += 1
                        return conn_info
                    except sqlite3.Error:
                        # Connection is invalid, close it and try next
                        self._close_connection(conn_info)
                        continue
                        
                except Empty:
                    break
                    
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
        
        self._stats['pool_misses'] += 1
        return None
    
    def _close_connection(self, conn_info: ConnectionInfo):
        """Safely close a connection."""
        try:
            conn_info.connection.close()
            self._stats['connections_closed'] += 1
            logger.debug(f"Closed database connection (thread: {conn_info.thread_id})")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
        finally:
            with self._lock:
                self._total_connections -= 1
    
    def get_connection(self) -> ConnectionInfo:
        """Get a connection from the pool or create a new one."""
        thread_id = threading.get_ident()
        
        with self._lock:
            # Check if this thread already has an active connection
            if thread_id in self._active_connections:
                conn_info = self._active_connections[thread_id]
                if not conn_info.in_use:
                    conn_info.in_use = True
                    conn_info.last_used = datetime.now()
                    return conn_info
                else:
                    logger.warning(f"Thread {thread_id} requesting connection while one is already in use")
            
            # Try to get connection from pool
            conn_info = self._get_connection_from_pool()
            
            if conn_info is None:
                # Create new connection if under limit
                if self._total_connections < self.max_connections:
                    conn = self._create_connection()
                    self._connection_counter += 1
                    conn_info = ConnectionInfo(
                        connection=conn,
                        created_at=datetime.now(),
                        last_used=datetime.now(),
                        thread_id=thread_id,
                        in_use=True
                    )
                    self._total_connections += 1
                else:
                    raise sqlite3.Error("Connection pool exhausted")
            
            conn_info.thread_id = thread_id
            conn_info.in_use = True
            self._active_connections[thread_id] = conn_info
            
            return conn_info
    
    def return_connection(self, conn_info: ConnectionInfo, commit: bool = True):
        """Return a connection to the pool."""
        thread_id = threading.get_ident()
        
        try:
            if commit:
                conn_info.connection.commit()
            else:
                conn_info.connection.rollback()
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
            # Close the connection if there's an error
            self._close_connection(conn_info)
            with self._lock:
                self._active_connections.pop(thread_id, None)
            return
        
        with self._lock:
            conn_info.in_use = False
            conn_info.last_used = datetime.now()
            
            # Remove from active connections
            self._active_connections.pop(thread_id, None)
            
            # Return to pool if there's space
            try:
                self._pool.put_nowait(conn_info)
            except Full:
                # Pool is full, close the connection
                self._close_connection(conn_info)
    
    def _cleanup_idle_connections(self):
        """Background thread to clean up idle connections."""
        while True:
            try:
                time.sleep(60)  # Check every minute
                
                current_time = datetime.now()
                idle_threshold = current_time - timedelta(seconds=self.max_idle_time)
                
                # Clean up idle connections in pool
                connections_to_close = []
                
                while True:
                    try:
                        conn_info = self._pool.get_nowait()
                        if conn_info.last_used < idle_threshold:
                            connections_to_close.append(conn_info)
                        else:
                            # Put back if not idle
                            self._pool.put_nowait(conn_info)
                            break
                    except Empty:
                        break
                
                # Close idle connections
                for conn_info in connections_to_close:
                    self._close_connection(conn_info)
                
                # Check for leaked connections
                with self._lock:
                    leaked_connections = []
                    for thread_id, conn_info in self._active_connections.items():
                        if conn_info.in_use and conn_info.last_used < idle_threshold:
                            leaked_connections.append((thread_id, conn_info))
                    
                    for thread_id, conn_info in leaked_connections:
                        logger.warning(f"Detected leaked connection from thread {thread_id}")
                        self._stats['connection_leaks_detected'] += 1
                        self._close_connection(conn_info)
                        self._active_connections.pop(thread_id, None)
                
            except Exception as e:
                logger.error(f"Error in connection cleanup thread: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._lock:
            return {
                **self._stats,
                'total_connections': self._total_connections,
                'active_connections': len(self._active_connections),
                'pool_size': self._pool.qsize(),
                'max_connections': self.max_connections
            }
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            # Close active connections
            for conn_info in self._active_connections.values():
                self._close_connection(conn_info)
            self._active_connections.clear()
            
            # Close pooled connections
            while True:
                try:
                    conn_info = self._pool.get_nowait()
                    self._close_connection(conn_info)
                except Empty:
                    break


# Global connection pool instance
_connection_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool(db_path: Path) -> ConnectionPool:
    """Get or create the global connection pool."""
    global _connection_pool
    
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                _connection_pool = ConnectionPool(db_path)
    
    return _connection_pool


@contextmanager
def get_pooled_connection(db_path: Path):
    """
    Context manager for getting a pooled database connection.
    
    This provides better connection management than the simple context manager,
    with connection pooling and leak detection.
    
    Args:
        db_path: Path to the SQLite database file
        
    Yields:
        sqlite3.Connection: A database connection from the pool
        
    Raises:
        sqlite3.Error: If connection cannot be obtained or database operation fails
    """
    pool = get_connection_pool(db_path)
    conn_info = None
    
    try:
        conn_info = pool.get_connection()
        yield conn_info.connection
        pool.return_connection(conn_info, commit=True)
    except Exception as e:
        if conn_info:
            pool.return_connection(conn_info, commit=False)
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        # Ensure connection is returned even if there's an exception
        if conn_info and conn_info.in_use:
            try:
                pool.return_connection(conn_info, commit=False)
            except Exception as cleanup_error:
                logger.error(f"Error during connection cleanup: {cleanup_error}")


def get_pool_stats() -> Dict[str, Any]:
    """Get connection pool statistics."""
    global _connection_pool
    
    if _connection_pool is None:
        return {"error": "Connection pool not initialized"}
    
    return _connection_pool.get_stats()


def close_connection_pool():
    """Close the global connection pool."""
    global _connection_pool
    
    if _connection_pool is not None:
        with _pool_lock:
            if _connection_pool is not None:
                _connection_pool.close_all()
                _connection_pool = None

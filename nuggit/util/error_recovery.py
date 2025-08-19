"""
Error recovery and resilience utilities for the Nuggit application.

This module provides circuit breaker patterns, retry mechanisms, and error recovery
strategies to improve application resilience and user experience.
"""

import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, TypeVar, Union, List
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import threading

from nuggit.util.timezone import now_utc, utc_now_iso

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds to wait before trying again
    success_threshold: int = 3  # Successes needed to close circuit
    timeout: float = 30.0  # Operation timeout in seconds


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation for handling service failures gracefully.
    
    Prevents cascading failures by temporarily stopping calls to a failing service
    and allowing it time to recover.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.stats = CircuitBreakerStats()
        self._lock = threading.RLock()
        self._last_failure_time: Optional[datetime] = None
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self.stats.current_state != CircuitState.OPEN:
            return False
        
        if not self._last_failure_time:
            return True
        
        time_since_failure = now_utc() - self._last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    def _record_success(self):
        """Record a successful operation."""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.consecutive_failures = 0
            self.stats.consecutive_successes += 1
            self.stats.last_success_time = now_utc()
            
            # If we're in half-open state and have enough successes, close the circuit
            if (self.stats.current_state == CircuitState.HALF_OPEN and 
                self.stats.consecutive_successes >= self.config.success_threshold):
                self.stats.current_state = CircuitState.CLOSED
                logger.info(f"Circuit breaker '{self.name}' closed after recovery")
    
    def _record_failure(self, error: Exception):
        """Record a failed operation."""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.consecutive_successes = 0
            self.stats.consecutive_failures += 1
            self.stats.last_failure_time = now_utc()
            self._last_failure_time = self.stats.last_failure_time
            
            # Open circuit if we've hit the failure threshold
            if (self.stats.current_state == CircuitState.CLOSED and 
                self.stats.consecutive_failures >= self.config.failure_threshold):
                self.stats.current_state = CircuitState.OPEN
                self.stats.circuit_opened_count += 1
                logger.warning(f"Circuit breaker '{self.name}' opened after {self.stats.consecutive_failures} failures")
            
            # If we're in half-open and fail, go back to open
            elif self.stats.current_state == CircuitState.HALF_OPEN:
                self.stats.current_state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' reopened during recovery attempt")
    
    def call(self, func: Callable[[], T]) -> T:
        """Execute a function with circuit breaker protection."""
        with self._lock:
            # Check if we should attempt reset
            if self._should_attempt_reset():
                self.stats.current_state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' attempting recovery")
            
            # Fail fast if circuit is open
            if self.stats.current_state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Last failure: {self.stats.last_failure_time}"
                )
        
        # Execute the function
        try:
            result = func()
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise
    
    async def call_async(self, func: Callable[[], T]) -> T:
        """Execute an async function with circuit breaker protection."""
        with self._lock:
            # Check if we should attempt reset
            if self._should_attempt_reset():
                self.stats.current_state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' attempting recovery")
            
            # Fail fast if circuit is open
            if self.stats.current_state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Last failure: {self.stats.last_failure_time}"
                )
        
        # Execute the async function
        try:
            result = await func()
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            success_rate = (
                self.stats.successful_requests / max(self.stats.total_requests, 1)
            ) * 100
            
            return {
                "name": self.name,
                "state": self.stats.current_state.value,
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "success_rate": round(success_rate, 2),
                "consecutive_failures": self.stats.consecutive_failures,
                "consecutive_successes": self.stats.consecutive_successes,
                "circuit_opened_count": self.stats.circuit_opened_count,
                "last_failure_time": utc_now_iso() if self.stats.last_failure_time else None,
                "last_success_time": utc_now_iso() if self.stats.last_success_time else None,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout
                }
            }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class ErrorRecoveryManager:
    """Manages circuit breakers and error recovery strategies."""
    
    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
    
    def get_circuit_breaker(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        with self._lock:
            if name not in self._circuit_breakers:
                if config is None:
                    config = CircuitBreakerConfig()
                self._circuit_breakers[name] = CircuitBreaker(name, config)
            return self._circuit_breakers[name]
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {
                name: breaker.get_stats() 
                for name, breaker in self._circuit_breakers.items()
            }
    
    def reset_circuit_breaker(self, name: str) -> bool:
        """Manually reset a circuit breaker."""
        with self._lock:
            if name in self._circuit_breakers:
                breaker = self._circuit_breakers[name]
                breaker.stats.current_state = CircuitState.CLOSED
                breaker.stats.consecutive_failures = 0
                breaker.stats.consecutive_successes = 0
                logger.info(f"Circuit breaker '{name}' manually reset")
                return True
            return False


# Global error recovery manager
_error_recovery_manager = ErrorRecoveryManager()


def get_error_recovery_manager() -> ErrorRecoveryManager:
    """Get the global error recovery manager."""
    return _error_recovery_manager


def circuit_breaker(
    name: str, 
    config: Optional[CircuitBreakerConfig] = None
):
    """
    Decorator to add circuit breaker protection to a function.
    
    Args:
        name: Name of the circuit breaker
        config: Circuit breaker configuration
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_error_recovery_manager()
            breaker = manager.get_circuit_breaker(name, config)
            
            return breaker.call(lambda: func(*args, **kwargs))
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = get_error_recovery_manager()
            breaker = manager.get_circuit_breaker(name, config)
            
            return await breaker.call_async(lambda: func(*args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


def with_fallback(fallback_func: Callable[[], T]):
    """
    Decorator to provide fallback functionality when primary function fails.
    
    Args:
        fallback_func: Function to call if primary function fails
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Primary function {func.__name__} failed: {e}. Using fallback.")
                try:
                    return fallback_func()
                except Exception as fallback_error:
                    logger.error(f"Fallback function also failed: {fallback_error}")
                    raise e  # Raise original error
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Primary function {func.__name__} failed: {e}. Using fallback.")
                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func()
                    else:
                        return fallback_func()
                except Exception as fallback_error:
                    logger.error(f"Fallback function also failed: {fallback_error}")
                    raise e  # Raise original error
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


@dataclass
class ErrorMetrics:
    """Error metrics for monitoring."""
    error_count: int = 0
    error_rate: float = 0.0
    last_error_time: Optional[datetime] = None
    error_types: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[Dict[str, Any]] = field(default_factory=list)


class ErrorMonitor:
    """Monitor and track application errors for alerting and analysis."""

    def __init__(self, max_recent_errors: int = 100):
        self.max_recent_errors = max_recent_errors
        self.metrics = ErrorMetrics()
        self._lock = threading.RLock()
        self._start_time = now_utc()

    def record_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """Record an error occurrence."""
        with self._lock:
            self.metrics.error_count += 1
            self.metrics.last_error_time = now_utc()

            # Track error types
            error_type = type(error).__name__
            self.metrics.error_types[error_type] = self.metrics.error_types.get(error_type, 0) + 1

            # Calculate error rate (errors per minute)
            time_elapsed = (now_utc() - self._start_time).total_seconds() / 60
            self.metrics.error_rate = self.metrics.error_count / max(time_elapsed, 1)

            # Store recent error details
            error_detail = {
                "timestamp": utc_now_iso(),
                "type": error_type,
                "message": str(error),
                "context": context or {}
            }

            self.metrics.recent_errors.append(error_detail)

            # Keep only recent errors
            if len(self.metrics.recent_errors) > self.max_recent_errors:
                self.metrics.recent_errors = self.metrics.recent_errors[-self.max_recent_errors:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get current error metrics."""
        with self._lock:
            return {
                "error_count": self.metrics.error_count,
                "error_rate": round(self.metrics.error_rate, 2),
                "last_error_time": utc_now_iso() if self.metrics.last_error_time else None,
                "error_types": dict(self.metrics.error_types),
                "recent_errors_count": len(self.metrics.recent_errors),
                "monitoring_duration_minutes": round(
                    (now_utc() - self._start_time).total_seconds() / 60, 2
                )
            }

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors for debugging."""
        with self._lock:
            return self.metrics.recent_errors[-limit:]

    def clear_metrics(self):
        """Clear all metrics (useful for testing)."""
        with self._lock:
            self.metrics = ErrorMetrics()
            self._start_time = now_utc()


# Global error monitor
_error_monitor = ErrorMonitor()


def get_error_monitor() -> ErrorMonitor:
    """Get the global error monitor."""
    return _error_monitor

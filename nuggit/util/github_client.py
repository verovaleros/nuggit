"""
Enhanced GitHub API client with comprehensive rate limiting and retry logic.

This module provides an improved GitHub API client that handles rate limiting,
implements exponential backoff, and provides better error handling for GitHub API calls.
"""

import time
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, TypeVar, Union
from dataclasses import dataclass
from enum import Enum

from github import Github
from github.GithubException import GithubException
from github.Repository import Repository

from nuggit.util.timezone import now_utc, utc_now_iso

# Import error recovery utilities
try:
    from nuggit.util.error_recovery import circuit_breaker, CircuitBreakerConfig
    ERROR_RECOVERY_AVAILABLE = True
except ImportError:
    ERROR_RECOVERY_AVAILABLE = False

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Constants
DEFAULT_RATE_LIMIT_RESET_TIME = 3600  # 1 hour in seconds


class RateLimitType(Enum):
    """Types of GitHub API rate limits."""
    CORE = "core"
    SEARCH = "search"
    GRAPHQL = "graphql"


@dataclass
class RateLimitInfo:
    """Information about GitHub API rate limits."""
    limit: int
    remaining: int
    reset_time: datetime
    used: int
    
    @property
    def reset_in_seconds(self) -> int:
        """Get seconds until rate limit reset."""
        return max(0, int((self.reset_time - datetime.utcnow()).total_seconds()))
    
    @property
    def is_exhausted(self) -> bool:
        """Check if rate limit is exhausted."""
        return self.remaining <= 0


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 300.0  # 5 minutes
    exponential_base: float = 2.0
    jitter: bool = True
    respect_retry_after: bool = True


class GitHubAPIClient:
    """Enhanced GitHub API client with rate limiting and retry logic."""
    
    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        self.token = token
        self.timeout = timeout
        self._github = Github(token, timeout=timeout) if token else Github(timeout=timeout)
        self._rate_limit_cache: Dict[RateLimitType, RateLimitInfo] = {}
        self._last_rate_limit_check = datetime.min
        self._rate_limit_check_interval = timedelta(minutes=5)  # Check every 5 minutes instead of 1
        
        # Statistics
        self._stats = {
            'requests_made': 0,
            'rate_limit_hits': 0,
            'retries_performed': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_wait_time': 0.0
        }
    
    def _update_rate_limit_info(self, force: bool = False):
        """Update cached rate limit information."""
        now = datetime.utcnow()

        if not force and (now - self._last_rate_limit_check) < self._rate_limit_check_interval:
            return

        try:
            rate_limit = self._github.get_rate_limit()

            # Handle different PyGithub API versions
            if hasattr(rate_limit, 'core'):
                # Newer PyGithub API
                core = rate_limit.core
                search = rate_limit.search
            else:
                # Older PyGithub API or different structure
                # Use the rate_limit object directly if it has the needed attributes
                if hasattr(rate_limit, 'limit'):
                    core = rate_limit
                    # Use default search rate limit values if no separate search info is available
                    search = None
                else:
                    # If we can't determine the structure, create default values
                    logger.debug("Unable to determine rate limit structure, using defaults")
                    self._rate_limit_cache[RateLimitType.CORE] = RateLimitInfo(
                        limit=5000, remaining=5000, reset_time=int(now.timestamp()) + DEFAULT_RATE_LIMIT_RESET_TIME, used=0
                    )
                    self._rate_limit_cache[RateLimitType.SEARCH] = RateLimitInfo(
                        limit=30, remaining=30, reset_time=int(now.timestamp()) + DEFAULT_RATE_LIMIT_RESET_TIME, used=0
                    )
                    self._last_rate_limit_check = now
                    return

            # Update core rate limit
            self._rate_limit_cache[RateLimitType.CORE] = RateLimitInfo(
                limit=core.limit,
                remaining=core.remaining,
                reset_time=core.reset,
                used=core.limit - core.remaining
            )

            # Update search rate limit
            if search is not None:
                self._rate_limit_cache[RateLimitType.SEARCH] = RateLimitInfo(
                    limit=search.limit,
                    remaining=search.remaining,
                    reset_time=search.reset,
                    used=search.limit - search.remaining
                )
            else:
                # Use default search rate limit values if no separate search info is available
                self._rate_limit_cache[RateLimitType.SEARCH] = RateLimitInfo(
                    limit=30, remaining=30, reset_time=int(now.timestamp()) + DEFAULT_RATE_LIMIT_RESET_TIME, used=0
                )

            self._last_rate_limit_check = now

        except Exception as e:
            logger.debug(f"Failed to update rate limit info: {e}")
            # Don't spam warnings, just use default values
            if not self._rate_limit_cache:
                self._rate_limit_cache[RateLimitType.CORE] = RateLimitInfo(
                    limit=5000, remaining=5000, reset_time=int(now.timestamp()) + DEFAULT_RATE_LIMIT_RESET_TIME, used=0
                )
                self._rate_limit_cache[RateLimitType.SEARCH] = RateLimitInfo(
                    limit=30, remaining=30, reset_time=int(now.timestamp()) + DEFAULT_RATE_LIMIT_RESET_TIME, used=0
                )
    
    def get_rate_limit_info(self, rate_type: RateLimitType = RateLimitType.CORE) -> Optional[RateLimitInfo]:
        """Get current rate limit information."""
        self._update_rate_limit_info()
        return self._rate_limit_cache.get(rate_type)
    
    def _calculate_backoff_delay(self, attempt: int, config: RetryConfig, rate_limit_reset: Optional[int] = None) -> float:
        """Calculate backoff delay with exponential backoff and jitter."""
        if rate_limit_reset and config.respect_retry_after:
            # If we have rate limit reset time, wait until then (with some buffer)
            delay = rate_limit_reset + random.uniform(1, 5)
        else:
            # Exponential backoff
            delay = config.base_delay * (config.exponential_base ** attempt)
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            delay *= random.uniform(0.5, 1.5)
        
        # Cap at max delay
        return min(delay, config.max_delay)
    
    def _should_retry(self, exception: Exception, attempt: int, config: RetryConfig) -> bool:
        """Determine if we should retry based on the exception and attempt count."""
        if attempt >= config.max_retries:
            return False
        
        if isinstance(exception, GithubException):
            # Retry on rate limit (403) or server errors (5xx)
            if exception.status == 403:  # Rate limit
                return True
            elif exception.status >= 500:  # Server errors
                return True
            elif exception.status == 502:  # Bad gateway
                return True
            elif exception.status == 503:  # Service unavailable
                return True
            elif exception.status == 504:  # Gateway timeout
                return True
        
        # Retry on network-related exceptions
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return True
        
        return False
    
    def _execute_with_retry(
        self,
        operation: Callable[[], T],
        config: RetryConfig,
        operation_name: str = "GitHub API call"
    ) -> T:
        """Execute an operation with retry logic and rate limiting."""
        last_exception = None
        
        for attempt in range(config.max_retries + 1):
            try:
                # Only check rate limit if we have cached info and it's not the first attempt
                if attempt > 0 and self._rate_limit_cache:
                    rate_info = self.get_rate_limit_info()
                    if rate_info and rate_info.is_exhausted:
                        wait_time = rate_info.reset_in_seconds + random.uniform(1, 5)
                        logger.warning(f"Rate limit exhausted, waiting {wait_time:.1f}s until reset")
                        time.sleep(wait_time)
                        self._stats['total_wait_time'] += wait_time
                        self._update_rate_limit_info(force=True)
                
                # Execute the operation
                self._stats['requests_made'] += 1
                result = operation()
                self._stats['successful_requests'] += 1
                
                if attempt > 0:
                    logger.info(f"{operation_name} succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                self._stats['failed_requests'] += 1
                
                if isinstance(e, GithubException) and e.status == 403:
                    self._stats['rate_limit_hits'] += 1
                
                if not self._should_retry(e, attempt, config):
                    logger.error(f"{operation_name} failed after {attempt} attempts: {e}")
                    break
                
                # Calculate delay
                rate_limit_reset = None
                if isinstance(e, GithubException) and e.status == 403:
                    rate_info = self.get_rate_limit_info()
                    if rate_info:
                        rate_limit_reset = rate_info.reset_in_seconds
                
                delay = self._calculate_backoff_delay(attempt, config, rate_limit_reset)
                
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s"
                )
                
                time.sleep(delay)
                self._stats['retries_performed'] += 1
                self._stats['total_wait_time'] += delay
                
                # Force rate limit update after rate limit errors
                if isinstance(e, GithubException) and e.status == 403:
                    self._update_rate_limit_info(force=True)
        
        # If we get here, all retries failed
        raise last_exception
    
    def get_repository(self, repo_name: str, config: Optional[RetryConfig] = None) -> Repository:
        """Get a repository with retry logic and circuit breaker protection."""
        if config is None:
            config = RetryConfig()

        def operation():
            return self._github.get_repo(repo_name)

        # Use circuit breaker if available
        if ERROR_RECOVERY_AVAILABLE:
            cb_config = CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                success_threshold=2
            )

            @circuit_breaker(f"github_get_repo_{repo_name}", cb_config)
            def protected_operation():
                return self._execute_with_retry(
                    operation,
                    config,
                    f"get_repository({repo_name})"
                )

            return protected_operation()
        else:
            return self._execute_with_retry(
                operation,
                config,
                f"get_repository({repo_name})"
            )
    
    def get_repository_info(
        self,
        owner: str,
        name: str,
        config: Optional[RetryConfig] = None
    ) -> Optional[Dict[str, Any]]:
        """Get repository information with enhanced error handling."""
        if config is None:
            config = RetryConfig()

        def operation():
            # Call GitHub API directly to avoid recursion
            repo = self._github.get_repo(f"{owner}/{name}")

            # Get contributors count (with fallback)
            try:
                contributors = repo.get_contributors()
                total_contributors = contributors.totalCount
            except Exception:
                total_contributors = "5000+"

            try:
                total_commits = repo.get_commits().totalCount
            except Exception:
                total_commits = 0

            # Get latest release
            latest_release = None
            try:
                releases = repo.get_releases()
                if releases.totalCount > 0:
                    latest_release = releases[0].tag_name
            except Exception:
                pass

            # Build repository info
            return {
                "id": repo.full_name,
                "name": repo.name,
                "description": repo.description or "",
                "url": repo.html_url,
                "topics": ", ".join(repo.get_topics()) if hasattr(repo, 'get_topics') else "",
                "license": repo.license.name if repo.license else "",
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "issues": repo.open_issues_count,
                "contributors": total_contributors,
                "commits": total_commits,
                "last_commit": repo.pushed_at.isoformat() if repo.pushed_at else None,
                "latest_release": latest_release,
            }

        try:
            return self._execute_with_retry(
                operation,
                config,
                f"get_repository_info({owner}/{name})"
            )
        except GithubException as e:
            if e.status == 404:
                logger.info(f"Repository {owner}/{name} not found")
                return None
            raise
    
    def get_commits(
        self,
        repo: Repository,
        limit: int = 5,
        config: Optional[RetryConfig] = None
    ) -> list:
        """Get repository commits with retry logic."""
        if config is None:
            config = RetryConfig(max_retries=3)  # Fewer retries for commits
        
        def operation():
            from nuggit.util.github import get_recent_commits
            return get_recent_commits(repo, limit=limit, max_retries=1)
        
        return self._execute_with_retry(
            operation,
            config,
            f"get_commits({repo.full_name})"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = self._stats.copy()
        
        # Add rate limit information
        rate_info = self.get_rate_limit_info()
        if rate_info:
            stats['rate_limit'] = {
                'remaining': rate_info.remaining,
                'limit': rate_info.limit,
                'reset_in_seconds': rate_info.reset_in_seconds,
                'utilization': (rate_info.used / rate_info.limit) if rate_info.limit > 0 else 0
            }
        
        # Calculate success rate
        total_requests = stats['successful_requests'] + stats['failed_requests']
        stats['success_rate'] = (
            stats['successful_requests'] / total_requests
            if total_requests > 0 else 0
        )
        
        return stats


# Global client instance
_github_client: Optional[GitHubAPIClient] = None


def get_github_client(token: Optional[str] = None) -> GitHubAPIClient:
    """Get or create the global GitHub client."""
    global _github_client
    
    if _github_client is None or (_github_client.token != token):
        _github_client = GitHubAPIClient(token)
    
    return _github_client


def get_client_stats() -> Dict[str, Any]:
    """Get GitHub client statistics."""
    global _github_client
    
    if _github_client is None:
        return {"error": "GitHub client not initialized"}
    
    return _github_client.get_stats()

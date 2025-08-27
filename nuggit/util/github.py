import re
import time
import os
import random
from github import Github
from github.GithubException import GithubException
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# GitHub API Configuration Constants
GITHUB_API_TIMEOUT_SECONDS = 10
GITHUB_TOKEN_PREVIEW_LENGTH = 4
DEFAULT_COMMIT_LIMIT = 5
MAX_COMMIT_MESSAGE_LENGTH = 100
COMMIT_MESSAGE_TRUNCATE_SUFFIX = "..."
COMMIT_SHA_SHORT_LENGTH = 7
DEFAULT_CONTRIBUTORS_FALLBACK = 5000
DEFAULT_COMMITS_FALLBACK = 0
DEFAULT_MAX_RETRIES = 3
RATE_LIMIT_STATUS_CODE = 403
NOT_FOUND_STATUS_CODE = 404
RATE_LIMIT_MAX_WAIT_SECONDS = 60

# Get GitHub token from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if GITHUB_TOKEN:
    logging.info(f"GitHub token loaded from environment: {GITHUB_TOKEN[:GITHUB_TOKEN_PREVIEW_LENGTH]}...")
else:
    logging.warning("No GitHub token found in environment")

# Suppress lower-level logs from PyGithub
logging.getLogger("github").setLevel(logging.ERROR)

# Import enhanced GitHub client
try:
    from nuggit.util.github_client import get_github_client, RetryConfig
    from nuggit.util.timezone import normalize_github_datetime, utc_now_iso
    USE_ENHANCED_CLIENT = True
except ImportError:
    USE_ENHANCED_CLIENT = False
    logging.warning("Enhanced GitHub client not available, using basic client")


def validate_repo_url(repo_url):
    """
    Validate the URL is a valid GitHub repository.

    Args:
        repo_url (str): The URL of the GitHub repository.

    Returns:
        tuple: A tuple containing the owner and repository name if the URL is valid, otherwise False.
    """
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', repo_url)
    if not match:
        return False
    return match.groups()


def get_repo_latest_release(repo):
    """
    Get the latest release tag name for a given repository.
    Args:
        repo (Repository): The GitHub repository object.
    Returns:
        str: The latest release tag name or "No release" if not found.
    """
    try:
        release = repo.get_latest_release()
        return release.tag_name
    except Exception:
        return "No release"


def get_repo_license(repo):
    """
    Get the license name for a given repository.
    Args:
        repo (Repository): The GitHub repository object.
    Returns:
        str: The license name or "No license" if not found.
    """
    try:
        license_info = repo.get_license()
        if license_info:
            return license_info.license.name
        else:
            return "No license"
    except GithubException:
        return "No license"


def get_repo_topics(repo):
    """
    Get the topics for a given repository.
    Args:
        repo (Repository): The GitHub repository object.
    Returns:
        list: A list of topics or an empty list if an error occurs.
    """
    try:
        topics = repo.get_topics()
        return topics
    except GithubException as e:
        return []


def get_repo_info(repo_owner, repo_name, token=None):
    """
    Get information about a GitHub repository with enhanced rate limiting.
    Args:
        repo_owner (str): The owner of the repository.
        repo_name (str): The name of the repository.
        token (str, optional): The GitHub access token. Defaults to None.
    Returns:
        dict: A dictionary containing information about the repository.
    """
    # Use the global token if none is provided
    if token is None:
        token = GITHUB_TOKEN

    # Use enhanced client if available
    if USE_ENHANCED_CLIENT:
        try:
            client = get_github_client(token)
            return client.get_repository_info(repo_owner, repo_name)
        except Exception as e:
            logging.error(f"Enhanced client failed, falling back to basic client: {e}")

    # Fallback to basic client
    gh = Github(token, timeout=GITHUB_API_TIMEOUT_SECONDS) if token else Github(timeout=GITHUB_API_TIMEOUT_SECONDS)

    try:
        rate_limit = gh.get_rate_limit()
        # Handle different PyGithub API versions
        if hasattr(rate_limit, 'core'):
            rate = rate_limit.core
        else:
            rate = rate_limit
        print(f"🔑 Authenticated? {token is not None}")
        print(f"📊 GitHub Rate Limit: {rate.remaining}/{rate.limit}, reset at {rate.reset}")
    except Exception as e:
        print(f"⚠️ Could not check GitHub rate limit: {e}")
        # Continue anyway - we'll catch errors when trying to get the repo
    try:
        repo = gh.get_repo(f"{repo_owner}/{repo_name}")

        # Get contributors count (with fallback)
        try:
            contributors = repo.get_contributors()
            total_contributors = contributors.totalCount
        except GithubException:
            total_contributors = f"{DEFAULT_CONTRIBUTORS_FALLBACK}+"

        try:
            total_commits = repo.get_commits().totalCount
        except GithubException:
            total_commits = DEFAULT_COMMITS_FALLBACK

        repo_info = {
            "id": f"{repo_owner}/{repo_name}",
            "name": repo.name,
            "description": repo.description or "No description provided.",
            "url": repo.html_url,
            "topics": ', '.join(get_repo_topics(repo)),
            "license": get_repo_license(repo),
            "created_at": normalize_github_datetime(repo.created_at.isoformat() if repo.created_at else None),
            "updated_at": normalize_github_datetime(repo.updated_at.isoformat() if repo.updated_at else None),
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "issues": repo.open_issues_count,
            "contributors": total_contributors if isinstance(total_contributors, int) else DEFAULT_CONTRIBUTORS_FALLBACK,
            "commits": total_commits,
            "last_commit": normalize_github_datetime(repo.pushed_at.isoformat() if repo.pushed_at else None),
            "latest_release": get_repo_latest_release(repo),
            "tags": "",
            "notes": ""
        }

        repo_info["last_synced"] = utc_now_iso()

        return repo_info

    except GithubException as e:
        print(f"❌ Error accessing {repo_owner}/{repo_name}: {e}")
        return None


def get_recent_commits(repo, limit=DEFAULT_COMMIT_LIMIT, branch=None, max_retries=DEFAULT_MAX_RETRIES):
    """
    Get recent commits for a given repository with improved error handling and options.

    Args:
        repo (Repository): The GitHub repository object.
        limit (int, optional): The number of commits to retrieve. Defaults to DEFAULT_COMMIT_LIMIT.
        branch (str, optional): The branch to get commits from. Defaults to None (uses default branch).
        max_retries (int, optional): Maximum number of retries for API calls. Defaults to DEFAULT_MAX_RETRIES.

    Returns:
        list: A list of dictionaries containing commit information with the following keys:
            - sha: The short SHA of the commit
            - author: The name of the author
            - date: The date of the commit in ISO format
            - message: The first line of the commit message

    Raises:
        ValueError: If repo is None or limit is not a positive integer
    """
    # Parameter validation
    if repo is None:
        logging.error("Repository object cannot be None")
        return []

    if not isinstance(limit, int) or limit <= 0:
        logging.warning(f"Invalid limit value: {limit}. Using default of {DEFAULT_COMMIT_LIMIT}.")
        limit = DEFAULT_COMMIT_LIMIT

    # Initialize result list
    result = []

    # Enhanced retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            # Get commits with optional branch parameter
            kwargs = {}
            if branch:
                kwargs['sha'] = branch

            commits_paginated = repo.get_commits(**kwargs)

            # Handle pagination properly for large repositories
            count = 0
            for commit in commits_paginated:
                if count >= limit:
                    break

                # Safely extract commit information with fallbacks for all fields
                try:
                    # Get short SHA (safely handle if sha is None)
                    short_sha = commit.sha[:COMMIT_SHA_SHORT_LENGTH] if commit and commit.sha else "Unknown"

                    # Get author name with fallbacks
                    author_name = "Unknown"
                    if commit and commit.commit and commit.commit.author:
                        author_name = commit.commit.author.name or "Unknown"

                    # Get date with fallbacks and normalize timezone
                    commit_date = ""
                    if commit and commit.commit and commit.commit.author:
                        if commit.commit.author.date:
                            try:
                                raw_date = commit.commit.author.date.isoformat()
                                commit_date = normalize_github_datetime(raw_date) or ""
                            except (AttributeError, TypeError):
                                commit_date = str(commit.commit.author.date)

                    # Get message with fallbacks
                    commit_message = ""
                    if commit and commit.commit and commit.commit.message:
                        # Get first line of commit message, or truncate if too long
                        message_lines = commit.commit.message.splitlines()
                        commit_message = message_lines[0] if message_lines else ""
                        # Truncate if too long
                        if len(commit_message) > MAX_COMMIT_MESSAGE_LENGTH:
                            truncate_length = MAX_COMMIT_MESSAGE_LENGTH - len(COMMIT_MESSAGE_TRUNCATE_SUFFIX)
                            commit_message = commit_message[:truncate_length] + COMMIT_MESSAGE_TRUNCATE_SUFFIX

                    result.append({
                        "sha": short_sha,
                        "author": author_name,
                        "date": commit_date,
                        "message": commit_message
                    })

                    count += 1
                except Exception as e:
                    logging.warning(f"Error processing commit: {e}")
                    # Continue to next commit if there's an error with this one
                    continue

            # If we got here without exceptions, break the retry loop
            break

        except GithubException as e:
            if e.status == RATE_LIMIT_STATUS_CODE and attempt < max_retries - 1:
                # Rate limit hit - use exponential backoff
                wait_time = min(2 ** attempt + random.uniform(0, 1), RATE_LIMIT_MAX_WAIT_SECONDS)
                logging.warning(f"GitHub API rate limit hit, retrying ({attempt+1}/{max_retries}) in {wait_time:.1f}s: {e}")
                time.sleep(wait_time)
            elif e.status == NOT_FOUND_STATUS_CODE:
                # Repository or branch not found
                logging.error(f"Repository or branch not found: {e}")
                return []
            else:
                # Log other GitHub exceptions
                logging.error(f"GitHub API error: {e}")
                return []
        except Exception as e:
            # Catch any other exceptions
            logging.error(f"Unexpected error fetching commits: {e}")
            return []

    return result


def get_token():
    """Get the GitHub token."""
    return GITHUB_TOKEN


def get_gh_client(token: str = None):
    """Get a GitHub client instance with enhanced rate limiting."""
    if token is None:
        token = GITHUB_TOKEN

    if USE_ENHANCED_CLIENT:
        return get_github_client(token)
    else:
        return Github(token, timeout=GITHUB_API_TIMEOUT_SECONDS) if token else Github(timeout=GITHUB_API_TIMEOUT_SECONDS)


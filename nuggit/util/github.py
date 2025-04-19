import re
import time
import os
from github import Github
from github.GithubException import GithubException
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Get GitHub token from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if GITHUB_TOKEN:
    logging.info(f"GitHub token loaded from environment: {GITHUB_TOKEN[:4]}...")
else:
    logging.warning("No GitHub token found in environment")

# Suppress lower-level logs from PyGithub
logging.getLogger("github").setLevel(logging.ERROR)


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
    # Use the global token if none is provided
    if token is None:
        token = GITHUB_TOKEN
    """
    Get information about a GitHub repository.
    Args:
        repo_owner (str): The owner of the repository.
        repo_name (str): The name of the repository.
        token (str, optional): The GitHub access token. Defaults to None.
    Returns:
        dict: A dictionary containing information about the repository.
    """
    # Authenticate with GitHub
    gh = Github(token, timeout=10) if token else Github(timeout=10)

    rate = gh.get_rate_limit().core
    print(f"🔑 Authenticated? {token is not None}")
    print(f"📊 GitHub Rate Limit: {rate.remaining}/{rate.limit}, reset at {rate.reset}")
    try:
        repo = gh.get_repo(f"{repo_owner}/{repo_name}")

        # Get contributors count (with fallback)
        try:
            contributors = repo.get_contributors()
            total_contributors = contributors.totalCount
        except GithubException:
            total_contributors = "5000+"

        try:
            total_commits = repo.get_commits().totalCount
        except GithubException:
            total_commits = 0

        repo_info = {
            "id": f"{repo_owner}/{repo_name}",
            "name": repo.name,
            "description": repo.description or "No description provided.",
            "url": repo.html_url,
            "topics": ', '.join(get_repo_topics(repo)),
            "license": get_repo_license(repo),
            "created_at": repo.created_at.isoformat() if repo.created_at else "",
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else "",
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "issues": repo.open_issues_count,
            "contributors": total_contributors if isinstance(total_contributors, int) else 5000,
            "commits": total_commits,
            "last_commit": repo.pushed_at.isoformat() if repo.pushed_at else "",
            "latest_release": get_repo_latest_release(repo),
            "tags": "",
            "notes": ""
        }

        repo_info["last_synced"] = datetime.utcnow().isoformat()

        return repo_info

    except GithubException as e:
        print(f"❌ Error accessing {repo_owner}/{repo_name}: {e}")
        return None


def get_recent_commits(repo, limit=5, branch=None, max_retries=3):
    """
    Get recent commits for a given repository with improved error handling and options.

    Args:
        repo (Repository): The GitHub repository object.
        limit (int, optional): The number of commits to retrieve. Defaults to 5.
        branch (str, optional): The branch to get commits from. Defaults to None (uses default branch).
        max_retries (int, optional): Maximum number of retries for API calls. Defaults to 3.

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
        logging.warning(f"Invalid limit value: {limit}. Using default of 5.")
        limit = 5

    # Initialize result list
    result = []

    # Retry logic for API rate limits or network issues
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
                    short_sha = commit.sha[:7] if commit and commit.sha else "Unknown"

                    # Get author name with fallbacks
                    author_name = "Unknown"
                    if commit and commit.commit and commit.commit.author:
                        author_name = commit.commit.author.name or "Unknown"

                    # Get date with fallbacks
                    commit_date = ""
                    if commit and commit.commit and commit.commit.author:
                        if commit.commit.author.date:
                            try:
                                commit_date = commit.commit.author.date.isoformat()
                            except (AttributeError, TypeError):
                                commit_date = str(commit.commit.author.date)

                    # Get message with fallbacks
                    commit_message = ""
                    if commit and commit.commit and commit.commit.message:
                        # Get first line of commit message, or truncate if too long
                        message_lines = commit.commit.message.splitlines()
                        commit_message = message_lines[0] if message_lines else ""
                        # Truncate if too long
                        if len(commit_message) > 100:
                            commit_message = commit_message[:97] + "..."

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
            if e.status == 403 and attempt < max_retries - 1:
                # This might be a rate limit issue, wait and retry
                logging.warning(f"GitHub API rate limit hit, retrying ({attempt+1}/{max_retries}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            elif e.status == 404:
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


import re
from os import getenv
from github import Github
from github.GithubException import GithubException
import logging
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

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


def get_repo_info(repo_owner, repo_name, token=getenv("GITHUB_TOKEN")):
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


def get_recent_commits(repo, limit=5):
    """
    Get recent commits for a given repository.
    Args:
        repo (Repository): The GitHub repository object.
        limit (int, optional): The number of commits to retrieve. Defaults to 5.
    Returns:
        list: A list of dictionaries containing commit information.
    """
    try:
        commits = repo.get_commits()
        return [{
            "sha": commit.sha[:7],
            "author": commit.commit.author.name if commit.commit.author else "Unknown",
            "date": commit.commit.author.date.isoformat() if commit.commit.author else "",
            "message": commit.commit.message.splitlines()[0]
        } for commit in commits[:limit]]
    except GithubException:
        return []


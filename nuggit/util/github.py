import re
from github import Github
from github.GithubException import GithubException
import logging

# Suppress lower-level logs from PyGithub
logging.getLogger("github").setLevel(logging.ERROR)


def validate_repo_url(repo_url):
    """
    Validate the URL is a valid GitHub repository.
    """
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', repo_url)
    if not match:
        return False
    return match.groups() 


def get_repo_latest_release(repo):
    try:
        release = repo.get_latest_release()
        return release.tag_name
    except Exception:
        return "No release"


def get_repo_license(repo):
    try:
        license_info = repo.get_license()
        if license_info:
            return license_info.license.name
        else:
            return "No license"
    except GithubException:
        return "No license"


def get_repo_topics(repo):
    try:
        topics = repo.get_topics()
        return topics
    except GithubException as e:
        return []


def get_repo_info(repo_owner, repo_name, token=None):
    # Authenticate with GitHub
    gh = Github(token) if token else Github()

    try:
        repo = gh.get_repo(f"{repo_owner}/{repo_name}")

        # Get contributors count (with fallback)
        try:
            contributors = repo.get_contributors()
            total_contributors = contributors.totalCount
        except GithubException:
            total_contributors = "5000+"

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
            "contributors": str(total_contributors),
            "commits": repo.get_commits().totalCount,
            "last_commit": repo.pushed_at.isoformat() if repo.pushed_at else "",
            "tags": "",
            "notes": ""
        }

        return repo_info

    except GithubException as e:
        print(f"Error accessing repository: {e}")
        return None


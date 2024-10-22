import re
from github import Github
from github.GithubException import GithubException

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
        releases = repo.get_releases()
        if releases.totalCount > 0:
            latest_release = releases[0]
            return f"{latest_release.tag_name} ({latest_release.published_at.date()})"
        else:
            return "No releases"
    except GithubException:
        return "No releases"


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
        repo_info = {
            'Tool': repo.name,
            'Owner': repo.owner.login,
            'URL': repo.html_url,
            'About': repo.description or "No description provided.",
            'Stars': repo.stargazers_count,
            'Forks': repo.forks_count,
            'Issues': repo.open_issues_count,
            'Latest Release': get_repo_latest_release(repo),
            'License': get_repo_license(repo),
            'Topics': get_repo_topics(repo),
        }
        return repo_info
    except GithubException as e:
        print(f"Error accessing repository: {e}")
        return None
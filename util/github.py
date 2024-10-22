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

def get_repo_info(repo_owner, repo_name, token=None):
    # Authenticate with GitHub
    gh = Github(token) if token else Github()

    try:
        repo = gh.get_repo(f"{repo_owner}/{repo_name}")
        repo_info = {
            'name': repo.name,
            'owner': repo.owner.login,
            'url': repo.html_url,
            'description': repo.description or "No description provided.",
            'stars': repo.stargazers_count,
            'forks': repo.forks_count,
            'open_issues': repo.open_issues_count,
        }
        return repo_info
    except GithubException as e:
        print(f"Error accessing repository: {e}")
        return None
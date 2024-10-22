import re

def validate_repo_url(repo_url):
    """
    Validate the URL is a valid GitHub repository.
    """
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', repo_url)
    if not match:
        return False
    return True

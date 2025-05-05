#!/usr/bin/env python3
"""
Script to test the improved get_recent_commits function.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from github import Github

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nuggit.util.github import get_recent_commits

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    # Load environment variables
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        logging.warning("No GitHub token found. Using unauthenticated access (rate limits apply).")
    
    # Initialize GitHub client
    gh = Github(token) if token else Github()
    
    # Test repositories
    test_repos = [
        "verovaleros/nuggit",  # The current repository
        "microsoft/vscode",    # A large repository
        "nonexistent/repo"     # A nonexistent repository
    ]
    
    for repo_id in test_repos:
        logging.info(f"Testing get_recent_commits with repository: {repo_id}")
        
        try:
            # Get repository
            repo = gh.get_repo(repo_id)
            
            # Test with default parameters
            logging.info("Testing with default parameters...")
            commits = get_recent_commits(repo)
            logging.info(f"Found {len(commits)} commits")
            for commit in commits:
                logging.info(f"  {commit['sha']} - {commit['author']} - {commit['message']}")
            
            # Test with branch parameter
            logging.info("Testing with branch parameter...")
            branches = list(repo.get_branches())[:1]  # Get first branch
            if branches:
                branch_name = branches[0].name
                logging.info(f"Using branch: {branch_name}")
                commits = get_recent_commits(repo, branch=branch_name, limit=3)
                logging.info(f"Found {len(commits)} commits on branch {branch_name}")
                for commit in commits:
                    logging.info(f"  {commit['sha']} - {commit['author']} - {commit['message']}")
            
        except Exception as e:
            logging.error(f"Error testing repository {repo_id}: {e}")
    
    logging.info("Testing complete!")

if __name__ == "__main__":
    main()

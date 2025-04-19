#!/usr/bin/env python3
"""
Script to test the improved repository API endpoints.
"""

import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# API base URL
API_BASE_URL = "http://localhost:8000"

def test_check_repository(repo_id):
    """Test the check repository endpoint."""
    logging.info(f"Testing check repository endpoint for {repo_id}")
    
    response = requests.get(f"{API_BASE_URL}/repositories/check/{repo_id}")
    logging.info(f"Status code: {response.status_code}")
    logging.info(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def test_add_repository_with_id(repo_id, token=None):
    """Test adding a repository with ID."""
    logging.info(f"Testing add repository endpoint with ID: {repo_id}")
    
    payload = {"id": repo_id}
    if token:
        payload["token"] = token
        
    response = requests.post(f"{API_BASE_URL}/repositories/", json=payload)
    logging.info(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        logging.info(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        logging.error(f"Error: {response.text}")
    
    return response

def test_add_repository_with_url(repo_url, token=None):
    """Test adding a repository with URL."""
    logging.info(f"Testing add repository endpoint with URL: {repo_url}")
    
    payload = {"url": repo_url}
    if token:
        payload["token"] = token
        
    response = requests.post(f"{API_BASE_URL}/repositories/", json=payload)
    logging.info(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        logging.info(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        logging.error(f"Error: {response.text}")
    
    return response

def test_update_repository(repo_id, token=None):
    """Test updating a repository."""
    logging.info(f"Testing update repository endpoint for {repo_id}")
    
    params = {}
    if token:
        params["token"] = token
        
    response = requests.put(f"{API_BASE_URL}/repositories/{repo_id}", params=params)
    logging.info(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        logging.info(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        logging.error(f"Error: {response.text}")
    
    return response

def test_batch_import(repo_ids, token=None):
    """Test batch import of repositories."""
    logging.info(f"Testing batch import endpoint with {len(repo_ids)} repositories")
    
    payload = {"repositories": repo_ids}
    if token:
        payload["token"] = token
        
    response = requests.post(f"{API_BASE_URL}/repositories/batch", json=payload)
    logging.info(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        logging.info(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        logging.error(f"Error: {response.text}")
    
    return response

def test_delete_repository(repo_id):
    """Test deleting a repository."""
    logging.info(f"Testing delete repository endpoint for {repo_id}")
    
    response = requests.delete(f"{API_BASE_URL}/repositories/{repo_id}")
    logging.info(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        logging.info(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        logging.error(f"Error: {response.text}")
    
    return response

def main():
    # Load environment variables
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        logging.warning("No GitHub token found. Using unauthenticated access (rate limits apply).")
    
    # Test repositories
    test_repos = [
        "verovaleros/nuggit",  # The current repository
        "microsoft/vscode",    # A large repository
        "nonexistent/repo"     # A nonexistent repository
    ]
    
    # Test check repository
    for repo_id in test_repos[:1]:  # Just test the first one
        test_check_repository(repo_id)
    
    # Test add repository with ID
    test_add_repository_with_id(test_repos[0], token)
    
    # Test add repository with URL
    test_add_repository_with_url("https://github.com/verovaleros/nuggit", token)
    
    # Test update repository
    test_update_repository(test_repos[0], token)
    
    # Test batch import
    test_batch_import(test_repos, token)
    
    # Test delete repository (uncomment to test)
    # test_delete_repository(test_repos[0])
    
    logging.info("Testing complete!")

if __name__ == "__main__":
    main()

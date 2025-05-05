# Nuggit Project Overview

Nuggit is a web application for tracking and managing GitHub repositories. It provides a dashboard for monitoring repository metrics, comparing versions over time, and adding comments to repositories.

## Project Architecture

Nuggit follows a client-server architecture with three main components:

1. **Backend API**: A FastAPI-based REST API that handles data processing, GitHub API interactions, and database operations.
2. **Frontend**: A Svelte-based single-page application (SPA) that provides the user interface.
3. **Database**: A SQLite database that stores repository information, comments, versions, and history.

## Key Features

- **Repository Dashboard**: View and search all tracked repositories
- **Repository Details**: Detailed view of repository metrics and information
- **Version Tracking**: Track changes to repositories over time
- **Version Comparison**: Compare metrics between different versions
- **Comments**: Add and view comments on repositories
- **Tagging**: Add tags to repositories for organization
- **GitHub Integration**: Fetch and update repository data from GitHub

## Component Overview

### Backend API

The backend API is built with FastAPI and provides endpoints for:

- Managing repositories (add, update, delete)
- Fetching repository details
- Managing comments
- Managing versions
- Comparing versions

The API interacts with the GitHub API to fetch repository data and stores it in the SQLite database.

### Frontend

The frontend is built with Svelte and provides:

- A dashboard for viewing all repositories
- A detail view for each repository
- Forms for adding and updating repositories
- UI for comparing versions
- UI for adding comments and tags

### Database

The SQLite database stores:

- Repository information
- Repository history (changes to fields)
- Comments
- Versions

## Data Flow

1. User adds a repository through the frontend
2. Frontend sends a request to the API
3. API fetches repository data from GitHub
4. API stores the data in the database
5. API returns the data to the frontend
6. Frontend displays the data to the user

When a repository is updated:

1. API fetches the latest data from GitHub
2. API compares the new data with the existing data
3. API records changes in the repository_history table
4. API creates a new version in the repository_versions table
5. API updates the repository data in the database

## Technology Stack

- **Backend**: Python, FastAPI, SQLite
- **Frontend**: JavaScript, Svelte
- **API Integration**: PyGithub (GitHub API client)
- **Deployment**: Docker (optional)

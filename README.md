# Nuggit: GitHub Repository Tracking and Analysis

Nuggit is a web application for tracking and analyzing GitHub repositories. It provides a dashboard for monitoring repository metrics, comparing versions over time, and adding comments to repositories.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/9c83975c-2139-4ee6-9e7a-6cbcb687792e">

## Features

- **Repository Dashboard**: View and search all tracked repositories
- **Repository Details**: Detailed view of repository metrics and information
- **Version Tracking**: Track changes to repositories over time
- **Version Comparison**: Compare metrics between different versions
- **Comments**: Add and view comments on repositories
- **Tagging**: Add tags to repositories for organization
- **GitHub Integration**: Fetch and update repository data from GitHub

## Architecture

Nuggit follows a client-server architecture with three main components:

1. **Backend API**: A FastAPI-based REST API that handles data processing, GitHub API interactions, and database operations.
2. **Frontend**: A Svelte-based single-page application (SPA) that provides the user interface.
3. **Database**: A SQLite database that stores repository information, comments, versions, and history.

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Node.js 14 or higher
- npm or yarn
- Git

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/verovaleros/nuggit.git
cd nuggit

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp nuggit/.env_EXAMPLE nuggit/.env
# Edit the .env file to add your GitHub token

# Start the API server
uvicorn nuggit.api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup

```bash
# Navigate to the frontend directory
cd nuggit/frontend

# Install dependencies
npm install
# or
yarn install

# Start the development server
npm run dev
# or
yarn dev
```

The frontend will be available at http://localhost:5173, and the API at http://localhost:8001.

## Docker

Run Nuggit via Docker Compose (recommended):

```bash
# Create and configure your .env file first
cp nuggit/.env_EXAMPLE nuggit/.env
# Edit the .env file to add your GitHub token in this format:
# GITHUB_TOKEN=your_github_token_here

# Start both frontend and API with Docker Compose
docker-compose up -d --build

# Check logs to verify GitHub token is loaded correctly
docker-compose logs
```

The application will be available at:
- Frontend: http://localhost:5173 (with hot-reloading enabled)
- API: http://localhost:8001

The Docker setup runs the frontend using `npm run dev` for development features.

## Documentation

For more detailed documentation, see:

- [Project Overview](docs/PROJECT_OVERVIEW.md): Overview of the project architecture and components
- [Installation Guide](docs/INSTALLATION.md): Detailed installation and setup instructions
- [API Documentation](docs/API.md): Documentation of the API endpoints
- [Database Documentation](docs/DATABASE.md): Documentation of the database schema
- [Frontend Documentation](docs/FRONTEND.md): Documentation of the frontend structure and components
- [Contributing Guide](docs/CONTRIBUTING.md): Guidelines for contributing to the project

## Legacy CLI Tool

Nuggit was originally a command-line tool. The legacy CLI can still be used:

```bash
python3 nuggit/nuggit.py --help
```

```
usage: nuggit.py [-h] -r REPO [-l LOG_FILE] [-d] [-v]

Nuggit: Small bits of big insights from GitHub repositories

optional arguments:
  -h, --help            show this help message and exit
  -r REPO, --repo REPO  URL of the GitHub repository to analyze.
  -l LOG_FILE, --log_file LOG_FILE
                        Log file name (default: nuggit.log)
  -d, --debug           Extra verbose for debugging.
  -v, --verbose         Be verbose
```

## License

This project is licensed under the GNU General Public License v2.0.

## About

Nuggit was created by verovaleros in October 2024.

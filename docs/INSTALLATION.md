# Nuggit Installation and Setup Guide

This guide provides instructions for setting up and running the Nuggit application.

## Prerequisites

- Python 3.9 or higher
- Node.js 14 or higher
- npm or yarn
- Git

## Clone the Repository

```bash
git clone https://github.com/verovaleros/nuggit.git
cd nuggit
```

## Backend Setup

### 1. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and edit it:

```bash
cp nuggit/.env_EXAMPLE nuggit/.env
```

Edit the `.env` file to add your GitHub token:

```
GITHUB_TOKEN=your_github_token_here
```

You can create a GitHub token at https://github.com/settings/tokens. The token needs the `repo` scope to access repository data.

### 4. Initialize the Database

The database will be automatically initialized when the API starts, but you can also initialize it manually:

```python
python -c "from nuggit.util.db import initialize_database; initialize_database()"
```

### 5. Start the API Server

```bash
uvicorn nuggit.api.main:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at http://localhost:8001.

## Frontend Setup

### 1. Navigate to the Frontend Directory

```bash
cd nuggit/frontend
```

### 2. Install Dependencies

```bash
npm install
# or
yarn install
```

### 3. Start the Development Server

```bash
npm run dev
# or
yarn dev
```

The frontend will be available at http://localhost:5173.

## Docker Setup

The Docker setup allows you to run both the frontend and API in a single container, making it easier to deploy and run the application.

### Option 1: Using Docker Compose (Recommended)

1. Make sure you have Docker and Docker Compose installed.

2. Create or update your `.env` file:

```bash
cp nuggit/.env_EXAMPLE nuggit/.env
# Edit the .env file to add your GitHub token
```

Make sure your `.env` file contains the GitHub token in this format:

```
GITHUB_TOKEN=your_github_token_here
```

3. Run the application using Docker Compose:

```bash
docker-compose up -d --build
```

This will:
- Build the Docker image if it doesn't exist
- Start the container in detached mode
- Map ports 8001 (API) and 5173 (frontend) to your host
- Mount your .env file and database file as volumes
- Load the GitHub token from your .env file
- Run the frontend using `npm run dev` for hot-reloading and development features

4. Check the logs to verify that the GitHub token is being loaded correctly:

```bash
docker-compose logs
```

You should see a message saying "GitHub token is set and ready to use"

5. Access the application:
   - Frontend: http://localhost:5173
   - API: http://localhost:8001

6. To stop the application:

```bash
docker-compose down
```

### Option 2: Using Docker Directly

1. Build the Docker image:

```bash
docker build -t nuggit .
```

2. Make sure your `.env` file is properly configured:

```bash
cp nuggit/.env_EXAMPLE nuggit/.env
# Edit the .env file to add your GitHub token in this format:
# GITHUB_TOKEN=your_github_token_here
```

3. Run the Docker container:

```bash
docker run -d \
  -p 8001:8001 \
  -p 5173:5173 \
  -v $(pwd)/nuggit/.env:/app/nuggit/.env:ro \
  -v $(pwd)/nuggit.db:/app/nuggit.db \
  --name nuggit \
  nuggit
```

4. Check the logs to verify that the GitHub token is being loaded correctly:

```bash
docker logs nuggit
```

You should see a message saying "GitHub token is set and ready to use"

5. Access the application:
   - Frontend: http://localhost:5173
   - API: http://localhost:8001

6. To stop the container:

```bash
docker stop nuggit
docker rm nuggit
```

## Production Deployment

For production deployment, you should:

1. Build the frontend for production:

```bash
cd nuggit/frontend
npm run build
# or
yarn build
```

2. Serve the frontend using a web server like Nginx or Apache.

3. Run the API server using a production ASGI server like Uvicorn with Gunicorn:

```bash
gunicorn nuggit.api.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8001
```

## Testing

### Run Backend Tests

```bash
python -m unittest discover tests
```

Or use the test script:

```bash
python scripts/run_db_tests.py
```

## Troubleshooting

### API Connection Issues

If the frontend cannot connect to the API, check that:

1. The API server is running on port 8001
2. There are no CORS issues (the API has CORS middleware enabled)
3. The frontend is using the correct API URL (http://localhost:8001)

### GitHub API Rate Limiting

If you encounter GitHub API rate limiting issues:

1. Make sure you have set a valid GitHub token in the `.env` file
2. Reduce the number of requests by limiting the number of repositories you add

### Database Issues

If you encounter database issues:

1. Check that the database file (`nuggit.db`) exists and is writable
2. Try initializing the database manually (see step 4 in Backend Setup)
3. If the database is corrupted, delete it and let the application create a new one

## Next Steps

After installation, you can:

1. Add repositories through the frontend
2. Explore repository details
3. Add comments and tags
4. Compare versions

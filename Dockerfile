FROM python:3.12

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Get git commit hash during build (requires git context)
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}

# Copy the API code
COPY nuggit/ /app/nuggit/

# Copy frontend files
COPY nuggit/frontend/ /app/frontend/

# Install frontend dependencies
WORKDIR /app/frontend
RUN npm install

# Go back to app directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create a script to load environment variables from .env file
RUN echo '#!/bin/bash\n\
if [ -f /app/nuggit/.env ]; then\n\
  export $(grep -v "^#" /app/nuggit/.env | xargs)\n\
fi' > /app/load_env.sh && chmod +x /app/load_env.sh

# Create a script to start both services
RUN echo '#!/bin/bash\n\
# Load environment variables from .env file\n\
source /app/load_env.sh\n\
\n\
# Print GitHub token status (without revealing the token)\n\
if [ -n "$GITHUB_TOKEN" ]; then\n\
  echo "GitHub token is set and ready to use"\n\
else\n\
  echo "WARNING: GitHub token is not set. Some features may not work correctly."\n\
fi\n\
\n\
# Start the API server\n\
uvicorn nuggit.api.main:app --host 0.0.0.0 --port 8001 &\n\
\n\
# Start the frontend using npm run dev\n\
cd /app/frontend && npm run dev -- --host 0.0.0.0 &\n\
\n\
# Wait for any process to exit\n\
wait -n\n\
\n\
# Exit with status of process that exited first\n\
exit $?' > /app/start.sh && chmod +x /app/start.sh

# Expose ports for API and frontend
EXPOSE 8001 5173

# Start both services
CMD ["/app/start.sh"]

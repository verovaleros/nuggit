# Nuggit: GitHub Repository Tracking and Analysis

Nuggit is a web application for tracking and analyzing GitHub repositories. It provides a dashboard for monitoring repository metrics, comparing versions over time, and adding comments to repositories.

<img width="1085" alt="image" src="https://github.com/user-attachments/assets/7541109c-d0a9-41f1-b981-f8708e55e803" />

## Features

- **User Authentication**: Secure user registration, login, and email verification
- **Repository Dashboard**: View and search all tracked repositories
- **Repository Details**: Detailed view of repository metrics and information
- **Version Tracking**: Track changes to repositories over time
- **Version Comparison**: Compare metrics between different versions
- **Comments**: Add and view comments on repositories
- **Tagging**: Add tags to repositories for organization
- **GitHub Integration**: Fetch and update repository data from GitHub
- **User Management**: Admin panel for managing users and system settings
- **Email Notifications**: Email verification and password reset functionality

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
- GitHub Personal Access Token (for repository data)
- SMTP server access (for email functionality)

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
# Edit the .env file with your configuration (see Configuration section below)

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

## Configuration

### Environment Variables

Nuggit requires several environment variables to be configured in the `.env` file:

#### Required Configuration

1. **GitHub Token** (Required for repository data):
   ```bash
   GITHUB_TOKEN=your_github_personal_access_token
   ```
   - Get your token from: https://github.com/settings/tokens
   - Required scopes: `public_repo` (for public repositories) or `repo` (for private repositories)

2. **JWT Secret Key** (Required for authentication):
   ```bash
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
   ```
   - Generate a secure key with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

3. **Email Configuration** (Required for user registration and password reset):
   ```bash
   FROM_EMAIL=nuggit@yourdomain.com
   FROM_NAME=Nuggit
   SMTP_HOST=your-smtp-server.com
   SMTP_PORT=587
   SMTP_USERNAME=your-smtp-username
   SMTP_PASSWORD=your-smtp-password
   SMTP_USE_TLS=true
   SMTP_USE_SSL=false
   ```

#### Optional Configuration

- `ACCESS_TOKEN_EXPIRE_MINUTES=10080` (7 days)
- `REFRESH_TOKEN_EXPIRE_DAYS=30`
- `BASE_URL=http://localhost:5173`
- `KO_FI_URL=https://ko-fi.com/yourusername`

### Email Setup Examples

#### Gmail
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use App Password, not regular password
SMTP_USE_TLS=true
```

#### Brevo (Sendinblue)
```bash
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=your-brevo-username
SMTP_PASSWORD=your-brevo-password
SMTP_USE_TLS=true
```

### First-Time Setup

1. **Copy the example configuration**:
   ```bash
   cp nuggit/.env_EXAMPLE nuggit/.env
   ```

2. **Edit the `.env` file** with your actual values

3. **Create an admin user** (after starting the application):
   ```bash
   docker-compose exec nuggit python nuggit/scripts/setup_admin.py
   ```

4. **Access the application**:
   - Frontend: http://localhost:5173
   - Register a new account or login with your admin credentials

## Docker

Run Nuggit via Docker Compose (recommended):

```bash
# Make sure you've configured your .env file first (see Configuration section above)

# Start both frontend and API with Docker Compose
docker-compose up -d --build

# Create an admin user (first time only)
docker-compose exec nuggit python nuggit/scripts/setup_admin.py

# Check logs to verify everything is working
docker-compose logs
```

The application will be available at:
- Frontend: http://localhost:5173 (with hot-reloading enabled)
- API: http://localhost:8001

The Docker setup runs the frontend using `npm run dev` for development features.

## User Management

### Authentication System

Nuggit includes a complete authentication system with:

- **User Registration**: New users can register with email verification
- **Email Verification**: Users must verify their email before accessing the system
- **Password Reset**: Users can reset their password via email
- **Admin Panel**: Administrators can manage users and system settings

### Creating Users

#### Admin User (First Time Setup)
```bash
# Create an admin user after starting the application
docker-compose exec nuggit python nuggit/scripts/setup_admin.py
```

#### Regular Users
1. **Via Web Interface**: Users can register at http://localhost:5173
2. **Via Admin Panel**: Admins can create users through the admin interface
3. **Via Script**: Use the setup script to create additional admin users

### Admin Features

Admin users have access to:
- **User Management**: View, activate/deactivate, and manage all users
- **System Settings**: Configure application-wide settings
- **Repository Access**: View and manage all repositories (not just their own)
- **User Statistics**: View system usage and user activity

### User Access Control

- **Repository Isolation**: Users can only see and manage their own repositories
- **Admin Override**: Admin users can access all repositories
- **Secure Authentication**: JWT-based authentication with refresh tokens
- **Email Verification**: Required for account activation

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

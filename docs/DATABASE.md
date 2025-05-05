# Nuggit Database Documentation

Nuggit uses a SQLite database to store repository information, history, comments, and versions. This document describes the database schema and relationships.

## Database Schema

The database consists of four main tables:

1. `repositories`: Stores repository information
2. `repository_history`: Tracks changes to repository fields
3. `repository_comments`: Stores comments on repositories
4. `repository_versions`: Stores versions of repositories

### Table: repositories

This table stores the main repository information.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key, format: "owner/repo" |
| name | TEXT | Repository name |
| description | TEXT | Repository description |
| url | TEXT | GitHub URL |
| topics | TEXT | Comma-separated list of topics |
| license | TEXT | License information |
| created_at | TEXT | ISO format timestamp of repository creation |
| updated_at | TEXT | ISO format timestamp of last GitHub update |
| stars | INTEGER | Number of stars |
| forks | INTEGER | Number of forks |
| issues | INTEGER | Number of open issues |
| contributors | TEXT | Number of contributors |
| commits | INTEGER | Total number of commits |
| last_commit | TEXT | ISO format timestamp of last commit |
| tags | TEXT | Comma-separated list of user-defined tags |
| notes | TEXT | User notes |
| last_synced | TEXT | ISO format timestamp of last sync with GitHub |

### Table: repository_history

This table tracks changes to repository fields over time.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| repo_id | TEXT | Foreign key to repositories.id |
| field | TEXT | Name of the field that changed |
| old_value | TEXT | Previous value |
| new_value | TEXT | New value |
| changed_at | TEXT | ISO format timestamp of the change |

### Table: repository_comments

This table stores comments on repositories.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| repo_id | TEXT | Foreign key to repositories.id |
| comment | TEXT | Comment text |
| author | TEXT | Comment author (default: "Anonymous") |
| created_at | TEXT | ISO format timestamp of comment creation |

### Table: repository_versions

This table stores versions of repositories.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| repo_id | TEXT | Foreign key to repositories.id |
| version_number | TEXT | Version number or name |
| release_date | TEXT | ISO format timestamp of release date (optional) |
| description | TEXT | Version description (optional) |
| created_at | TEXT | ISO format timestamp of version creation |

## Relationships

- `repository_history.repo_id` → `repositories.id` (many-to-one)
- `repository_comments.repo_id` → `repositories.id` (many-to-one)
- `repository_versions.repo_id` → `repositories.id` (many-to-one)

## Database Operations

The database operations are handled by functions in the `nuggit/util/db.py` and `nuggit/util/async_db.py` files.

### Key Functions

- `initialize_database()`: Creates the tables if they don't exist
- `get_connection()`: Context manager for SQLite connections
- `insert_or_update_repo(repo_data)`: Inserts or updates a repository
- `get_repository(repo_id)`: Retrieves a repository by ID
- `list_all_repositories()`: Lists all repositories
- `delete_repository(repo_id)`: Deletes a repository and related data
- `add_comment(repo_id, comment, author)`: Adds a comment to a repository
- `get_comments(repo_id)`: Gets comments for a repository
- `add_version(repo_id, version_number, release_date, description)`: Adds a version to a repository
- `get_versions(repo_id)`: Gets versions for a repository
- `get_repository_history(repo_id)`: Gets history for a repository

## Version Tracking

When a repository is updated from GitHub, the changes are recorded in the `repository_history` table. A new version is also created in the `repository_versions` table to mark the update.

The version comparison feature uses the history data to show what changed between two versions.

## Asynchronous Operations

The `nuggit/util/async_db.py` file provides asynchronous wrappers around the synchronous database functions in `db.py`, allowing them to be used with FastAPI's async routes.

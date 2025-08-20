# Data Integrity Implementation

This document describes the comprehensive data integrity features implemented in Nuggit to address the following issues:

- ✅ **Database Migrations** - Schema changes with automatic version tracking
- ✅ **Foreign Key Constraints** - Proper referential integrity enforcement  
- ✅ **Data Validation** - Comprehensive validation before database insertion
- ✅ **Optimistic Locking** - Safe handling of concurrent modifications

## 1. Database Migrations System

### Overview
A comprehensive migration system that handles schema versioning, forward/backward migrations, and automatic migration discovery.

### Key Features
- **Version Tracking**: All migrations are tracked in `schema_migrations` table
- **Rollback Support**: Each migration includes rollback SQL for safe reversions
- **Integrity Validation**: Checksums ensure migration files haven't been tampered with
- **Dependency Management**: Migrations can specify dependencies on other migrations
- **CLI Tool**: Command-line interface for managing migrations

### Files
- `nuggit/util/migrations.py` - Core migration system
- `nuggit/cli/migrate.py` - CLI tool for migration management
- `nuggit/migrations/001_initial_schema.sql` - Initial schema with constraints

### Usage
```bash
# Check migration status
python -m nuggit.cli.migrate status

# Apply all pending migrations
python -m nuggit.cli.migrate migrate

# Rollback to specific version
python -m nuggit.cli.migrate rollback --target 001

# Validate migration integrity
python -m nuggit.cli.migrate validate
```

### Migration File Format
```sql
-- Name: Migration Description
-- Dependencies: 001,002
-- Created: 2025-01-19T12:00:00

-- +migrate Up
CREATE TABLE example (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- +migrate Down
DROP TABLE example;
```

## 2. Foreign Key Constraints

### Implementation
All tables now include proper foreign key constraints with CASCADE deletion:

```sql
-- Repository relationships
FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
```

### Affected Tables
- `repository_history.repo_id` → `repositories.id`
- `repository_comments.repo_id` → `repositories.id`  
- `repository_versions.repo_id` → `repositories.id`

### Benefits
- **Referential Integrity**: Prevents orphaned records
- **Automatic Cleanup**: Related data is automatically deleted when repository is removed
- **Data Consistency**: Ensures all references point to valid repositories

## 3. Data Validation

### Overview
Comprehensive validation using Pydantic models before any database insertion.

### Validation Models
- `RepositoryModel` - Repository data validation
- `RepositoryHistoryModel` - History record validation
- `RepositoryCommentModel` - Comment validation
- `RepositoryVersionModel` - Version validation

### Key Validations

#### Repository Validation
- **ID Format**: Must be in `owner/repo` format
- **URL Format**: Must be valid GitHub URL
- **Numeric Fields**: Stars, forks, issues, commits must be ≥ 0
- **Timestamps**: Must be valid ISO format
- **Required Fields**: ID, name, URL are mandatory

#### Comment Validation
- **Non-empty Content**: Comments cannot be empty or whitespace-only
- **Author Validation**: Author name cannot be empty
- **Repository Reference**: Must reference valid repository

#### Version Validation
- **Version Number**: Cannot be empty, must contain valid characters
- **Date Format**: Release dates must be valid ISO format
- **Unique Constraint**: Version numbers must be unique per repository

### Usage
```python
from nuggit.util.validation import validate_repository_data, ValidationError

try:
    validated_data = validate_repository_data(raw_data)
    # Data is safe to insert
except ValidationError as e:
    # Handle validation errors
    print(f"Validation failed: {e}")
```

## 4. Optimistic Locking

### Overview
Prevents concurrent modification conflicts using version numbers.

### Implementation
- **Version Column**: Each repository has a `version` integer field
- **Automatic Increment**: Version increments on every update
- **Conflict Detection**: Updates fail if expected version doesn't match current version

### Usage
```python
from nuggit.util.db import update_repository_fields, OptimisticLockError

try:
    # Update with version check
    success = update_repository_fields(
        repo_id='owner/repo',
        fields={'stars': 150},
        expected_version=1  # Must match current version
    )
except OptimisticLockError:
    # Handle concurrent modification
    print("Repository was modified by another process")
```

### Benefits
- **Conflict Prevention**: Prevents lost updates in concurrent scenarios
- **Data Consistency**: Ensures updates are based on current state
- **Graceful Handling**: Applications can detect and handle conflicts appropriately

## 5. Database Schema Constraints

### Table-Level Constraints
All tables include comprehensive CHECK constraints:

#### Repositories Table
```sql
id TEXT PRIMARY KEY CHECK(length(id) > 0 AND id LIKE '%/%'),
name TEXT NOT NULL CHECK(length(name) > 0),
url TEXT NOT NULL CHECK(url LIKE 'https://github.com/%' OR url LIKE 'http://github.com/%'),
stars INTEGER DEFAULT 0 CHECK(stars >= 0),
forks INTEGER DEFAULT 0 CHECK(forks >= 0),
issues INTEGER DEFAULT 0 CHECK(issues >= 0),
commits INTEGER DEFAULT 0 CHECK(commits >= 0),
version INTEGER DEFAULT 1 CHECK(version > 0)
```

#### Comments Table
```sql
comment TEXT NOT NULL CHECK(length(trim(comment)) > 0),
author TEXT DEFAULT 'Anonymous' CHECK(length(trim(author)) > 0),
created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL)
```

#### Versions Table
```sql
version_number TEXT NOT NULL CHECK(length(trim(version_number)) > 0),
release_date TEXT CHECK(release_date IS NULL OR date(release_date) IS NOT NULL),
UNIQUE(repo_id, version_number)  -- Prevent duplicate versions
```

## 6. Performance Optimizations

### Indexes
Comprehensive indexing for optimal query performance:

```sql
-- Repository indexes
CREATE INDEX idx_repositories_name ON repositories(name);
CREATE INDEX idx_repositories_stars ON repositories(stars);
CREATE INDEX idx_repositories_last_synced ON repositories(last_synced);
CREATE INDEX idx_repositories_version ON repositories(version);

-- History indexes
CREATE INDEX idx_repository_history_repo_id ON repository_history(repo_id);
CREATE INDEX idx_repository_history_changed_at ON repository_history(changed_at);
CREATE INDEX idx_repository_history_field ON repository_history(field);

-- Comment indexes
CREATE INDEX idx_repository_comments_repo_id ON repository_comments(repo_id);
CREATE INDEX idx_repository_comments_created_at ON repository_comments(created_at);

-- Version indexes
CREATE INDEX idx_repository_versions_repo_id ON repository_versions(repo_id);
CREATE INDEX idx_repository_versions_created_at ON repository_versions(created_at);
```

## 7. Testing

### Test Coverage
Comprehensive test suite covering all data integrity features:

- **Migration Tests**: Schema creation, application, rollback, validation
- **Validation Tests**: Valid/invalid data scenarios for all models
- **Optimistic Locking Tests**: Successful updates, conflict detection
- **Foreign Key Tests**: Valid references, constraint enforcement

### Running Tests
```bash
python -m unittest tests.test_data_integrity -v
```

## 8. Integration

### Database Initialization
The migration system is integrated into the database initialization:

```python
from nuggit.util.db import initialize_database

# Automatically applies migrations
initialize_database()
```

### API Integration
All database operations now include validation:

```python
from nuggit.util.db import insert_or_update_repo
from nuggit.util.validation import ValidationError

try:
    insert_or_update_repo(repo_data)  # Automatically validated
except ValidationError as e:
    # Handle validation errors in API
    raise HTTPException(status_code=400, detail=str(e))
```

## 9. Benefits Achieved

### Data Quality
- **Consistent Format**: All data follows strict validation rules
- **Referential Integrity**: No orphaned or invalid references
- **Type Safety**: Numeric fields cannot have invalid values

### Reliability
- **Concurrent Safety**: Optimistic locking prevents data corruption
- **Schema Evolution**: Migrations enable safe schema changes
- **Rollback Capability**: Can safely revert problematic changes

### Maintainability
- **Version Tracking**: Clear history of all schema changes
- **Automated Validation**: Reduces manual error checking
- **Comprehensive Testing**: Ensures reliability of all features

### Performance
- **Optimized Indexes**: Fast queries on common access patterns
- **Efficient Constraints**: Database-level validation is faster than application-level
- **Minimal Overhead**: Optimistic locking adds minimal performance cost

This implementation provides a robust foundation for data integrity that will scale with the application's growth and ensure data consistency across all operations.

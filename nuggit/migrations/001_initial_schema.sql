-- Name: Initial Schema
-- Dependencies: 
-- Created: 2025-01-19T00:00:00.000000

-- +migrate Up

CREATE TABLE repositories (
    id TEXT PRIMARY KEY CHECK(length(id) > 0 AND id LIKE '%/%'),
    name TEXT NOT NULL CHECK(length(name) > 0),
    description TEXT,
    url TEXT NOT NULL CHECK(url LIKE 'https://github.com/%' OR url LIKE 'http://github.com/%'),
    topics TEXT,
    license TEXT,
    created_at TEXT CHECK(created_at IS NULL OR datetime(created_at) IS NOT NULL),
    updated_at TEXT CHECK(updated_at IS NULL OR datetime(updated_at) IS NOT NULL),
    stars INTEGER DEFAULT 0 CHECK(stars >= 0),
    forks INTEGER DEFAULT 0 CHECK(forks >= 0),
    issues INTEGER DEFAULT 0 CHECK(issues >= 0),
    contributors TEXT,
    commits INTEGER DEFAULT 0 CHECK(commits >= 0),
    last_commit TEXT CHECK(last_commit IS NULL OR datetime(last_commit) IS NOT NULL),
    tags TEXT,
    notes TEXT,
    last_synced TEXT CHECK(last_synced IS NULL OR datetime(last_synced) IS NOT NULL),
    version INTEGER DEFAULT 1 CHECK(version > 0)
);

CREATE TABLE repository_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id TEXT NOT NULL CHECK(length(repo_id) > 0),
    field TEXT NOT NULL CHECK(length(field) > 0),
    old_value TEXT,
    new_value TEXT,
    changed_at TEXT NOT NULL CHECK(datetime(changed_at) IS NOT NULL),
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE TABLE repository_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id TEXT NOT NULL CHECK(length(repo_id) > 0),
    comment TEXT NOT NULL CHECK(length(trim(comment)) > 0),
    author TEXT DEFAULT 'Anonymous' CHECK(length(trim(author)) > 0),
    created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL),
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE TABLE repository_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id TEXT NOT NULL CHECK(length(repo_id) > 0),
    version_number TEXT NOT NULL CHECK(length(trim(version_number)) > 0),
    release_date TEXT CHECK(release_date IS NULL OR date(release_date) IS NOT NULL),
    description TEXT,
    created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL),
    FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE,
    UNIQUE(repo_id, version_number)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories(name);
CREATE INDEX IF NOT EXISTS idx_repositories_stars ON repositories(stars);
CREATE INDEX IF NOT EXISTS idx_repositories_last_synced ON repositories(last_synced);
CREATE INDEX IF NOT EXISTS idx_repositories_version ON repositories(version);
CREATE INDEX IF NOT EXISTS idx_repository_history_repo_id ON repository_history(repo_id);
CREATE INDEX IF NOT EXISTS idx_repository_history_changed_at ON repository_history(changed_at);
CREATE INDEX IF NOT EXISTS idx_repository_history_field ON repository_history(field);
CREATE INDEX IF NOT EXISTS idx_repository_comments_repo_id ON repository_comments(repo_id);
CREATE INDEX IF NOT EXISTS idx_repository_comments_created_at ON repository_comments(created_at);
CREATE INDEX IF NOT EXISTS idx_repository_versions_repo_id ON repository_versions(repo_id);
CREATE INDEX IF NOT EXISTS idx_repository_versions_created_at ON repository_versions(created_at);
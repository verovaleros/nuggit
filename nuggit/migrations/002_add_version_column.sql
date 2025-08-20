-- Name: Add Version Column
-- Dependencies:
-- Created: 2025-08-20T08:35:00.000000

-- +migrate Up

-- Add version column to repositories table with default value of 1
-- This preserves all existing data while adding the new column
ALTER TABLE repositories ADD COLUMN version INTEGER DEFAULT 1 CHECK(version > 0);

-- Update all existing repositories to have version = 1
UPDATE repositories SET version = 1 WHERE version IS NULL;

-- +migrate Down

-- Remove the version column (this will preserve data in other columns)
-- Note: SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
CREATE TABLE repositories_backup AS SELECT 
    id, name, description, url, topics, license, created_at, updated_at, 
    stars, forks, issues, contributors, commits, last_commit, tags, notes, last_synced
FROM repositories;

DROP TABLE repositories;

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
    last_synced TEXT CHECK(last_synced IS NULL OR datetime(last_synced) IS NOT NULL)
);

INSERT INTO repositories SELECT * FROM repositories_backup;
DROP TABLE repositories_backup;

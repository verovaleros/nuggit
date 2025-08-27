-- Name: Add Authentication Tables
-- Dependencies: 001
-- Created: 2025-08-24T00:00:00.000000

-- +migrate Up

-- Users table for authentication and user management
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL CHECK(length(email) > 0 AND email LIKE '%@%'),
    username TEXT UNIQUE NOT NULL CHECK(length(username) >= 3 AND length(username) <= 50),
    password_hash TEXT NOT NULL CHECK(length(password_hash) > 0),
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    first_name TEXT CHECK(first_name IS NULL OR length(trim(first_name)) > 0),
    last_name TEXT CHECK(last_name IS NULL OR length(trim(last_name)) > 0),
    created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL),
    updated_at TEXT NOT NULL CHECK(datetime(updated_at) IS NOT NULL),
    last_login_at TEXT CHECK(last_login_at IS NULL OR datetime(last_login_at) IS NOT NULL)
);

-- Email verification tokens
CREATE TABLE email_verification_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL CHECK(length(token) > 0),
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL CHECK(datetime(expires_at) IS NOT NULL),
    created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL),
    used_at TEXT CHECK(used_at IS NULL OR datetime(used_at) IS NOT NULL),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Password reset tokens
CREATE TABLE password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL CHECK(length(token) > 0),
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL CHECK(datetime(expires_at) IS NOT NULL),
    created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL),
    used_at TEXT CHECK(used_at IS NULL OR datetime(used_at) IS NOT NULL),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User sessions for tracking active sessions
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL CHECK(length(session_id) > 0),
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL CHECK(datetime(expires_at) IS NOT NULL),
    created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL),
    last_accessed_at TEXT NOT NULL CHECK(datetime(last_accessed_at) IS NOT NULL),
    ip_address TEXT,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Add user_id column to repositories table to associate repositories with users
ALTER TABLE repositories ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_verified ON users(is_verified);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_token ON email_verification_tokens(token);
CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_user_id ON email_verification_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_expires_at ON email_verification_tokens(expires_at);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);

CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_active ON user_sessions(is_active);

CREATE INDEX IF NOT EXISTS idx_repositories_user_id ON repositories(user_id);

-- +migrate Down

-- Drop indexes
DROP INDEX IF EXISTS idx_repositories_user_id;
DROP INDEX IF EXISTS idx_user_sessions_is_active;
DROP INDEX IF EXISTS idx_user_sessions_expires_at;
DROP INDEX IF EXISTS idx_user_sessions_user_id;
DROP INDEX IF EXISTS idx_user_sessions_session_id;
DROP INDEX IF EXISTS idx_password_reset_tokens_expires_at;
DROP INDEX IF EXISTS idx_password_reset_tokens_user_id;
DROP INDEX IF EXISTS idx_password_reset_tokens_token;
DROP INDEX IF EXISTS idx_email_verification_tokens_expires_at;
DROP INDEX IF EXISTS idx_email_verification_tokens_user_id;
DROP INDEX IF EXISTS idx_email_verification_tokens_token;
DROP INDEX IF EXISTS idx_users_created_at;
DROP INDEX IF EXISTS idx_users_is_active;
DROP INDEX IF EXISTS idx_users_is_verified;
DROP INDEX IF EXISTS idx_users_username;
DROP INDEX IF EXISTS idx_users_email;

-- Remove user_id column from repositories (SQLite doesn't support DROP COLUMN directly)
-- This would require recreating the table in a real rollback scenario

-- Drop tables
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS password_reset_tokens;
DROP TABLE IF EXISTS email_verification_tokens;
DROP TABLE IF EXISTS users;

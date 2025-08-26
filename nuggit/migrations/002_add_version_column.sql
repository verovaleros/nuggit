-- Name: Add Version Column
-- Dependencies:
-- Created: 2025-08-20T08:35:00.000000

-- +migrate Up

-- Note: The version column is already included in migration 001 (Initial Schema)
-- This migration is kept for compatibility but performs no operations
-- as the version column already exists in the repositories table

-- Check if version column exists and update any NULL values to 1
-- This is safe to run even if all records already have version = 1
UPDATE repositories SET version = 1 WHERE version IS NULL;

-- +migrate Down

-- SAFETY NOTE: This migration is now a no-op since the version column
-- is already included in migration 001. Rolling back this migration
-- would be dangerous and is not supported.
--
-- If rollback is absolutely necessary, it should be done manually
-- with proper data backup procedures.

-- No rollback operations - this migration is kept for compatibility only

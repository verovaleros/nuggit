"""
Database migration system for Nuggit.

This module provides a comprehensive migration system that handles:
- Schema versioning and tracking
- Forward and backward migrations
- Automatic migration discovery and execution
- Data integrity validation
- Rollback capabilities
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json

from nuggit.util.timezone import utc_now_iso, now_utc

logger = logging.getLogger(__name__)

# Migration directory
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
MIGRATIONS_DIR.mkdir(exist_ok=True)

@dataclass
class Migration:
    """Represents a database migration."""
    version: str
    name: str
    up_sql: str
    down_sql: str
    checksum: str
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class MigrationError(Exception):
    """Base exception for migration errors."""
    pass


class MigrationManager:
    """Manages database migrations with version tracking and rollback capabilities."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.migrations: Dict[str, Migration] = {}
        self._ensure_migration_table()
        self._load_migrations()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with migration-specific settings."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _ensure_migration_table(self):
        """Create the migration tracking table if it doesn't exist."""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    execution_time_ms INTEGER,
                    rollback_sql TEXT
                )
            """)
            
            # Create index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at 
                ON schema_migrations(applied_at)
            """)
    
    def _load_migrations(self):
        """Load all migration files from the migrations directory."""
        self.migrations.clear()
        
        for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            try:
                migration = self._parse_migration_file(migration_file)
                self.migrations[migration.version] = migration
                logger.debug(f"Loaded migration {migration.version}: {migration.name}")
            except Exception as e:
                logger.error(f"Failed to load migration {migration_file}: {e}")
                raise MigrationError(f"Invalid migration file {migration_file}: {e}")
    
    def _parse_migration_file(self, file_path: Path) -> Migration:
        """Parse a migration file and extract metadata and SQL."""
        content = file_path.read_text(encoding='utf-8')
        
        # Extract version from filename (e.g., "001_initial_schema.sql" -> "001")
        version = file_path.stem.split('_')[0]
        
        # Parse migration metadata from comments
        lines = content.split('\n')
        name = ""
        dependencies = []
        up_sql = ""
        down_sql = ""
        
        in_up_section = False
        in_down_section = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('-- Name:'):
                name = line[8:].strip()
            elif line.startswith('-- Dependencies:'):
                deps_str = line[16:].strip()
                if deps_str:
                    dependencies = [d.strip() for d in deps_str.split(',')]
            elif line == '-- +migrate Up':
                in_up_section = True
                in_down_section = False
            elif line == '-- +migrate Down':
                in_up_section = False
                in_down_section = True
            elif in_up_section and not line.startswith('--'):
                up_sql += line + '\n'
            elif in_down_section and not line.startswith('--'):
                down_sql += line + '\n'
        
        if not name:
            name = file_path.stem.replace('_', ' ').title()
        
        # Calculate checksum for integrity verification
        checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        return Migration(
            version=version,
            name=name,
            up_sql=up_sql.strip(),
            down_sql=down_sql.strip(),
            checksum=checksum,
            dependencies=dependencies
        )
    
    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get list of applied migrations from the database."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT version, name, checksum, applied_at, execution_time_ms
                FROM schema_migrations
                ORDER BY applied_at
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of migrations that haven't been applied yet."""
        applied_versions = {m['version'] for m in self.get_applied_migrations()}
        pending = []
        
        for version in sorted(self.migrations.keys()):
            if version not in applied_versions:
                migration = self.migrations[version]
                # Check if dependencies are satisfied
                for dep in migration.dependencies:
                    if dep not in applied_versions:
                        raise MigrationError(
                            f"Migration {version} depends on {dep} which is not applied"
                        )
                pending.append(migration)
        
        return pending
    
    def apply_migration(self, migration: Migration) -> float:
        """Apply a single migration and record it."""
        logger.info(f"Applying migration {migration.version}: {migration.name}")
        
        start_time = now_utc()
        
        with self.get_connection() as conn:
            # Verify migration hasn't been applied
            cursor = conn.execute(
                "SELECT version FROM schema_migrations WHERE version = ?",
                (migration.version,)
            )
            if cursor.fetchone():
                raise MigrationError(f"Migration {migration.version} already applied")
            
            # Execute the migration SQL
            try:
                # Split SQL into individual statements
                statements = [s.strip() for s in migration.up_sql.split(';') if s.strip()]
                for statement in statements:
                    conn.execute(statement)
                
                # Record the migration
                execution_time = (now_utc() - start_time).total_seconds() * 1000
                conn.execute("""
                    INSERT INTO schema_migrations 
                    (version, name, checksum, applied_at, execution_time_ms, rollback_sql)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    utc_now_iso(),
                    int(execution_time),
                    migration.down_sql
                ))
                
                logger.info(f"Migration {migration.version} applied successfully in {execution_time:.2f}ms")
                return execution_time
                
            except Exception as e:
                logger.error(f"Failed to apply migration {migration.version}: {e}")
                raise MigrationError(f"Migration {migration.version} failed: {e}")
    
    def rollback_migration(self, version: str) -> float:
        """Rollback a specific migration."""
        logger.info(f"Rolling back migration {version}")
        
        start_time = now_utc()
        
        with self.get_connection() as conn:
            # Get the migration record
            cursor = conn.execute(
                "SELECT rollback_sql FROM schema_migrations WHERE version = ?",
                (version,)
            )
            row = cursor.fetchone()
            if not row:
                raise MigrationError(f"Migration {version} not found in applied migrations")
            
            rollback_sql = row['rollback_sql']
            if not rollback_sql:
                raise MigrationError(f"Migration {version} has no rollback SQL")
            
            try:
                # Execute rollback SQL
                statements = [s.strip() for s in rollback_sql.split(';') if s.strip()]
                for statement in statements:
                    conn.execute(statement)
                
                # Remove migration record
                conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
                
                execution_time = (now_utc() - start_time).total_seconds() * 1000
                logger.info(f"Migration {version} rolled back successfully in {execution_time:.2f}ms")
                return execution_time
                
            except Exception as e:
                logger.error(f"Failed to rollback migration {version}: {e}")
                raise MigrationError(f"Rollback of migration {version} failed: {e}")
    
    def migrate(self, target_version: Optional[str] = None) -> List[str]:
        """Apply all pending migrations up to target version."""
        pending = self.get_pending_migrations()
        
        if target_version:
            # Filter to only migrations up to target version
            pending = [m for m in pending if m.version <= target_version]
        
        applied_versions = []
        
        for migration in pending:
            try:
                self.apply_migration(migration)
                applied_versions.append(migration.version)
            except Exception as e:
                logger.error(f"Migration failed at {migration.version}: {e}")
                raise
        
        if applied_versions:
            logger.info(f"Applied {len(applied_versions)} migrations: {', '.join(applied_versions)}")
        else:
            logger.info("No pending migrations to apply")
        
        return applied_versions
    
    def rollback_to(self, target_version: str) -> List[str]:
        """Rollback migrations to a specific version."""
        applied = self.get_applied_migrations()
        to_rollback = [m for m in reversed(applied) if m['version'] > target_version]
        
        rolled_back = []
        
        for migration in to_rollback:
            try:
                self.rollback_migration(migration['version'])
                rolled_back.append(migration['version'])
            except Exception as e:
                logger.error(f"Rollback failed at {migration['version']}: {e}")
                raise
        
        if rolled_back:
            logger.info(f"Rolled back {len(rolled_back)} migrations: {', '.join(rolled_back)}")
        else:
            logger.info("No migrations to rollback")
        
        return rolled_back
    
    def validate_migrations(self) -> List[str]:
        """Validate applied migrations against current migration files."""
        issues = []
        applied = {m['version']: m for m in self.get_applied_migrations()}
        
        for version, applied_migration in applied.items():
            if version not in self.migrations:
                issues.append(f"Applied migration {version} not found in migration files")
                continue
            
            current_migration = self.migrations[version]
            if applied_migration['checksum'] != current_migration.checksum:
                issues.append(f"Migration {version} checksum mismatch - file may have been modified")
        
        return issues
    
    def get_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        issues = self.validate_migrations()
        
        return {
            'applied_count': len(applied),
            'pending_count': len(pending),
            'total_migrations': len(self.migrations),
            'current_version': applied[-1]['version'] if applied else None,
            'latest_available': max(self.migrations.keys()) if self.migrations else None,
            'issues': issues,
            'applied_migrations': applied,
            'pending_migrations': [
                {'version': m.version, 'name': m.name} for m in pending
            ]
        }


def create_migration(name: str, up_sql: str, down_sql: str, dependencies: List[str] = None) -> Path:
    """Create a new migration file."""
    if dependencies is None:
        dependencies = []
    
    # Generate version number based on timestamp
    version = now_utc().strftime("%Y%m%d%H%M%S")
    
    # Sanitize name for filename
    safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in name.lower())
    filename = f"{version}_{safe_name}.sql"
    
    content = f"""-- Name: {name}
-- Dependencies: {', '.join(dependencies) if dependencies else ''}
-- Created: {utc_now_iso()}

-- +migrate Up
{up_sql}

-- +migrate Down
{down_sql}
"""
    
    file_path = MIGRATIONS_DIR / filename
    file_path.write_text(content, encoding='utf-8')
    
    logger.info(f"Created migration {version}: {name}")
    return file_path

#!/usr/bin/env python3
"""
Database migration CLI tool for Nuggit.

This tool provides command-line interface for managing database migrations:
- Apply pending migrations
- Rollback migrations
- Check migration status
- Create new migrations
- Validate migration integrity
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

# Add the parent directory to the path so we can import nuggit modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nuggit.util.migrations import MigrationManager, MigrationError, create_migration
from nuggit.util.db import DB_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_status(args):
    """Show migration status."""
    try:
        manager = MigrationManager(DB_PATH)
        status = manager.get_status()
        
        print(f"Database: {DB_PATH}")
        print(f"Applied migrations: {status['applied_count']}")
        print(f"Pending migrations: {status['pending_count']}")
        print(f"Total migrations: {status['total_migrations']}")
        print(f"Current version: {status['current_version'] or 'None'}")
        print(f"Latest available: {status['latest_available'] or 'None'}")
        
        if status['issues']:
            print("\n⚠️  Issues found:")
            for issue in status['issues']:
                print(f"  - {issue}")
        
        if status['pending_migrations']:
            print("\n📋 Pending migrations:")
            for migration in status['pending_migrations']:
                print(f"  - {migration['version']}: {migration['name']}")
        
        if status['applied_migrations']:
            print("\n✅ Applied migrations:")
            for migration in status['applied_migrations'][-5:]:  # Show last 5
                print(f"  - {migration['version']}: {migration['name']} ({migration['applied_at']})")
            
            if len(status['applied_migrations']) > 5:
                print(f"  ... and {len(status['applied_migrations']) - 5} more")
                
    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        return 1
    
    return 0


def cmd_migrate(args):
    """Apply pending migrations."""
    try:
        manager = MigrationManager(DB_PATH)
        
        if args.target:
            print(f"Migrating to version {args.target}...")
            applied = manager.migrate(args.target)
        else:
            print("Applying all pending migrations...")
            applied = manager.migrate()
        
        if applied:
            print(f"✅ Successfully applied {len(applied)} migrations:")
            for version in applied:
                print(f"  - {version}")
        else:
            print("✅ No pending migrations to apply")
            
    except MigrationError as e:
        logger.error(f"Migration failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return 1
    
    return 0


def cmd_rollback(args):
    """Rollback migrations."""
    if not args.target:
        logger.error("Target version is required for rollback")
        return 1
    
    try:
        manager = MigrationManager(DB_PATH)
        
        print(f"Rolling back to version {args.target}...")
        rolled_back = manager.rollback_to(args.target)
        
        if rolled_back:
            print(f"✅ Successfully rolled back {len(rolled_back)} migrations:")
            for version in rolled_back:
                print(f"  - {version}")
        else:
            print("✅ No migrations to rollback")
            
    except MigrationError as e:
        logger.error(f"Rollback failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during rollback: {e}")
        return 1
    
    return 0


def cmd_validate(args):
    """Validate migration integrity."""
    try:
        manager = MigrationManager(DB_PATH)
        issues = manager.validate_migrations()
        
        if issues:
            print("❌ Migration validation failed:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("✅ All migrations are valid")
            return 0
            
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


def cmd_create(args):
    """Create a new migration."""
    if not args.name:
        logger.error("Migration name is required")
        return 1
    
    try:
        # Get SQL content from user
        print("Enter the UP SQL (press Ctrl+D when done):")
        up_sql_lines = []
        try:
            while True:
                line = input()
                up_sql_lines.append(line)
        except EOFError:
            pass
        
        up_sql = '\n'.join(up_sql_lines).strip()
        
        if not up_sql:
            logger.error("UP SQL cannot be empty")
            return 1
        
        print("\nEnter the DOWN SQL (press Ctrl+D when done):")
        down_sql_lines = []
        try:
            while True:
                line = input()
                down_sql_lines.append(line)
        except EOFError:
            pass
        
        down_sql = '\n'.join(down_sql_lines).strip()
        
        if not down_sql:
            logger.error("DOWN SQL cannot be empty")
            return 1
        
        # Parse dependencies
        dependencies = []
        if args.depends:
            dependencies = [dep.strip() for dep in args.depends.split(',')]
        
        # Create migration
        file_path = create_migration(args.name, up_sql, down_sql, dependencies)
        print(f"✅ Created migration: {file_path}")
        
    except KeyboardInterrupt:
        print("\n❌ Migration creation cancelled")
        return 1
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        return 1
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Nuggit Database Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                    # Show migration status
  %(prog)s migrate                   # Apply all pending migrations
  %(prog)s migrate --target 002      # Migrate to specific version
  %(prog)s rollback --target 001     # Rollback to specific version
  %(prog)s validate                  # Validate migration integrity
  %(prog)s create --name "add_index" # Create new migration
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Apply migrations')
    migrate_parser.add_argument(
        '--target', '-t',
        help='Target version to migrate to (default: latest)'
    )
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migrations')
    rollback_parser.add_argument(
        '--target', '-t', required=True,
        help='Target version to rollback to'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate migrations')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument(
        '--name', '-n', required=True,
        help='Migration name'
    )
    create_parser.add_argument(
        '--depends', '-d',
        help='Comma-separated list of dependency versions'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    command_map = {
        'status': cmd_status,
        'migrate': cmd_migrate,
        'rollback': cmd_rollback,
        'validate': cmd_validate,
        'create': cmd_create,
    }
    
    return command_map[args.command](args)


if __name__ == '__main__':
    sys.exit(main())

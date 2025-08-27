"""
Database backup and restore utilities for Nuggit.

This module provides comprehensive backup and restore functionality to prevent data loss.
"""

import os
import shutil
import sqlite3
import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from nuggit.util.timezone import utc_now_iso
from nuggit.util.db import get_connection, DB_PATH

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)


def create_backup(backup_name: Optional[str] = None, compress: bool = True) -> str:
    """
    Create a backup of the database.
    
    Args:
        backup_name: Optional custom name for the backup
        compress: Whether to compress the backup file
        
    Returns:
        str: Path to the created backup file
    """
    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"nuggit_backup_{timestamp}"
    
    backup_path = BACKUP_DIR / f"{backup_name}.db"
    
    try:
        # Create a backup using SQLite's backup API
        with sqlite3.connect(DB_PATH) as source_conn:
            with sqlite3.connect(backup_path) as backup_conn:
                source_conn.backup(backup_conn)
        
        logger.info(f"Database backup created: {backup_path}")
        
        # Optionally compress the backup
        if compress:
            compressed_path = backup_path.with_suffix('.db.gz')
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed backup
            backup_path.unlink()
            backup_path = compressed_path
            logger.info(f"Backup compressed: {backup_path}")
        
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise


def restore_backup(backup_path: str) -> bool:
    """
    Restore database from a backup file.
    
    Args:
        backup_path: Path to the backup file
        
    Returns:
        bool: True if restore was successful
    """
    backup_file = Path(backup_path)
    
    if not backup_file.exists():
        logger.error(f"Backup file not found: {backup_path}")
        return False
    
    try:
        # Create a backup of current database before restore
        current_backup = create_backup("pre_restore_backup", compress=False)
        logger.info(f"Created backup of current database: {current_backup}")
        
        # Handle compressed backups
        if backup_file.suffix == '.gz':
            temp_path = backup_file.with_suffix('')
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_file = temp_path
        
        # Restore the backup
        shutil.copy2(backup_file, DB_PATH)
        
        # Clean up temporary file if created
        if backup_file.name.endswith('.db') and backup_file.parent == BACKUP_DIR:
            if backup_file != Path(backup_path):  # Only remove if it's a temp file
                backup_file.unlink()
        
        logger.info(f"Database restored from: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        return False


def export_data_json(output_path: Optional[str] = None) -> str:
    """
    Export all database data to JSON format.
    
    Args:
        output_path: Optional path for the export file
        
    Returns:
        str: Path to the exported JSON file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = BACKUP_DIR / f"nuggit_export_{timestamp}.json"
    
    try:
        data = {}
        
        with get_connection() as conn:
            # Get all table names
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Export each table
            for table in tables:
                cursor = conn.execute(f"SELECT * FROM {table}")
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                
                data[table] = {
                    'columns': columns,
                    'rows': [dict(zip(columns, row)) for row in rows]
                }
        
        # Add metadata
        data['_metadata'] = {
            'export_time': utc_now_iso(),
            'version': '1.0',
            'total_tables': len(tables),
            'total_repositories': len(data.get('repositories', {}).get('rows', []))
        }
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        
        logger.info(f"Data exported to JSON: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        raise


def import_data_json(json_path: str) -> bool:
    """
    Import data from JSON export.
    
    Args:
        json_path: Path to the JSON export file
        
    Returns:
        bool: True if import was successful
    """
    json_file = Path(json_path)
    
    if not json_file.exists():
        logger.error(f"JSON file not found: {json_path}")
        return False
    
    try:
        # Create backup before import
        backup_path = create_backup("pre_import_backup", compress=False)
        logger.info(f"Created backup before import: {backup_path}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        with get_connection() as conn:
            # Clear existing data (optional - could be made configurable)
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                if table in data and table != '_metadata':
                    conn.execute(f"DELETE FROM {table}")
            
            # Import data
            for table_name, table_data in data.items():
                if table_name.startswith('_'):
                    continue
                
                if table_name not in tables:
                    logger.warning(f"Table {table_name} not found in current schema, skipping")
                    continue
                
                rows = table_data.get('rows', [])
                if not rows:
                    continue
                
                # Get column names from first row
                columns = list(rows[0].keys())
                placeholders = ', '.join(['?' for _ in columns])
                column_names = ', '.join(columns)
                
                insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
                
                for row in rows:
                    values = [row.get(col) for col in columns]
                    conn.execute(insert_sql, values)
        
        logger.info(f"Data imported from JSON: {json_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import data: {e}")
        return False


def list_backups() -> List[Dict[str, Any]]:
    """
    List all available backups.
    
    Returns:
        List of backup information dictionaries
    """
    backups = []
    
    if not BACKUP_DIR.exists():
        return backups
    
    for backup_file in BACKUP_DIR.glob("*.db*"):
        try:
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size_bytes': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'compressed': backup_file.suffix == '.gz'
            })
        except Exception as e:
            logger.warning(f"Could not get info for backup {backup_file}: {e}")
    
    # Sort by creation time, newest first
    backups.sort(key=lambda x: x['created'], reverse=True)
    return backups


def auto_backup() -> Optional[str]:
    """
    Create an automatic backup with timestamp.
    
    Returns:
        str: Path to created backup, or None if failed
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = create_backup(f"auto_{timestamp}", compress=True)
        
        # Keep only last 10 auto backups
        auto_backups = [b for b in list_backups() if b['name'].startswith('auto_')]
        if len(auto_backups) > 10:
            for old_backup in auto_backups[10:]:
                try:
                    Path(old_backup['path']).unlink()
                    logger.info(f"Removed old backup: {old_backup['name']}")
                except Exception as e:
                    logger.warning(f"Could not remove old backup {old_backup['name']}: {e}")
        
        return backup_path
        
    except Exception as e:
        logger.error(f"Auto backup failed: {e}")
        return None


def verify_backup(backup_path: str) -> bool:
    """
    Verify that a backup file is valid.
    
    Args:
        backup_path: Path to the backup file
        
    Returns:
        bool: True if backup is valid
    """
    backup_file = Path(backup_path)
    
    if not backup_file.exists():
        return False
    
    try:
        # Handle compressed backups
        if backup_file.suffix == '.gz':
            temp_path = backup_file.with_suffix('')
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            test_file = temp_path
        else:
            test_file = backup_file
        
        # Try to open and query the database
        with sqlite3.connect(test_file) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master")
            cursor.fetchone()
        
        # Clean up temp file
        if test_file != backup_file:
            test_file.unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"Backup verification failed for {backup_path}: {e}")
        return False

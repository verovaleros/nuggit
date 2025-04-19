#!/usr/bin/env python3
"""
Script to migrate existing repository notes to the new comments system.
This script should be run once after upgrading to the new comments functionality.
"""

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nuggit.util.db import get_connection, add_comment

def migrate_notes_to_comments():
    """
    Migrate existing notes from repositories table to repository_comments table.
    """
    print("Starting migration of notes to comments...")
    
    migrated_count = 0
    empty_notes_count = 0
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all repositories with non-empty notes
            cursor.execute("SELECT id, notes FROM repositories WHERE notes IS NOT NULL AND notes != ''")
            repos_with_notes = cursor.fetchall()
            
            print(f"Found {len(repos_with_notes)} repositories with notes.")
            
            # For each repository with notes
            for repo_id, notes in repos_with_notes:
                if notes and notes.strip():
                    # Add the notes as a comment
                    comment_id = add_comment(
                        repo_id=repo_id,
                        comment=f"Migrated from notes:\n\n{notes}",
                        author="System Migration"
                    )
                    
                    print(f"Migrated notes for repository {repo_id} to comment ID {comment_id}")
                    migrated_count += 1
                else:
                    empty_notes_count += 1
            
            # Clear the notes field for all repositories
            cursor.execute("UPDATE repositories SET notes = '' WHERE notes IS NOT NULL AND notes != ''")
            
            print(f"Migration complete. Migrated {migrated_count} notes to comments.")
            print(f"Found {empty_notes_count} repositories with empty notes (not migrated).")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = migrate_notes_to_comments()
    sys.exit(0 if success else 1)

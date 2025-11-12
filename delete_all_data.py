#!/usr/bin/env python3
"""
Delete all data from PinPoint database (preserves structure)

This script will:
1. Show current row counts for all tables
2. Ask for confirmation
3. Delete all data using TRUNCATE CASCADE
4. Show final row counts to verify deletion
"""
import sys
import os

# Fix encoding for Windows console
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")

from sqlalchemy import text
from app.database import engine

def get_row_counts():
    """Get row count for each table"""
    tables = [
        'users',
        'encrypted_notes',
        'encryption_keys',
        'devices',
        'sync_events',
        'subscription_events',
        'fcm_tokens',
        'admin_audit_logs'
    ]

    counts = {}
    with engine.connect() as conn:
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.scalar()

    return counts

def delete_all_data():
    """Delete all data from all tables"""
    sql = """
    -- Disable triggers temporarily
    SET session_replication_role = 'replica';

    -- Delete data from all tables
    TRUNCATE TABLE admin_audit_logs CASCADE;
    TRUNCATE TABLE fcm_tokens CASCADE;
    TRUNCATE TABLE subscription_events CASCADE;
    TRUNCATE TABLE sync_events CASCADE;
    TRUNCATE TABLE encrypted_notes CASCADE;
    TRUNCATE TABLE encryption_keys CASCADE;
    TRUNCATE TABLE devices CASCADE;
    TRUNCATE TABLE users CASCADE;

    -- Re-enable triggers
    SET session_replication_role = 'origin';
    """

    with engine.begin() as conn:
        # Execute each statement separately
        conn.execute(text("SET session_replication_role = 'replica'"))
        conn.execute(text("TRUNCATE TABLE admin_audit_logs CASCADE"))
        conn.execute(text("TRUNCATE TABLE fcm_tokens CASCADE"))
        conn.execute(text("TRUNCATE TABLE subscription_events CASCADE"))
        conn.execute(text("TRUNCATE TABLE sync_events CASCADE"))
        conn.execute(text("TRUNCATE TABLE encrypted_notes CASCADE"))
        conn.execute(text("TRUNCATE TABLE encryption_keys CASCADE"))
        conn.execute(text("TRUNCATE TABLE devices CASCADE"))
        conn.execute(text("TRUNCATE TABLE users CASCADE"))
        conn.execute(text("SET session_replication_role = 'origin'"))

    print("[OK] All data deleted successfully!")

def main():
    print("=" * 60)
    print("WARNING: DELETE ALL DATA FROM PINPOINT DATABASE")
    print("=" * 60)
    print()

    # Show current counts
    print("Current row counts:")
    print("-" * 40)
    counts_before = get_row_counts()
    total_rows = 0
    for table, count in counts_before.items():
        print(f"  {table:25s} : {count:>6,} rows")
        total_rows += count
    print("-" * 40)
    print(f"  {'TOTAL':25s} : {total_rows:>6,} rows")
    print()

    if total_rows == 0:
        print("[OK] Database is already empty!")
        return

    # Confirmation
    print("WARNING: This will DELETE ALL DATA from the database!")
    print("   - All users will be deleted")
    print("   - All notes will be deleted")
    print("   - All subscriptions will be deleted")
    print("   - All sync history will be deleted")
    print("   - Database structure will be preserved")
    print()

    response = input("Type 'DELETE ALL DATA' to confirm: ")
    if response != 'DELETE ALL DATA':
        print("[CANCELLED] No data was deleted.")
        sys.exit(0)

    print()
    print("Deleting all data...")
    delete_all_data()

    # Verify deletion
    print()
    print("Final row counts:")
    print("-" * 40)
    counts_after = get_row_counts()
    for table, count in counts_after.items():
        status = "[OK]" if count == 0 else "[ERROR]"
        print(f"  {status} {table:25s} : {count:>6,} rows")
    print("-" * 40)

    # Check if any data remains
    remaining = sum(counts_after.values())
    if remaining > 0:
        print()
        print(f"[WARNING] {remaining} rows still remain!")
    else:
        print()
        print("[SUCCESS] All data deleted! Database is clean.")

if __name__ == "__main__":
    main()

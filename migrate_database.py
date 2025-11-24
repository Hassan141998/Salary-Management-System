"""
Database Migration Script for RASS Salary Management System
This adds the new columns to existing database without losing data
"""

import sqlite3
from datetime import datetime


def migrate_database():
    print("=" * 50)
    print("RASS CUISINE - Database Migration")
    print("=" * 50)

    # Connect to database
    conn = sqlite3.connect('rass_salary.db')
    cursor = conn.cursor()

    try:
        print("\n1. Checking existing columns...")

        # Check Employee table columns
        cursor.execute("PRAGMA table_info(employee)")
        employee_columns = [column[1] for column in cursor.fetchall()]
        print(f"   Current Employee columns: {', '.join(employee_columns)}")

        # Add salary_payment_date if missing
        if 'salary_payment_date' not in employee_columns:
            print("\n2. Adding 'salary_payment_date' column to Employee table...")
            cursor.execute("""
                           ALTER TABLE employee
                               ADD COLUMN salary_payment_date DATE
                           """)
            print("   ✅ Added salary_payment_date")
        else:
            print("\n2. ✅ salary_payment_date already exists")

        # Add updated_at if missing
        if 'updated_at' not in employee_columns:
            print("\n3. Adding 'updated_at' column to Employee table...")
            cursor.execute("""
                           ALTER TABLE employee
                               ADD COLUMN updated_at DATETIME
                           """)
            # Set default value for existing rows
            cursor.execute("""
                           UPDATE employee
                           SET updated_at = created_at
                           WHERE updated_at IS NULL
                           """)
            print("   ✅ Added updated_at")
        else:
            print("\n3. ✅ updated_at already exists")

        # Check Transaction table columns
        cursor.execute("PRAGMA table_info(transaction)")
        transaction_columns = [column[1] for column in cursor.fetchall()]
        print(f"\n4. Current Transaction columns: {', '.join(transaction_columns)}")

        # Add time column if missing
        if 'time' not in transaction_columns:
            print("\n5. Adding 'time' column to Transaction table...")
            cursor.execute("""
                           ALTER TABLE transaction
                               ADD COLUMN time TIME
                           """)
            # Set default time for existing transactions (12:00 PM)
            cursor.execute("""
                           UPDATE transaction
                           SET time = '12:00:00'
                           WHERE time IS NULL
                           """)
            print("   ✅ Added time column")
        else:
            print("\n5. ✅ time column already exists")

        # Commit changes
        conn.commit()

        print("\n" + "=" * 50)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("\nYour database has been updated with new columns.")
        print("All existing data has been preserved.")
        print("\nYou can now restart your Flask application:")
        print("   python app.py")
        print("\n")

    except Exception as e:
        print(f"\n❌ ERROR during migration: {e}")
        conn.rollback()
        print("\nMigration failed. Your database is unchanged.")
        print("Please contact support or use Option 1 (Fresh Start)")

    finally:
        conn.close()


if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: Make sure Flask is NOT running!")
    print("Press Ctrl+C now if Flask is still running.\n")

    response = input("Do you want to proceed with migration? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        migrate_database()
    else:
        print("\nMigration cancelled.")
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

print("🔄 Running storage limits migration...\n")

# Read the migration file
with open('migrations/017_add_storage_limits.sql', 'r') as f:
    migration_sql = f.read()

# Connect to database
conn = psycopg2.connect(database_url)
conn.autocommit = False  # Use transactions
cursor = conn.cursor()

try:
    # Execute the entire migration
    print("📝 Executing migration SQL...")
    cursor.execute(migration_sql)

    # Commit the transaction
    conn.commit()
    print("✅ Migration committed successfully!\n")

    # Verify columns were added
    print("🔍 Verifying storage columns exist...")
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name IN ('storage_quota', 'storage_used')
        ORDER BY column_name;
    """)

    columns = cursor.fetchall()
    if columns:
        print("✓ Storage columns added successfully:")
        for col in columns:
            print(f"  • {col[0]}: {col[1]} (default: {col[2]})")
    else:
        print("⚠️  Warning: Could not verify columns")

    # Check how many users now have storage values
    cursor.execute("""
        SELECT
            COUNT(*) as total_users,
            COUNT(storage_quota) as users_with_quota,
            COUNT(storage_used) as users_with_used
        FROM users;
    """)

    stats = cursor.fetchone()
    print(f"\n📊 User storage stats:")
    print(f"  • Total users: {stats[0]}")
    print(f"  • Users with storage_quota: {stats[1]}")
    print(f"  • Users with storage_used: {stats[2]}")

except Exception as e:
    print(f"❌ Error running migration: {e}")
    conn.rollback()
    raise
finally:
    cursor.close()
    conn.close()

print("\n✅ Migration completed successfully!")

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

client = create_client(supabase_url, supabase_key)

print("🔄 Running storage limits migration using Supabase client...\n")

# Since we can't execute raw SQL directly through Supabase Python client,
# we'll execute each statement individually using the PostgREST API

statements = [
    # Add storage_quota column
    """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS storage_quota BIGINT DEFAULT 2147483648;
    """,
    # Add storage_used column
    """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS storage_used BIGINT DEFAULT 0;
    """,
]

print("⚠️  Note: Direct SQL execution through Supabase Python client is limited.")
print("The migration needs to be run directly in the Supabase SQL Editor.\n")

print("📋 Please run the following SQL in your Supabase SQL Editor:")
print("=" * 70)

# Read and display the migration file
with open('migrations/017_add_storage_limits.sql', 'r') as f:
    migration_sql = f.read()
    print(migration_sql)

print("=" * 70)

print("\n📍 To run this migration:")
print("1. Go to your Supabase Dashboard")
print("2. Navigate to the SQL Editor")
print("3. Copy and paste the SQL above")
print("4. Click 'Run'")

print("\n💡 Alternatively, here's a quick check to see if the columns already exist:")

# Check if columns exist
try:
    result = client.table("users").select("id, email, storage_quota, storage_used").limit(1).execute()
    print("\n✅ Storage columns already exist!")
    print(f"   Found user with storage data: {result.data[0] if result.data else 'No users yet'}")
except Exception as e:
    error_msg = str(e)
    if "storage_quota" in error_msg or "storage_used" in error_msg:
        print(f"\n❌ Storage columns do NOT exist yet. Error: {error_msg[:200]}")
        print("\n👆 Please run the SQL migration in Supabase SQL Editor as shown above.")
    else:
        print(f"\n⚠️  Unexpected error: {error_msg}")

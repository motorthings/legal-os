#!/bin/bash
# Apply migration 024 via psql

# Supabase database connection details
DB_PASSWORD="${SUPABASE_DB_PASSWORD}"
DB_HOST="db.iyugbpnxfbhqjxrvmnij.supabase.co"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="postgres"

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ SUPABASE_DB_PASSWORD environment variable is not set"
    echo ""
    echo "To run this migration:"
    echo "1. Get the database password from Supabase Dashboard > Project Settings > Database"
    echo "2. Set it: export SUPABASE_DB_PASSWORD='your-password'"
    echo "3. Run this script again"
    echo ""
    echo "OR apply manually via Supabase SQL Editor:"
    echo "1. Go to https://supabase.com/dashboard/project/iyugbpnxfbhqjxrvmnij/sql"
    echo "2. Paste the contents of migrations/024_system_instruction_document_mappings.sql"
    echo "3. Click 'Run'"
    exit 1
fi

echo "📊 Applying migration 024 to production database"
echo "🔗 Host: $DB_HOST"
echo "="

PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f migrations/024_system_instruction_document_mappings.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration 024 applied successfully!"
else
    echo ""
    echo "❌ Migration failed. Please check the error above."
fi

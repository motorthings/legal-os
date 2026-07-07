#!/bin/bash
# Apply migration 029 - Contract Analysis System

set -e

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
    exit 1
fi

# Extract database connection details from Supabase URL
DB_HOST="db.iyugbpnxfbhqjxrvmnij.supabase.co"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="postgres"

# Get password from environment
export PGPASSWORD="SBPQxRHSy8OMOttZ"

echo "============================================================"
echo "📋 Applying Migration 029: Contract Analysis System"
echo "============================================================"
echo ""

# Apply migration using psql
psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f migrations/029_contract_analysis_system.sql

echo ""
echo "✅ Migration 029 applied successfully!"
echo ""
echo "Created:"
echo "  - contract_analysis table"
echo "  - contract_chat_history table"
echo "  - performance indexes"
echo "  - updated_at trigger"
echo "  - get_contract_stats() function"
echo "  - RLS policies (admin + user)"
echo ""

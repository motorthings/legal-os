#!/bin/bash

ADMIN_TOKEN='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTNkNWZkMi03ZTBkLTRjMmUtOWMzOS1lNjQyM2Q1MTNmZjYiLCJlbWFpbCI6ImlkYnlwYWlnZUBnbWFpbC5jb20iLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJ1c2VyX21ldGFkYXRhIjp7InJvbGUiOiJhZG1pbiJ9LCJpYXQiOjE3NjM0MjI1MzEsImV4cCI6MTc2MzUwODkzMX0.LLNommWGUByVVyRKFxt2143R-vCzW_cF9g5JjzkxWS8'

echo "========================================="
echo "SuperAssistant API Endpoint Tests"
echo "========================================="
echo ""

echo "1. Root Endpoint (GET /):"
curl -s http://localhost:8000/
echo -e "\n"

echo "2. Admin Clients List (GET /api/clients):"
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/clients | python3 -m json.tool 2>/dev/null || curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/clients
echo -e "\n"

echo "3. Storage Info (GET /api/users/storage):"
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/users/storage | python3 -m json.tool 2>/dev/null || curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/users/storage
echo -e "\n"

echo "4. Conversations List (GET /api/conversations):"
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/conversations | python3 -m json.tool 2>/dev/null | head -30 || curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/conversations | head -30
echo -e "\n"

echo "5. Google Drive Status (GET /api/google-drive/status):"
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/google-drive/status | python3 -m json.tool 2>/dev/null || curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/google-drive/status
echo -e "\n"

echo "========================================="
echo "Tests Complete"
echo "========================================="

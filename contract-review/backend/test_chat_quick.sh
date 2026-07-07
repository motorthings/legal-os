#!/bin/bash

ADMIN_TOKEN='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTNkNWZkMi03ZTBkLTRjMmUtOWMzOS1lNjQyM2Q1MTNmZjYiLCJlbWFpbCI6ImlkYnlwYWlnZUBnbWFpbC5jb20iLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJ1c2VyX21ldGFkYXRhIjp7InJvbGUiOiJhZG1pbiJ9LCJpYXQiOjE3NjM0MjI1MzEsImV4cCI6MTc2MzUwODkzMX0.LLNommWGUByVVyRKFxt2143R-vCzW_cF9g5JjzkxWS8'

echo "=== Testing Chat Endpoint ==="
echo ""
echo "Sending chat message..."
curl -s -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, can you help me?",
    "use_knowledge_base": true,
    "max_chunks": 3
  }' | python3 -m json.tool 2>/dev/null | head -50

echo ""
echo "=== Chat Test Complete ==="

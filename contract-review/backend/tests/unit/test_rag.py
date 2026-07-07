import requests
import json

response = requests.post(
    'http://localhost:8000/api/chat',
    json={
        'message': 'what documents are in the knowledge base?',
        'client_id': '4e94bfa4-d02c-4e52-b4d5-f0701f5c320b',
        'use_rag': True,
        'max_chunks': 5
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

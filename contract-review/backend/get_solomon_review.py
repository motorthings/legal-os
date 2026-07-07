import requests
import json
import re

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
EXTRACTION_ID = "5c615335-e299-43c0-b7d8-408ab7763798"

headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

# Get solomon_reviews for this extraction
url = f"{SUPABASE_URL}/rest/v1/solomon_reviews"
params = {
    "extraction_id": f"eq.{EXTRACTION_ID}",
    "select": "*",
    "order": "created_at.desc",
    "limit": 1
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    reviews = response.json()
    if reviews:
        review = reviews[0]
        print("✅ Found solomon_review\n")
        
        # Get generated_instructions
        if 'generated_instructions' in review and review['generated_instructions']:
            instructions = review['generated_instructions']
            
            # Extract functions
            functions = re.findall(r'<function name="([^"]+)"', instructions)
            if functions:
                print(f"📋 Charlie's Configured Functions ({len(functions)} total):")
                for i, f in enumerate(functions, 1):
                    print(f"   {i}. {f}")
                print()
            
            print(f"Instructions length: {len(instructions):,} characters")
            print()
            
            # Also save to a file for reference
            with open('charlie_functions.txt', 'w') as f:
                f.write("Charlie's Functions:\n")
                f.write("=" * 60 + "\n")
                for i, func in enumerate(functions, 1):
                    f.write(f"{i}. {func}\n")
            
            print("✅ Saved functions to charlie_functions.txt")
        else:
            print("⚠️  No generated_instructions found")
            print(f"\nAvailable fields: {list(review.keys())}")
    else:
        print("❌ No solomon_review found for this extraction")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)

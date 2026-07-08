"""Create a Supabase Auth user with admin API."""
import os, sys, json, urllib.request

EMAIL = sys.argv[1] if len(sys.argv) > 1 else "charlie@waifinder.org"
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else "ButtButt"

url = os.environ["SUPABASE_URL"]
service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
anon_key = os.environ["SUPABASE_ANON_KEY"]

data = json.dumps({
    "email": EMAIL,
    "password": PASSWORD,
    "email_confirm": True,
    "user_metadata": {
        "display_name": "Charlie Fuller",
        "role": "partner",
        "client_id": "d3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01"
    }
}).encode()

req = urllib.request.Request(
    f"{url}/auth/v1/admin/users",
    data=data,
    headers={
        "Authorization": f"Bearer {service_key}",
        "apikey": anon_key,
        "Content-Type": "application/json"
    }
)

resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(json.dumps(result, indent=2))
print(f"\nUser created: {result.get('email')} (id: {result.get('id')})")

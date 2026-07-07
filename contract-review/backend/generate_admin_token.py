import os
from datetime import datetime, timedelta, timezone
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

# Admin user details
user_id = "00000000-0000-0000-0000-000000000002"
email = "admin@example.com"
role = "admin"  # Admin role

# JWT configuration
secret = os.getenv("SUPABASE_JWT_SECRET")
if not secret:
    print("ERROR: SUPABASE_JWT_SECRET not found in .env")
    exit(1)

# Token expiration (24 hours)
now = datetime.now(timezone.utc)
exp = now + timedelta(hours=24)

# JWT payload
payload = {
    "sub": user_id,
    "email": email,
    "aud": "authenticated",
    "role": "authenticated",
    "user_metadata": {"role": role},  # Admin role in metadata
    "iat": int(now.timestamp()),
    "exp": int(exp.timestamp())
}

# Generate token
token = jwt.encode(payload, secret, algorithm="HS256")

print("=" * 80)
print("Admin JWT Token Generated")
print("=" * 80)
print()
print(f"User ID: {user_id}")
print(f"Email: {email}")
print(f"Role: {role}")
print(f"Expires: 24 hours from now")
print()
print("Token:")
print(token)
print()
print("=" * 80)
print()
print("To use this token in tests:")
print(f"export TEST_ADMIN_TOKEN='{token}'")
print()
print("=" * 80)

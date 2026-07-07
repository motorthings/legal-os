"""
Generate a test JWT token for testing purposes

This script creates a valid JWT token using the Supabase JWT secret
from the .env file. The token can be used for testing API endpoints.

Usage:
    python3 generate_test_token.py [user_id] [email]

If user_id and email are not provided, uses default test values.

Example:
    python3 generate_test_token.py
    python3 generate_test_token.py "123e4567-e89b-12d3-a456-426614174000" "test@example.com"
"""

import jwt
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_test_token(user_id: str = None, email: str = None, expires_in_hours: int = 24):
    """
    Generate a test JWT token

    Args:
        user_id: User ID (UUID) - if None, uses a default test ID
        email: User email - if None, uses test@example.com
        expires_in_hours: Token expiration time in hours (default: 24)

    Returns:
        str: Encoded JWT token
    """
    # Get JWT secret from environment
    jwt_secret = os.getenv('SUPABASE_JWT_SECRET')

    if not jwt_secret:
        print("❌ Error: SUPABASE_JWT_SECRET not found in environment variables")
        print("Make sure you have a .env file with SUPABASE_JWT_SECRET set")
        sys.exit(1)

    # Use provided values or defaults
    user_id = user_id or "00000000-0000-0000-0000-000000000001"
    email = email or "test@example.com"

    # Calculate expiration
    import time
    now_timestamp = int(time.time())  # Use current Unix timestamp
    exp_timestamp = now_timestamp + (expires_in_hours * 3600)

    # Create JWT payload (mimicking Supabase JWT structure)
    payload = {
        'sub': user_id,  # Subject (user ID)
        'email': email,
        'aud': 'authenticated',  # Audience
        'role': 'authenticated',
        'iat': now_timestamp,  # Issued at (current time)
        'exp': exp_timestamp,  # Expiration
    }

    # Encode the token
    token = jwt.encode(payload, jwt_secret, algorithm='HS256')

    return token


if __name__ == "__main__":
    # Parse command line arguments
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    email = sys.argv[2] if len(sys.argv) > 2 else None

    # Generate token
    token = generate_test_token(user_id, email)

    # Display results
    print("=" * 80)
    print("Test JWT Token Generated")
    print("=" * 80)
    print(f"\nUser ID: {user_id or '00000000-0000-0000-0000-000000000001'}")
    print(f"Email: {email or 'test@example.com'}")
    print(f"Expires: 24 hours from now")
    print(f"\nToken:\n{token}")
    print("\n" + "=" * 80)
    print("\nTo use this token in tests:")
    print(f"export TEST_JWT_TOKEN='{token}'")
    print("\nOr run directly:")
    print(f"TEST_JWT_TOKEN='{token}' python3 test_kb_comprehensive.py")
    print("=" * 80)

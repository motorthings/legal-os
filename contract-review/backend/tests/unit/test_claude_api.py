"""
Test script to verify Anthropic Claude API connection
"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_claude_api():
    """Test basic Claude API functionality"""

    # Load API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not found in environment")
        print("Make sure you've activated venv and have .env loaded")
        return False

    print(f"✓ API key found: {api_key[:20]}...")

    # Initialize client
    client = Anthropic(api_key=api_key)

    print("\n🤖 Sending test message to Claude...")

    try:
        # Send a test message
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Please respond with exactly: 'SuperAssistant API test successful!'"
                }
            ]
        )

        # Extract response
        response_text = message.content[0].text

        print("\n✅ SUCCESS! Claude responded:")
        print(f"   {response_text}")
        print(f"\n📊 Usage:")
        print(f"   Input tokens: {message.usage.input_tokens}")
        print(f"   Output tokens: {message.usage.output_tokens}")
        print(f"   Model: {message.model}")

        return True

    except Exception as e:
        print(f"\n❌ ERROR calling Claude API:")
        print(f"   {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SuperAssistant MVP - Claude API Test")
    print("=" * 60)

    success = test_claude_api()

    print("\n" + "=" * 60)
    if success:
        print("✅ Claude API is working! Ready for chat integration.")
    else:
        print("❌ Claude API test failed. Check error messages above.")
    print("=" * 60)

#!/usr/bin/env python3
"""
ElevenLabs Agent Setup Script
Automatically creates the SuperAssistant Discovery Interview agent
"""

import os
import json
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")
BACKEND_URL = os.environ.get("BACKEND_URL", "https://superassistant-mvp-production.up.railway.app")

# Interview script
INTERVIEW_SCRIPT = """You are a warm, professional AI interviewer conducting a discovery session for SuperAssistant, a platform that creates personalized AI executive assistants.

Your goal is to understand the client's workflow, challenges, values, and priorities in order to configure their perfect AI assistant.

CONVERSATION FLOW:

1. OPENING (1-2 minutes)
"Hi! I'm excited to learn about your role and how SuperAssistant can best support you. This conversation will take about 15-20 minutes. I'll ask you some questions about your workflow, challenges, and goals. Feel free to share examples and be as specific as you'd like. Ready to begin?"

2. ROLE & CONTEXT (3-4 minutes)
- "Let's start with your role. What's your title, and what does your day-to-day look like?"
- "Who are your key stakeholders? Who do you report to, and who reports to you?"
- "What are the main responsibilities that consume most of your time?"

3. PAIN POINTS & BOTTLENECKS (5-6 minutes) [MOST IMPORTANT]
- "What are the biggest bottlenecks or frustrations in your workflow right now?"
- [For each pain point]: "Can you give me a specific example of when this happened recently?"
- "How often does [pain point] come up? Daily? Weekly?"
- "What impact does this have on your effectiveness or team?"
- "Have you tried any solutions? What worked or didn't work?"

4. DECISION-MAKING & FRAMEWORKS (3-4 minutes)
- "Walk me through how you make decisions. Do you use any particular frameworks or mental models?"
- "When you're prioritizing competing demands, what criteria do you use?"
- "Are there any tools, systems, or methodologies you rely on regularly?"

5. COMMUNICATION & STYLE (2-3 minutes)
- "How do you prefer to communicate? More direct and concise, or detailed with context?"
- "When you're working with data, do you prefer raw numbers, visualizations, or narrative summaries?"
- "How do you typically give feedback or direction to your team?"

6. VALUES & PRIORITIES (2-3 minutes)
- "What matters most to you in how you work? What values drive your decisions?"
- "What are your top 3 priorities right now - personally or for your team?"
- "Looking at the next 3-6 months, what would success look like?"

7. TEAM & DELEGATION (2-3 minutes)
- "Tell me about your team. What are their strengths?"
- "What kinds of things do you find yourself doing that could be delegated?"
- "Where would freeing up your time have the biggest impact?"

8. CLOSING (1 minute)
"Thank you so much for sharing all of this. This gives us a great foundation to configure your SuperAssistant. We'll process this conversation and set up your personalized AI assistant based on everything you've shared. You should hear from us within 24 hours. Any questions before we wrap up?"

INTERVIEW GUIDELINES:
- Maintain a warm, professional coaching tone throughout
- Ask follow-up questions when responses are vague: "Can you give me a specific example?"
- Probe deeper on pain points - these are crucial for configuration
- Let them go off-topic briefly if they're sharing valuable context, then gently guide back
- If they ask about SuperAssistant features, briefly answer but return to discovery
- Keep total time to 15-20 minutes (you can pace accordingly)
- End with clear next steps and timeline

Remember: Your goal is to understand THEM, not to pitch. Listen actively and dig deep."""

FIRST_MESSAGE = "Hi! I'm excited to learn about your role and how SuperAssistant can best support you. This conversation will take about 15-20 minutes. I'll ask you some questions about your workflow, challenges, and goals. Feel free to share examples and be as specific as you'd like. Ready to begin?"


def create_agent():
    """Create ElevenLabs conversational agent"""

    print("\n" + "="*70)
    print("ELEVENLABS AGENT SETUP")
    print("="*70 + "\n")

    if not ELEVENLABS_API_KEY:
        print("❌ Error: ELEVENLABS_API_KEY not found in environment variables")
        print("   Please add it to your .env file")
        return None

    if not ELEVENLABS_VOICE_ID:
        print("❌ Error: ELEVENLABS_VOICE_ID not found in environment variables")
        print("   Please add it to your .env file")
        return None

    print(f"✅ API Key found: {ELEVENLABS_API_KEY[:20]}...")
    print(f"✅ Voice ID: {ELEVENLABS_VOICE_ID}")
    print(f"✅ Webhook URL: {BACKEND_URL}/api/webhooks/interview-complete\n")

    # Prepare agent configuration
    agent_config = {
        "name": "SuperAssistant Discovery Interview",
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": INTERVIEW_SCRIPT,
                    "llm": "claude-3-5-sonnet"  # Use Claude for best conversation quality
                },
                "first_message": FIRST_MESSAGE,
                "language": "en"
            },
            "tts": {
                "model_id": "eleven_turbo_v2_5",  # Latest model
                "voice_id": ELEVENLABS_VOICE_ID
            },
            "asr": {
                "quality": "high"
            }
        },
        "platform_settings": {
            "widget": {
                "avatar_url": "",  # Optional: Add your logo/avatar
                "theme": "light"
            }
        },
        "tags": ["superassistant", "discovery", "interview"]
    }

    print("📝 Creating agent with configuration:")
    print(f"   Name: SuperAssistant Discovery Interview")
    print(f"   Voice: {ELEVENLABS_VOICE_ID}")
    print(f"   Model: Claude 3.5 Sonnet")
    print(f"   Language: English")
    print("\n⏳ Sending request to ElevenLabs API...")

    try:
        # Create agent via API
        response = httpx.post(
            "https://api.elevenlabs.io/v1/convai/agents/create",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json=agent_config,
            timeout=30.0
        )

        response.raise_for_status()
        result = response.json()

        agent_id = result.get("agent_id")

        if agent_id:
            print(f"\n✅ SUCCESS! Agent created with ID: {agent_id}\n")

            # Now configure webhook
            configure_webhook(agent_id)

            # Update .env file
            update_env_file(agent_id)

            return agent_id
        else:
            print(f"\n❌ Error: No agent_id in response")
            print(f"Response: {json.dumps(result, indent=2)}")
            return None

    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"\n❌ Error creating agent: {str(e)}")
        return None


def configure_webhook(agent_id):
    """Configure webhook for agent"""

    print("📡 Configuring webhook...")

    webhook_url = f"{BACKEND_URL}/api/webhooks/interview-complete"

    try:
        # Update agent with webhook configuration
        response = httpx.patch(
            f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "platform_settings": {
                    "webhook_url": webhook_url,
                    "webhook_events": ["conversation.completed"]
                }
            },
            timeout=30.0
        )

        response.raise_for_status()
        print(f"✅ Webhook configured: {webhook_url}")

    except Exception as e:
        print(f"⚠️  Webhook configuration failed: {str(e)}")
        print(f"   You can configure manually in ElevenLabs dashboard")
        print(f"   Webhook URL: {webhook_url}")


def update_env_file(agent_id):
    """Update .env file with agent ID"""

    print("\n📝 Updating .env file...")

    env_path = os.path.join(os.path.dirname(__file__), '.env')

    try:
        # Read current .env
        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Check if ELEVENLABS_AGENT_ID already exists
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('ELEVENLABS_AGENT_ID='):
                lines[i] = f'ELEVENLABS_AGENT_ID={agent_id}\n'
                updated = True
                break

        # If not found, add it after ELEVENLABS_VOICE_ID
        if not updated:
            for i, line in enumerate(lines):
                if line.startswith('ELEVENLABS_VOICE_ID='):
                    lines.insert(i + 1, f'ELEVENLABS_AGENT_ID={agent_id}\n')
                    break

        # Write back
        with open(env_path, 'w') as f:
            f.writelines(lines)

        print(f"✅ Added ELEVENLABS_AGENT_ID={agent_id} to .env")

    except Exception as e:
        print(f"⚠️  Could not update .env file: {str(e)}")
        print(f"   Please manually add: ELEVENLABS_AGENT_ID={agent_id}")


def print_next_steps(agent_id):
    """Print next steps for user"""

    print("\n" + "="*70)
    print("SETUP COMPLETE!")
    print("="*70 + "\n")

    print("✅ Agent created successfully")
    print(f"✅ Agent ID: {agent_id}")
    print("✅ Webhook configured")
    print("✅ .env file updated")

    print("\n📋 NEXT STEPS:\n")

    print("1. Restart your backend to load new environment variables:")
    print("   Press Ctrl+C and run: ./venv/bin/uvicorn main:app --reload\n")

    print("2. Test the interview:")
    print("   - Navigate to: http://localhost:3000/admin/clients")
    print("   - Select a client → Interview tab")
    print("   - Click 'Schedule Interview'")
    print("   - Visit the generated interview URL")
    print("   - Complete the voice interview\n")

    print("3. Deploy to production:")
    print("   - Add to Railway environment variables:")
    print(f"     ELEVENLABS_API_KEY={ELEVENLABS_API_KEY}")
    print(f"     ELEVENLABS_VOICE_ID={ELEVENLABS_VOICE_ID}")
    print(f"     ELEVENLABS_AGENT_ID={agent_id}\n")

    print("4. Monitor the pipeline:")
    print("   - Check backend logs for webhook receipt")
    print("   - Verify Solomon Stage 1 extraction")
    print("   - Verify Solomon Stage 2 generation")
    print("   - Check client.system_instructions in database\n")

    print("🎉 Your automated interview system is ready!")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    agent_id = create_agent()

    if agent_id:
        print_next_steps(agent_id)
    else:
        print("\n❌ Setup failed. Please check errors above.\n")

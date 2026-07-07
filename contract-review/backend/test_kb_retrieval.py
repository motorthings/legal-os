#!/usr/bin/env python3
"""
Test script to verify knowledge base retrieval is working
"""
import os
from dotenv import load_dotenv
from database import get_supabase
from document_processor import search_similar_chunks
from system_instructions_loader import get_system_instructions_for_user
from anthropic import Anthropic

load_dotenv()

# Initialize
supabase = get_supabase()
anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Test user
user_id = 'd3ba5354-873a-435a-a36a-853373c4f6e5'

# Get user data
user_result = supabase.table('users').select('*').eq('id', user_id).execute()
if not user_result.data:
    print("❌ User not found")
    exit(1)

user = user_result.data[0]
print(f"✅ Testing for user: {user['name']} ({user['email']})")
print(f"   Client ID: {user['client_id']}\n")

# Test query
test_query = "What can you tell me about the superassistant-mvp project?"
print(f"📝 Test Query: {test_query}\n")

# Test 1: Check system instructions
print("=" * 80)
print("TEST 1: System Instructions")
print("=" * 80)
try:
    system_instructions = get_system_instructions_for_user(user_id, user)
    print(f"✅ System instructions loaded: {len(system_instructions)} characters")

    # Check if it has the updated KB refs
    if "FOR_PAIGE.md" in system_instructions:
        print("✅ Contains reference to FOR_PAIGE.md")
    else:
        print("❌ Missing reference to FOR_PAIGE.md")

    if "README.md" in system_instructions:
        print("✅ Contains reference to README.md")
    else:
        print("❌ Missing reference to README.md")

    # Check for the new guardrail
    if "prioritize information from the knowledge base documents" in system_instructions:
        print("✅ Has updated prioritization guardrail")
    else:
        print("❌ Still has old restrictive guardrail")

except Exception as e:
    print(f"❌ Error loading system instructions: {e}")

print()

# Test 2: Check RAG retrieval
print("=" * 80)
print("TEST 2: RAG Retrieval")
print("=" * 80)
try:
    context_chunks = search_similar_chunks(
        test_query,
        user['client_id'],
        limit=5,
        min_similarity=0.40
    )

    print(f"✅ Retrieved {len(context_chunks)} relevant chunks")
    print()

    if context_chunks:
        for i, chunk in enumerate(context_chunks):
            print(f"Chunk {i+1}:")
            print(f"  Similarity: {chunk['similarity']:.2%}")
            print(f"  Content preview: {chunk['content'][:100]}...")
            print()
    else:
        print("⚠️  No chunks retrieved (similarity threshold may be too high)")

except Exception as e:
    print(f"❌ Error retrieving chunks: {e}")

print()

# Test 3: Full chat request
print("=" * 80)
print("TEST 3: Full Chat Request with RAG")
print("=" * 80)

try:
    # Build context
    if context_chunks:
        context_text = "\n\n".join([
            f"[Source {i+1} - Relevance: {chunk['similarity']:.2f}]:\n{chunk['content']}"
            for i, chunk in enumerate(context_chunks)
        ])
        user_prompt = f"""You have access to the user's knowledge base. Here are the most relevant excerpts related to their question:

<knowledge_base_context>
{context_text}
</knowledge_base_context>

User's question: {test_query}

Instructions:
- Use the knowledge base context above to inform your response
- Quote or reference specific information from the context when relevant
- If the context contains the answer, use it confidently
- If the context is not relevant or doesn't fully answer the question, acknowledge this and provide the best response you can
- Be specific about which parts of your answer come from the knowledge base versus general knowledge"""
    else:
        user_prompt = test_query

    # Call Claude
    message = anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        system=system_instructions,
        messages=[{"role": "user", "content": user_prompt}]
    )

    response_text = message.content[0].text

    print("✅ Response generated successfully\n")
    print("📤 RESPONSE:")
    print("-" * 80)
    print(response_text)
    print("-" * 80)
    print()
    print(f"📊 Tokens used: {message.usage.input_tokens} input, {message.usage.output_tokens} output")
    print(f"📚 Context chunks used: {len(context_chunks)}")

except Exception as e:
    print(f"❌ Error generating response: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

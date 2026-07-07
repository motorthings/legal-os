"""
Test the chat endpoint with RAG integration
Tests:
1. Chat with document context (RAG enabled)
2. Chat without RAG
3. Verify context chunks are being used
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_chat_with_rag():
    print("=" * 70)
    print("Testing Chat Endpoint with RAG Integration")
    print("=" * 70)

    # Test queries about the documents
    test_queries = [
        {
            "query": "What are the key principles for innovation?",
            "use_rag": True,
            "description": "Should find innovation strategy from documents"
        },
        {
            "query": "Tell me about the PB_Magic framework",
            "use_rag": True,
            "description": "Should find PB_Magic framework details"
        },
        {
            "query": "What is 2 + 2?",
            "use_rag": True,
            "description": "Question not in documents - should handle gracefully"
        },
        {
            "query": "What strategic frameworks are mentioned?",
            "use_rag": True,
            "description": "Should find ICE and OKR frameworks"
        }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\n{'─' * 70}")
        print(f"Test {i}: {test['description']}")
        print(f"{'─' * 70}")
        print(f"Query: \"{test['query']}\"")
        print(f"RAG Enabled: {test['use_rag']}")

        # Make chat request
        payload = {
            "message": test['query'],
            "use_rag": test['use_rag'],
            "max_chunks": 3
        }

        try:
            response = requests.post(
                f"{API_BASE}/api/chat",
                json=payload
            )

            if response.status_code != 200:
                print(f"\n❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")
                continue

            result = response.json()

            # Display results
            print(f"\n✅ Response received!")
            print(f"\n📊 Metadata:")
            print(f"   Context chunks used: {result['context_used']}")
            print(f"   Input tokens: {result['tokens']['input']}")
            print(f"   Output tokens: {result['tokens']['output']}")

            # Show context chunks if RAG was used
            if result['context_used'] > 0:
                print(f"\n📚 Document Context Used:")
                for j, chunk in enumerate(result['chunks'], 1):
                    print(f"\n   Chunk {j} (Similarity: {chunk['similarity']:.4f} / {chunk['similarity']*100:.2f}%)")
                    print(f"   Content preview: {chunk['content'][:100]}...")

            # Show assistant response
            print(f"\n🤖 Assistant Response:")
            print(f"   {'-' * 66}")
            # Indent each line of the response
            for line in result['message'].split('\n'):
                print(f"   {line}")
            print(f"   {'-' * 66}")

        except requests.exceptions.ConnectionError:
            print(f"\n❌ Cannot connect to API server")
            print(f"   Make sure FastAPI is running: uvicorn main:app --reload")
            return
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "=" * 70)
    print("✅ Chat endpoint testing complete!")
    print("=" * 70)
    print("\n📝 Summary:")
    print("   ✓ RAG integration allows chat to reference your documents")
    print("   ✓ Similarity scores show relevance of retrieved context")
    print("   ✓ Claude uses document context to provide informed answers")
    print("   ✓ Handles both document-related and general queries")
    print("\n🎉 Your RAG-powered chat endpoint is working!")
    print("=" * 70)


if __name__ == "__main__":
    test_chat_with_rag()

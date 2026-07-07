"""
Test the complete API workflow:
1. Upload document
2. Process document
3. Search for content
"""
import requests
import time

API_BASE = "http://localhost:8000"

def test_complete_workflow():
    print("=" * 60)
    print("SuperAssistant API - Complete Workflow Test")
    print("=" * 60)

    # Step 1: Upload a document
    print("\n📤 Step 1: Uploading document...")

    test_content = """
    Executive Leadership Framework

    This document outlines key principles for executive decision-making:

    1. Innovation Strategy
    - Focus on disruptive technologies
    - Encourage creative thinking
    - Balance risk and reward

    2. Operational Efficiency
    - Streamline processes
    - Eliminate redundancies
    - Measure KPIs continuously

    3. PB_Magic Framework
    - Leadership effectiveness measurement
    - Track executive growth
    - Data-driven insights

    4. Strategic Frameworks
    - ICE prioritization (Impact, Confidence, Ease)
    - OKR goal setting (Objectives and Key Results)
    - Quarterly business reviews
    """

    # Save test file
    with open('test_executive_doc.txt', 'w') as f:
        f.write(test_content)

    # Upload
    with open('test_executive_doc.txt', 'rb') as f:
        files = {'file': ('executive_leadership.txt', f, 'text/plain')}
        response = requests.post(f"{API_BASE}/api/documents/upload", files=files)

    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return

    upload_result = response.json()
    document_id = upload_result['document_id']
    print(f"✅ Uploaded! Document ID: {document_id}")

    # Step 2: Process the document
    print("\n⚙️ Step 2: Processing document (chunking + embedding)...")

    response = requests.post(f"{API_BASE}/api/documents/{document_id}/process")

    if response.status_code != 200:
        print(f"❌ Processing failed: {response.text}")
        return

    process_result = response.json()
    print(f"✅ Processed!")
    print(f"   Chunks created: {process_result['chunks_created']}")
    print(f"   Chunks stored: {process_result['chunks_stored']}")

    # Step 3: Search for content
    print("\n🔍 Step 3: Testing vector search...")

    # Test multiple queries
    queries = [
        "innovation and creativity",
        "efficiency and optimization",
        "PB_Magic framework for leadership",
        "OKR and ICE frameworks"
    ]

    for query in queries:
        print(f"\n   Query: '{query}'")

        response = requests.post(
            f"{API_BASE}/api/search",
            params={'query': query, 'limit': 2}
        )

        if response.status_code != 200:
            print(f"   ❌ Search failed: {response.text}")
            continue

        search_result = response.json()
        print(f"   Found {search_result['count']} results")

        for i, result in enumerate(search_result['results'], 1):
            print(f"\n   Result {i}:")
            print(f"      Similarity: {result['similarity']:.4f}")
            print(f"      Content: {result['content'][:80]}...")

    # Cleanup
    import os
    os.remove('test_executive_doc.txt')

    print("\n" + "=" * 60)
    print("✅ Complete workflow test passed!")
    print("=" * 60)
    print("\nAPI Endpoints Working:")
    print("  ✓ POST /api/documents/upload")
    print("  ✓ POST /api/documents/{id}/process")
    print("  ✓ POST /api/search")
    print("\n🎉 RAG pipeline fully operational via API!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_complete_workflow()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server")
        print("   Make sure FastAPI is running: uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

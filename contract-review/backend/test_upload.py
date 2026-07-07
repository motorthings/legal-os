"""
Test script to verify document upload endpoint
"""
import requests
import os

def test_document_upload():
    """Test uploading a document to the API"""

    # Create a simple test file
    test_content = """
    SuperAssistant Test Document

    This is a test document for verifying the upload pipeline.

    Key Topics:
    - Innovation and efficiency
    - Executive decision-making
    - PB_Magic framework for leadership evaluation
    - ICE and OKR frameworks

    This document will be chunked, embedded, and stored in the vector database
    for retrieval-augmented generation (RAG).
    """

    # Save test file
    test_filename = 'test_document.txt'
    with open(test_filename, 'w') as f:
        f.write(test_content)

    print("=" * 60)
    print("SuperAssistant MVP - Document Upload Test")
    print("=" * 60)
    print(f"\n📄 Created test file: {test_filename}")
    print(f"   Size: {len(test_content)} bytes")

    # Test against local server
    api_url = "http://localhost:8000/api/documents/upload"

    print(f"\n🚀 Uploading to: {api_url}")

    try:
        # Open file and upload
        with open(test_filename, 'rb') as f:
            files = {'file': (test_filename, f, 'text/plain')}
            response = requests.post(api_url, files=files)

        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS! Document uploaded:")
            print(f"   Document ID: {result['document_id']}")
            print(f"   Filename: {result['filename']}")
            print(f"   Storage URL: {result['storage_url']}")
            print(f"   File size: {result['file_size']} bytes")
            print(f"   Message: {result['message']}")

            # Clean up test file
            os.remove(test_filename)
            print(f"\n✓ Cleaned up test file")

            return result['document_id']
        else:
            print(f"\n❌ Upload failed with status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API server")
        print("   Make sure the FastAPI server is running:")
        print("   uvicorn main:app --reload")
        return None
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return None

if __name__ == "__main__":
    document_id = test_document_upload()

    print("\n" + "=" * 60)
    if document_id:
        print("✅ Upload test passed!")
        print(f"   Document ID: {document_id}")
        print("   Next: Process this document (chunking + embeddings)")
    else:
        print("❌ Upload test failed. Check error messages above.")
    print("=" * 60)

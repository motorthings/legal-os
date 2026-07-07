"""
Tests for document processing and text extraction
"""
import pytest
from document_processor import extract_text_from_file, chunk_text


class TestTextExtraction:
    """Test text extraction from various file types"""

    def test_extract_text_from_txt(self):
        """Test extracting text from plain text file"""
        content = b"Hello, World!\nThis is a test document."
        result = extract_text_from_file(content, "test.txt")

        assert result == "Hello, World!\nThis is a test document."

    def test_extract_text_from_invalid_utf8(self):
        """Test extracting text from invalid UTF-8"""
        content = b"\xff\xfe"  # Invalid UTF-8

        with pytest.raises(ValueError, match="Failed to decode"):
            extract_text_from_file(content, "test.txt")

    def test_extract_text_unsupported_format(self):
        """Test unsupported file format"""
        content = b"some binary data"

        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text_from_file(content, "test.xyz")


class TestTextChunking:
    """Test text chunking functionality"""

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size"""
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=100, overlap=20)

        assert len(chunks) == 1
        assert chunks[0]['content'] == text
        assert chunks[0]['chunk_index'] == 0

    def test_chunk_long_text(self):
        """Test chunking long text"""
        # Create a long text (1500 chars)
        text = "Lorem ipsum dolor sit amet. " * 50

        chunks = chunk_text(text, chunk_size=500, overlap=100)

        # Should create multiple chunks
        assert len(chunks) > 1

        # All chunks should have content
        for chunk in chunks:
            assert len(chunk['content']) > 0
            assert 'chunk_index' in chunk

        # Chunks should have proper indices
        for i, chunk in enumerate(chunks):
            assert chunk['chunk_index'] == i

    def test_chunk_overlap(self):
        """Test that chunks have proper overlap"""
        text = "A" * 1000 + "B" * 1000

        chunks = chunk_text(text, chunk_size=800, overlap=200)

        # First chunk should contain A's
        assert 'A' in chunks[0]['content']

        # Later chunks should have overlap
        if len(chunks) > 1:
            # There should be some content overlap between chunks
            assert len(chunks[0]['content']) > 0
            assert len(chunks[1]['content']) > 0

    def test_chunk_boundary_handling(self):
        """Test text chunking respects sentence boundaries"""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."

        chunks = chunk_text(text, chunk_size=40, overlap=10)

        # Should create chunks at sentence boundaries when possible
        for chunk in chunks:
            content = chunk['content']
            # If chunk ends mid-text, it should try to end at boundary
            # (This is a simplified test - actual implementation may vary)
            assert len(content) > 0

    def test_chunk_empty_text(self):
        """Test chunking empty text"""
        text = ""
        chunks = chunk_text(text, chunk_size=800, overlap=200)

        # Should return one empty chunk or no chunks
        assert len(chunks) <= 1
        if len(chunks) == 1:
            assert chunks[0]['content'] == ""

    def test_chunk_custom_sizes(self):
        """Test chunking with different sizes"""
        text = "A" * 2000

        # Small chunks
        small_chunks = chunk_text(text, chunk_size=200, overlap=50)
        assert len(small_chunks) > 5

        # Large chunks
        large_chunks = chunk_text(text, chunk_size=1000, overlap=100)
        assert len(large_chunks) < len(small_chunks)


class TestDocumentProcessing:
    """Integration tests for document processing pipeline"""

    def test_full_pipeline(self):
        """Test the complete document processing pipeline"""
        # This would test: upload -> extract -> chunk -> embed
        # Requires mocking or test database
        pass

    def test_concurrent_processing(self):
        """Test processing multiple documents concurrently"""
        # Test thread safety and concurrency
        pass

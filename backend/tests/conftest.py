"""Shared test fixtures for the Second Brain RAG backend."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set test environment variables before any app imports
os.environ.setdefault("API_KEY", "test-api-key-12345")
os.environ.setdefault("API_KEYS", "test-api-key-12345,second-key-67890")
os.environ.setdefault("GOOGLE_API_KEY", "fake-gemini-key")
os.environ.setdefault("GROQ_API_KEY", "fake-groq-key")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("CACHE_BACKEND", "memory")
os.environ.setdefault("CHROMA_HOST", "localhost")
os.environ.setdefault("CHROMA_PORT", "8001")


@pytest.fixture
def sample_documents():
    """Sample langchain Documents for testing chunking and ingestion."""
    from langchain_core.documents import Document

    return [
        Document(
            page_content="Machine learning is a subset of artificial intelligence that enables "
            "systems to learn from data. Deep learning uses neural networks with multiple layers.",
            metadata={"filename": "ml_intro.pdf", "page_number": 1, "source_type": "pdf"},
        ),
        Document(
            page_content="Python is a high-level programming language widely used in data science. "
            "Libraries like NumPy and Pandas provide powerful data manipulation tools.",
            metadata={"filename": "python_guide.pdf", "page_number": 1, "source_type": "pdf"},
        ),
    ]


@pytest.fixture
def mock_embeddings():
    """Mock embedding vectors (384-dim like all-MiniLM-L6-v2)."""
    import numpy as np

    return [np.random.rand(384).tolist() for _ in range(5)]


@pytest.fixture
def mock_chroma_results():
    """Mock ChromaDB query results."""
    return [
        {
            "text": "Machine learning is a subset of AI.",
            "metadata": {
                "filename": "ml_intro.pdf",
                "page_number": 1,
                "hash": "abc123",
                "parent_id": "parent-uuid-1",
            },
            "score": 0.85,
        },
        {
            "text": "Deep learning uses neural networks.",
            "metadata": {
                "filename": "ml_intro.pdf",
                "page_number": 2,
                "hash": "def456",
                "parent_id": "parent-uuid-2",
            },
            "score": 0.72,
        },
    ]


@pytest.fixture
def mock_bm25_results():
    """Mock BM25 search results."""
    return [
        {"id": "bm25-1", "text": "Neural networks are used in deep learning.", "score": 3.5},
        {"id": "bm25-2", "text": "Machine learning algorithms learn from data.", "score": 2.8},
    ]

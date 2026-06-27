import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import chromadb

from app.rag.vectorstore.chroma_store import add_documents, query, delete_document, list_documents, get_stats

@pytest.fixture
def mock_chroma_client():
    client = chromadb.EphemeralClient()
    with patch("app.rag.vectorstore.chroma_store.get_client", return_value=client):
        yield client
        
@pytest.mark.asyncio
async def test_chroma_store_cycle(mock_chroma_client):
    # 1. Add Documents
    docs = ["Hello world", "This is a test"]
    embeddings = [[0.1, 0.1], [0.2, 0.2]]
    metadatas = [
        {"hash": "hash1", "doc_id": "doc1", "filename": "file1.txt"},
        {"hash": "hash2", "doc_id": "doc1", "filename": "file1.txt"}
    ]
    
    await add_documents(docs, embeddings, metadatas)
    
    # Verify stats
    stats = get_stats()
    assert stats["total_chunks"] == 2
    assert stats["total_docs"] == 1
    
    # 2. Add same documents again (should skip because of same hash/doc_id combination)
    await add_documents(docs, embeddings, metadatas)
    stats = get_stats()
    assert stats["total_chunks"] == 2
    
    # 3. Query
    results = await query([0.1, 0.1], n_results=1, score_threshold=0.5)
    assert len(results) == 1
    assert results[0]["text"] == "Hello world"
    assert results[0]["score"] > 0.9
    
    # 4. List Documents
    doc_list = await list_documents()
    assert len(doc_list) == 1
    assert doc_list[0]["doc_id"] == "doc1"
    assert doc_list[0]["chunk_count"] == 2
    
    # 5. Delete Document
    await delete_document("doc1")
    stats_after = get_stats()
    assert stats_after["total_chunks"] == 0
    assert stats_after["total_docs"] == 0

@pytest.mark.asyncio
async def test_local_embedder():
    from app.rag.embeddings.local_embedder import embed_documents
    with patch("app.rag.embeddings.local_embedder.model") as mock_model:
        mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.1, 0.2], [0.3, 0.4]])
        
        texts = ["Text 1", "Text 2"]
        result1 = await embed_documents(texts)
        assert len(result1) == 2
        assert result1[0] == [0.1, 0.2]

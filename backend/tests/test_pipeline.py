import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.rag.retrievers.hybrid_retriever import reciprocal_rank_fusion, hybrid_search

def test_reciprocal_rank_fusion():
    dense_results = [
        {"id": "doc1", "text": "A"},
        {"id": "doc2", "text": "B"}
    ]
    sparse_results = [
        {"id": "doc2", "text": "B"},
        {"id": "doc3", "text": "C"}
    ]
    
    fused = reciprocal_rank_fusion(dense_results, sparse_results, k=60)
    
    assert len(fused) == 3
    # doc2 should be ranked highest because it appears in both lists
    assert fused[0]["id"] == "doc2"
    
@pytest.mark.asyncio
@patch("app.rag.retrievers.hybrid_retriever.chroma_query", new_callable=AsyncMock)
@patch("app.rag.retrievers.hybrid_retriever.embed_documents", new_callable=AsyncMock)
@patch("app.rag.retrievers.hybrid_retriever.get_bm25_store")
async def test_hybrid_search(mock_get_bm25, mock_embed, mock_chroma):
    mock_embed.return_value = [[0.1, 0.2]]
    mock_chroma.return_value = [{"id": "doc1", "text": "Chroma result"}]
    
    mock_bm25 = MagicMock()
    mock_bm25.search.return_value = [{"id": "doc2", "text": "BM25 result"}]
    mock_get_bm25.return_value = mock_bm25
    
    with patch("app.rag.retrievers.hybrid_retriever.reranker", MagicMock()) as mock_reranker:
        mock_reranker.predict.return_value = [0.9, 0.1]
        
        results = await hybrid_search("test query", top_k=2)
        
        assert len(results) == 2
        # Verify reranking scored doc1 higher (0.9 vs 0.1)
        assert results[0]["id"] == "doc1"
        assert results[0]["rerank_score"] == 0.9

"""Tests for the hybrid retrieval pipeline (RRF fusion and reranking)."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.rag.retrievers.hybrid_retriever import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_basic_fusion(self):
        dense = [
            {"id": "doc1", "text": "Machine learning", "score": 0.9},
            {"id": "doc2", "text": "Deep learning", "score": 0.8},
        ]
        sparse = [
            {"id": "doc2", "text": "Deep learning", "score": 3.5},
            {"id": "doc3", "text": "Neural networks", "score": 2.0},
        ]

        fused = reciprocal_rank_fusion(dense, sparse)

        # doc2 appears in both, should rank highest
        assert fused[0]["id"] == "doc2"
        assert len(fused) == 3  # doc1, doc2, doc3

    def test_empty_inputs(self):
        fused = reciprocal_rank_fusion([], [])
        assert fused == []

    def test_single_source(self):
        dense = [
            {"id": "a", "text": "only dense", "score": 0.9},
        ]
        fused = reciprocal_rank_fusion(dense, [])
        assert len(fused) == 1
        assert fused[0]["id"] == "a"

    def test_no_duplicate_docs_in_output(self):
        dense = [
            {"id": "shared", "text": "same doc", "score": 0.9},
        ]
        sparse = [
            {"id": "shared", "text": "same doc", "score": 5.0},
        ]
        fused = reciprocal_rank_fusion(dense, sparse)
        assert len(fused) == 1

    def test_assigns_ids_from_metadata_hash(self):
        """Documents without explicit id should get id from metadata hash."""
        dense = [
            {"text": "no id doc", "metadata": {"hash": "hash123"}, "score": 0.5},
        ]
        fused = reciprocal_rank_fusion(dense, [])
        assert fused[0]["id"] == "hash123"

    def test_custom_k_parameter(self):
        dense = [{"id": "a", "text": "doc", "score": 0.9}]
        sparse = [{"id": "b", "text": "doc2", "score": 1.0}]

        # With a very large k, scores should be very small but still work
        fused = reciprocal_rank_fusion(dense, sparse, k=1000)
        assert len(fused) == 2

    def test_preserves_document_content(self):
        """Fusion should preserve all original fields in documents."""
        dense = [
            {
                "id": "doc1",
                "text": "Full text content",
                "metadata": {"filename": "test.pdf", "page": 1},
                "score": 0.85,
            }
        ]
        fused = reciprocal_rank_fusion(dense, [])
        assert fused[0]["text"] == "Full text content"
        assert fused[0]["metadata"]["filename"] == "test.pdf"


class TestHybridSearch:
    @pytest.mark.asyncio
    async def test_hybrid_search_combines_sources(
        self, mock_chroma_results, mock_bm25_results
    ):
        with patch(
            "app.rag.retrievers.hybrid_retriever.embed_documents",
            new_callable=AsyncMock,
            return_value=[[0.1] * 384],
        ), patch(
            "app.rag.retrievers.hybrid_retriever.chroma_query",
            new_callable=AsyncMock,
            return_value=mock_chroma_results,
        ), patch(
            "app.rag.retrievers.hybrid_retriever.get_bm25_store"
        ) as mock_bm25_store, patch(
            "app.rag.retrievers.hybrid_retriever.reranker", None
        ):
            mock_store = MagicMock()
            mock_store.search.return_value = mock_bm25_results
            mock_bm25_store.return_value = mock_store

            from app.rag.retrievers.hybrid_retriever import hybrid_search

            results = await hybrid_search("machine learning", top_k=5)

            assert len(results) > 0
            assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_handles_empty_embeddings(self):
        """If embedding fails, should still return BM25 results."""
        with patch(
            "app.rag.retrievers.hybrid_retriever.embed_documents",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.rag.retrievers.hybrid_retriever.get_bm25_store"
        ) as mock_bm25_store, patch(
            "app.rag.retrievers.hybrid_retriever.reranker", None
        ):
            mock_store = MagicMock()
            mock_store.search.return_value = [
                {"id": "bm25-1", "text": "fallback result", "score": 2.0}
            ]
            mock_bm25_store.return_value = mock_store

            from app.rag.retrievers.hybrid_retriever import hybrid_search

            results = await hybrid_search("test query", top_k=3)
            assert len(results) >= 1

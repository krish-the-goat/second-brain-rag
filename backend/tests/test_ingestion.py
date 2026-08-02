"""Tests for the ingestion pipeline."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from langchain_core.documents import Document


class TestIngestionPipeline:
    @pytest.mark.asyncio
    async def test_process_file_pdf(self, tmp_path):
        """Test that PDF ingestion flows through the full pipeline."""
        pdf_path = str(tmp_path / "test.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"fake pdf content")

        mock_docs = [
            Document(
                page_content="Test content from PDF",
                metadata={"filename": "test.pdf", "page_number": 1, "source_type": "pdf"},
            )
        ]

        with patch(
            "app.rag.ingestion.load_pdf", new_callable=AsyncMock, return_value=mock_docs
        ), patch(
            "app.rag.ingestion.chunk_documents",
            return_value=(mock_docs, {"parent-1": "parent text"}),
        ), patch(
            "app.rag.ingestion.embed_documents",
            new_callable=AsyncMock,
            return_value=[[0.1] * 384],
        ), patch(
            "app.rag.ingestion.add_documents", new_callable=AsyncMock
        ), patch(
            "app.rag.ingestion.set_cache", new_callable=AsyncMock
        ) as mock_cache, patch(
            "app.rag.ingestion.get_bm25_store"
        ) as mock_bm25, patch(
            "app.rag.graph.graph_extractor.extract_and_store_graph", new_callable=AsyncMock
        ):
            mock_store = MagicMock()
            mock_store.add_documents = MagicMock()
            mock_store.update_document_metadata = MagicMock()
            mock_bm25.return_value = mock_store

            from app.rag.ingestion import ingestion_pipeline

            await ingestion_pipeline.process_file(
                pdf_path, "test.pdf", "application/pdf", "job-123"
            )

            # Verify job status was set to completed
            mock_cache.assert_any_call("job:job-123", "completed")

    @pytest.mark.asyncio
    async def test_process_file_unsupported_format(self, tmp_path):
        """Unsupported formats should mark the job as failed."""
        txt_path = str(tmp_path / "test.txt")
        with open(txt_path, "w") as f:
            f.write("plain text")

        with patch(
            "app.rag.ingestion.set_cache", new_callable=AsyncMock
        ) as mock_cache:
            from app.rag.ingestion import ingestion_pipeline

            await ingestion_pipeline.process_file(
                txt_path, "test.txt", "text/plain", "job-456"
            )

            # Should be marked as failed
            calls = [str(c) for c in mock_cache.call_args_list]
            assert any("failed" in c for c in calls)

    @pytest.mark.asyncio
    async def test_process_url(self):
        """Test URL ingestion calls the web loader."""
        mock_docs = [
            Document(
                page_content="Web page content",
                metadata={"url": "https://example.com", "source_type": "web"},
            )
        ]

        with patch(
            "app.rag.ingestion.load_web", new_callable=AsyncMock, return_value=mock_docs
        ), patch(
            "app.rag.ingestion.chunk_documents",
            return_value=(mock_docs, {"p1": "parent"}),
        ), patch(
            "app.rag.ingestion.embed_documents",
            new_callable=AsyncMock,
            return_value=[[0.1] * 384],
        ), patch(
            "app.rag.ingestion.add_documents", new_callable=AsyncMock
        ), patch(
            "app.rag.ingestion.set_cache", new_callable=AsyncMock
        ) as mock_cache, patch(
            "app.rag.ingestion.get_bm25_store"
        ) as mock_bm25, patch(
            "app.rag.graph.graph_extractor.extract_and_store_graph", new_callable=AsyncMock
        ):
            mock_store = MagicMock()
            mock_store.add_documents = MagicMock()
            mock_store.update_document_metadata = MagicMock()
            mock_bm25.return_value = mock_store

            from app.rag.ingestion import ingestion_pipeline

            await ingestion_pipeline.process_url("https://example.com", "job-789")

            mock_cache.assert_any_call("job:job-789", "completed")

    @pytest.mark.asyncio
    async def test_cleanup_temp_file_on_success(self, tmp_path):
        """Temp files should be removed after processing."""
        import os

        pdf_path = str(tmp_path / "cleanup_test.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"content")

        mock_docs = [
            Document(page_content="text", metadata={"filename": "f.pdf", "source_type": "pdf"})
        ]

        with patch(
            "app.rag.ingestion.load_pdf", new_callable=AsyncMock, return_value=mock_docs
        ), patch(
            "app.rag.ingestion.chunk_documents",
            return_value=(mock_docs, {"p": "text"}),
        ), patch(
            "app.rag.ingestion.embed_documents",
            new_callable=AsyncMock,
            return_value=[[0.1] * 384],
        ), patch(
            "app.rag.ingestion.add_documents", new_callable=AsyncMock
        ), patch(
            "app.rag.ingestion.set_cache", new_callable=AsyncMock
        ), patch(
            "app.rag.ingestion.get_bm25_store"
        ) as mock_bm25, patch(
            "app.rag.graph.graph_extractor.extract_and_store_graph", new_callable=AsyncMock
        ):
            mock_store = MagicMock()
            mock_store.add_documents = MagicMock()
            mock_store.update_document_metadata = MagicMock()
            mock_bm25.return_value = mock_store

            from app.rag.ingestion import ingestion_pipeline

            await ingestion_pipeline.process_file(
                pdf_path, "cleanup_test.pdf", "application/pdf", "job-cleanup"
            )

            # File should be deleted
            assert not os.path.exists(pdf_path)

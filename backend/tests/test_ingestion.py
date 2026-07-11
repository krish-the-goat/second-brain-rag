import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from langchain_core.documents import Document
from app.rag.ingestion import IngestionPipeline, ingestion_pipeline

@pytest.fixture
def mock_docs():
    return [Document(page_content="Test content", metadata={"hash": "123"})]

@pytest.mark.asyncio
@patch("app.rag.ingestion.load_pdf", new_callable=AsyncMock)
@patch("app.rag.ingestion.IngestionPipeline._process_docs", new_callable=AsyncMock)
@patch("app.rag.ingestion.set_cache", new_callable=AsyncMock)
@patch("os.path.exists", return_value=True)
@patch("os.remove")
async def test_process_file_pdf(mock_remove, mock_exists, mock_set_cache, mock_process_docs, mock_load_pdf, mock_docs):
    mock_load_pdf.return_value = mock_docs
    
    await ingestion_pipeline.process_file("dummy.pdf", "dummy.pdf", "application/pdf", "job_1")
    
    # Assert cache was set to processing then completed
    mock_set_cache.assert_any_call("job:job_1", "processing")
    mock_set_cache.assert_any_call("job:job_1", "completed")
    
    # Assert process docs was called with the documents
    mock_process_docs.assert_called_once()
    
    # Assert file cleanup happened
    mock_remove.assert_called_once_with("dummy.pdf")

@pytest.mark.asyncio
@patch("app.rag.ingestion.load_web", new_callable=AsyncMock)
@patch("app.rag.ingestion.IngestionPipeline._process_docs", new_callable=AsyncMock)
@patch("app.rag.ingestion.set_cache", new_callable=AsyncMock)
async def test_process_url(mock_set_cache, mock_process_docs, mock_load_web, mock_docs):
    mock_load_web.return_value = mock_docs
    
    await ingestion_pipeline.process_url("https://example.com", "job_url")
    
    mock_load_web.assert_called_once_with("https://example.com")
    mock_set_cache.assert_any_call("job:job_url", "processing")
    mock_set_cache.assert_any_call("job:job_url", "completed")
    mock_process_docs.assert_called_once()

@pytest.mark.asyncio
@patch("app.rag.ingestion.set_cache", new_callable=AsyncMock)
async def test_process_file_unsupported(mock_set_cache):
    # Testing branch where UnsupportedFormatError is raised
    await ingestion_pipeline.process_file("dummy.txt", "dummy.txt", "text/plain", "job_error")
    
    mock_set_cache.assert_any_call("job:job_error", "processing")
    # Should set failed status
    failed_calls = [call for call in mock_set_cache.call_args_list if "failed:" in call[0][1]]
    assert len(failed_calls) == 1

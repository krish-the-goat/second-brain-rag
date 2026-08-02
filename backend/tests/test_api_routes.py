"""Tests for API routes (health, documents, chat)."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked dependencies."""
    # Patch heavy dependencies before importing the app
    with patch("app.rag.retrievers.hybrid_retriever.CrossEncoder"), \
         patch("app.core.cache.init_cache", new_callable=AsyncMock), \
         patch("app.core.cache.close_cache", new_callable=AsyncMock), \
         patch("app.rag.vectorstore.chroma_store.get_stats", return_value={"total_chunks": 10}):
        from app.main import app
        with TestClient(app) as c:
            yield c


@pytest.fixture
def auth_headers():
    """Valid API key headers for authenticated endpoints."""
    return {"X-API-Key": "test-api-key-12345"}


class TestHealthRoutes:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Second Brain RAG" in response.json()["message"]


class TestAuthMiddleware:
    def test_protected_route_without_key(self, client):
        response = client.get("/documents")
        assert response.status_code == 403

    def test_protected_route_with_invalid_key(self, client):
        response = client.get("/documents", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403

    def test_protected_route_with_valid_key(self, client, auth_headers):
        with patch(
            "app.api.routes.documents.get_bm25_store"
        ) as mock_bm25:
            mock_store = MagicMock()
            mock_store.get_document_metadata.return_value = []
            mock_bm25.return_value = mock_store

            response = client.get("/documents", headers=auth_headers)
            assert response.status_code == 200

    def test_second_api_key_is_accepted(self, client):
        """Multi-key auth: the second key in API_KEYS should also work."""
        with patch(
            "app.api.routes.documents.get_bm25_store"
        ) as mock_bm25:
            mock_store = MagicMock()
            mock_store.get_document_metadata.return_value = []
            mock_bm25.return_value = mock_store

            response = client.get(
                "/documents", headers={"X-API-Key": "second-key-67890"}
            )
            assert response.status_code == 200


class TestDocumentRoutes:
    def test_upload_invalid_extension(self, client, auth_headers):
        """Only PDF and DOCX should be accepted."""
        response = client.post(
            "/documents/upload",
            headers=auth_headers,
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400

    def test_get_job_status_unknown(self, client, auth_headers):
        with patch("app.api.routes.documents.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = None
            response = client.get("/documents/jobs/fake-uuid", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["status"] == "unknown"

    def test_get_job_status_completed(self, client, auth_headers):
        with patch("app.api.routes.documents.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = "completed"
            response = client.get("/documents/jobs/real-uuid", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["status"] == "completed"

    def test_list_documents_empty(self, client, auth_headers):
        with patch(
            "app.api.routes.documents.get_bm25_store"
        ) as mock_bm25:
            mock_store = MagicMock()
            mock_store.get_document_metadata.return_value = []
            mock_bm25.return_value = mock_store

            response = client.get("/documents", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["documents"] == []


class TestChatRoutes:
    def test_chat_requires_auth(self, client):
        response = client.post("/chat", json={"question": "What is AI?"})
        assert response.status_code == 403

    def test_chat_validates_question_length(self, client, auth_headers):
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={"question": ""},
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_chat_stream_requires_auth(self, client):
        response = client.post("/chat/stream", json={"question": "Hello"})
        assert response.status_code == 403

    def test_chat_validates_history_length(self, client, auth_headers):
        """Chat history should respect max_length=20."""
        long_history = [{"role": "user", "content": f"msg {i}"} for i in range(25)]

        response = client.post(
            "/chat",
            headers=auth_headers,
            json={"question": "test", "chat_history": long_history},
        )
        assert response.status_code == 422

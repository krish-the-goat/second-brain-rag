import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@patch("app.api.routes.chat.pipeline")
def test_chat_stream_endpoint(mock_pipeline):
    # Mock the async generator for SSE
    async def mock_ask_stream(question, history):
        yield f"data: {json.dumps({'text': 'Hello'})}\n\n"
        yield f"data: {json.dumps({'text': ' World'})}\n\n"
        yield f"data: {json.dumps({'sources': [{'id': '123', 'text': 'foo'}]})}\n\n"

    mock_pipeline.ask_stream = mock_ask_stream

    response = client.post(
        "/chat/stream",
        json={"question": "What is life?", "chat_history": []},
        headers={"X-API-Key": "test-api-key-12345"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Read the streamed chunks
    chunks = [c for c in response.iter_lines() if c]
    assert len(chunks) >= 3
    assert "Hello" in chunks[0]
    assert "World" in chunks[1]
    assert "sources" in chunks[2]

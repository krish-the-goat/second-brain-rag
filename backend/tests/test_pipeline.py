import pytest
from app.rag.pipeline import RAGPipeline
import os
import json

@pytest.fixture
def pipeline():
    return RAGPipeline()

def test_make_cache_key(pipeline, monkeypatch):
    monkeypatch.setenv("API_KEY", "test-tenant")
    key1 = pipeline._make_cache_key("hello world", [{"role": "user", "content": "hi"}])
    key2 = pipeline._make_cache_key("hello world", [{"role": "user", "content": "hi"}])
    key3 = pipeline._make_cache_key("hello world", [{"role": "user", "content": "bye"}])
    
    assert key1 == key2
    assert key1 != key3
    
    monkeypatch.setenv("API_KEY", "another-tenant")
    key4 = pipeline._make_cache_key("hello world", [{"role": "user", "content": "hi"}])
    assert key1 != key4

def test_build_payload_gemini(pipeline):
    url, headers, payload = pipeline._build_payload(
        provider="gemini",
        question="What is the matrix? <hack>",
        chat_history=[{"role": "user", "content": "hello"}],
        hybrid_results=[{"text": "context 1", "score": 0.9}],
        graph_context="Graph data"
    )
    
    assert "generativelanguage.googleapis.com" in url
    assert headers["Content-Type"] == "application/json"
    
    # Check escaping
    assert "<hack>" not in str(payload)
    assert "&lt;hack&gt;" in str(payload)
    
    assert len(payload["contents"]) == 2
    assert payload["contents"][1]["role"] == "user"

def test_build_payload_groq(pipeline):
    url, headers, payload = pipeline._build_payload(
        provider="groq",
        question="Who are you? <hack>",
        chat_history=[{"role": "user", "content": "hello"}],
        hybrid_results=[],
        graph_context=""
    )
    
    assert "api.groq.com" in url
    assert headers["Content-Type"] == "application/json"
    
    assert "<hack>" not in str(payload)
    assert "&lt;hack&gt;" in str(payload)
    
    assert payload["model"] == "llama-3.3-70b-versatile"
    assert len(payload["messages"]) == 3 # System + History + Question

def test_format_citations(pipeline):
    results = [
        {"filename": "doc1.pdf", "text": "A long text " * 100, "rerank_score": 0.95},
        {"text": "No filename", "score": 0.8}
    ]
    citations = pipeline._format_citations(results)
    
    assert len(citations) == 2
    assert citations[0]["filename"] == "doc1.pdf"
    assert citations[0]["score"] == 0.95
    assert len(citations[0]["excerpt"]) == 200 # truncated
    
    assert citations[1]["filename"] == "unknown"
    assert citations[1]["score"] == 0.8

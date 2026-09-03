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

    # Cache key with owner_id cross-user isolation
    k_owner1 = pipeline._make_cache_key("hello world", [{"role": "user", "content": "hi"}], owner_id="1")
    k_owner2 = pipeline._make_cache_key("hello world", [{"role": "user", "content": "hi"}], owner_id="2")
    assert k_owner1 != k_owner2
    assert k_owner1 != key1

    # Passing via tenant_key parameter gives equivalent isolation
    k_tenant1 = pipeline._make_cache_key("hello world", [{"role": "user", "content": "hi"}], tenant_key="1")
    assert k_tenant1 == k_owner1

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
        {"filename": "doc1.pdf", "text": "A long text " * 100, "rerank_score": 0.95, "metadata": {"page_number": 4}},
        {"text": "No filename", "score": 0.8},
        {"text": "Doc with top-level page", "score": 0.9, "page_number": 12, "filename": "doc2.pdf"},
    ]
    citations = pipeline._format_citations(results)
    
    assert len(citations) == 3
    assert citations[0]["filename"] == "doc1.pdf"
    assert citations[0]["score"] == 0.95
    assert citations[0]["page_number"] == 4
    assert len(citations[0]["excerpt"]) == 200 # truncated
    
    assert citations[1]["filename"] == "unknown"
    assert citations[1]["score"] == 0.8
    assert citations[1]["page_number"] is None

    assert citations[2]["filename"] == "doc2.pdf"
    assert citations[2]["score"] == 0.9
    assert citations[2]["page_number"] == 12

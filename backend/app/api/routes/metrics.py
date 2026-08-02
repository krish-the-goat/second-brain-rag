from fastapi import APIRouter
import asyncio
from app.core.cache import get_metric
from app.rag.vectorstore.chroma_store import get_stats
from app.rag.vectorstore.bm25_store import get_bm25_store

router = APIRouter(tags=["Metrics"])

@router.get("/metrics")
async def metrics():
    # Run ChromaDB I/O in a separate thread so it doesn't block the event loop
    stats = await asyncio.to_thread(get_stats)
    total_docs = await asyncio.to_thread(get_bm25_store().get_total_docs)
    
    queries_today = await get_metric("queries_today")
    total_tokens_used = await get_metric("total_tokens_used")
    estimated_cost_usd = await get_metric("estimated_cost_usd")
    
    # Calculate average dynamically to avoid race conditions during updates
    total_reqs = await get_metric("total_http_requests")
    total_time = await get_metric("total_response_time_ms")
    avg_response_time_ms = total_time / total_reqs if total_reqs > 0 else 0.0
    
    return {
        "total_documents": total_docs,
        "total_chunks": stats.get("total_chunks", 0),
        "queries_today": queries_today,
        "avg_response_time_ms": avg_response_time_ms,
        "total_tokens_used": total_tokens_used,
        "estimated_cost_usd": estimated_cost_usd
    }

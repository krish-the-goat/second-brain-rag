from fastapi import APIRouter, Request
from app.core.cache import get_metric
from app.rag.vectorstore.chroma_store import get_stats

router = APIRouter(tags=["Metrics"])

@router.get("/metrics")
async def metrics():
    stats = get_stats()
    
    queries_today = await get_metric("queries_today")
    avg_response_time_ms = await get_metric("avg_response_time_ms")
    total_tokens_used = await get_metric("total_tokens_used")
    estimated_cost_usd = await get_metric("estimated_cost_usd")
    
    return {
        "total_documents": stats["total_docs"],
        "total_chunks": stats["total_chunks"],
        "queries_today": queries_today,
        "avg_response_time_ms": avg_response_time_ms,
        "total_tokens_used": total_tokens_used,
        "estimated_cost_usd": estimated_cost_usd
    }

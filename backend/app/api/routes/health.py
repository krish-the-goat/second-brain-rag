from fastapi import APIRouter, HTTPException, Request
from app.rag.vectorstore.chroma_store import get_stats
import httpx
import os

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness_check():
    try:
        # Check ChromaDB
        get_stats()
        
        # Check OpenRouter
        api_url = "https://openrouter.ai/api/v1/auth/key"
        headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(api_url, headers=headers)
            resp.raise_for_status()
        
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service Unavailable: {str(e)}")

from fastapi import APIRouter, HTTPException, Request
from langchain_google_genai import ChatGoogleGenerativeAI
from app.rag.vectorstore.chroma_store import get_stats

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness_check():
    try:
        # Check ChromaDB
        get_stats()
        
        # Check Gemini
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
        await llm.ainvoke("ping")
        
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service Unavailable: {str(e)}")

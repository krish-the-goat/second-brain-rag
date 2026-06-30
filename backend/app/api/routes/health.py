from fastapi import APIRouter, HTTPException
import httpx
import os

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check():
    """
    Verifies that:
    1. ChromaDB is reachable and queryable.
    2. The Google Gemini API key is present and the API is reachable.
    """
    errors = []

    # 1. ChromaDB
    try:
        from app.rag.vectorstore.chroma_store import get_stats
        get_stats()
    except Exception as e:
        errors.append(f"ChromaDB unavailable: {e}")

    # 2. Google Gemini API key validity
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        errors.append("GOOGLE_API_KEY environment variable is not set.")
    else:
        try:
            # Lightweight model-list call to verify the key is accepted.
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"x-goog-api-key": google_api_key},
                    timeout=5.0,
                )
                if resp.status_code == 401:
                    errors.append("GOOGLE_API_KEY is invalid (401 Unauthorized).")
                elif resp.status_code not in (200, 404):
                    errors.append(f"Google API returned unexpected status {resp.status_code}.")
        except Exception as e:
            errors.append(f"Google API unreachable: {e}")

    if errors:
        raise HTTPException(status_code=503, detail={"errors": errors})

    return {"status": "ready"}

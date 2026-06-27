import os
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.logging import get_logger

logger = get_logger(__name__)

# Use a fast, free local embedding model
model_name = "all-MiniLM-L6-v2"
logger.info(f"Loading local embedding model: {model_name}")
try:
    model = SentenceTransformer(model_name)
except Exception as e:
    logger.error(f"Failed to load local embedding model: {e}")
    model = None

async def embed_documents(texts: List[str]) -> List[List[float]]:
    """
    Generates embeddings locally using SentenceTransformers.
    """
    if not model or not texts:
        return []
        
    try:
        import asyncio
        # SentenceTransformer.encode returns numpy arrays, we convert to lists
        # CRITICAL FIX: Wrapped CPU-bound encode in to_thread to prevent event loop blocking
        embeddings = await asyncio.to_thread(model.encode, texts, show_progress_bar=False)
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Local embedding generation failed: {e}")
        return []

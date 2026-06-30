import os
from typing import List
from app.core.logging import get_logger

logger = get_logger(__name__)

_model = None
_model_load_attempted = False
MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():
    """Lazy-load the SentenceTransformer model on first use.

    Loading at module import time blocks the event loop (and gunicorn startup)
    while the ~90 MB model downloads from HuggingFace. By deferring the load
    to the first embed call (which already runs in a thread via asyncio.to_thread)
    we keep startup fast and surface download errors as proper HTTP 500s rather
    than silent crashes.
    """
    global _model, _model_load_attempted
    if _model_load_attempted:
        return _model
    _model_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading local embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load local embedding model: {e}")
        _model = None
    return _model


async def embed_documents(texts: List[str]) -> List[List[float]]:
    """Generate embeddings locally using SentenceTransformers.

    Runs the CPU-bound encode() in a thread pool so the async event loop
    is never blocked.
    """
    if not texts:
        return []

    try:
        import asyncio
        model = await asyncio.to_thread(_get_model)
        if model is None:
            logger.error("Embedding model unavailable — cannot embed documents.")
            return []

        embeddings = await asyncio.to_thread(model.encode, texts, show_progress_bar=False)
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Local embedding generation failed: {e}")
        return []

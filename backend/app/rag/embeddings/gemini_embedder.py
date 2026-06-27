import os
import time
import hashlib
import asyncio
from typing import List, Optional
import structlog
from google.api_core import exceptions
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.cache import get_cache, set_cache

logger = structlog.get_logger(__name__)

async def embed_documents(texts: List[str]) -> List[List[float]]:
    """
    Embed documents using Gemini with caching, batching (max 100), and exponential backoff.
    """
    if not texts:
        return []
        
    final_embeddings = []
    
    batch_size = 100
    embedder = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_embeddings = [None] * len(batch_texts)
        texts_to_embed = []
        indices_to_embed = []
        
        for j, text in enumerate(batch_texts):
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            cache_key = f"emb:{text_hash}"
            cached_emb = await get_cache(cache_key)
            
            if cached_emb:
                batch_embeddings[j] = cached_emb
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(j)
                
        if texts_to_embed:
            retries = [1, 2, 4]
            api_embeddings = None
            
            for delay in retries + [0]:
                try:
                    api_embeddings = await embedder.aembed_documents(texts_to_embed)
                    break
                except exceptions.ResourceExhausted as e:
                    if delay == 0:
                        logger.error("Rate limit exhausted after retries.")
                        raise e
                    logger.warning("Rate limit hit, retrying...", delay=delay)
                    await asyncio.sleep(delay)
            
            total_chars = sum(len(t) for t in texts_to_embed)
            logger.info("Embedded batch", num_docs=len(texts_to_embed), approx_chars=total_chars)
            
            for idx, emb, text in zip(indices_to_embed, api_embeddings, texts_to_embed):
                batch_embeddings[idx] = emb
                text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                await set_cache(f"emb:{text_hash}", emb, 86400)
                
        final_embeddings.extend(batch_embeddings)
        
    return final_embeddings

from typing import List, Dict, Tuple
from app.rag.vectorstore.chroma_store import query as chroma_query
from app.rag.embeddings.local_embedder import embed_documents
from app.rag.vectorstore.bm25_store import get_bm25_store
from sentence_transformers import CrossEncoder
import structlog
import uuid

logger = structlog.get_logger(__name__)

# Load local cross-encoder for reranking.
try:
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    logger.info("Successfully loaded local CrossEncoder for reranking.")
except Exception as e:
    logger.error(f"Failed to load CrossEncoder: {e}")
    reranker = None

def reciprocal_rank_fusion(dense_results: List[Dict], sparse_results: List[Dict], k: int = 60) -> List[Dict]:
    fused_scores = {}
    doc_map = {}

    def add_to_fusion(results: List[Dict]):
        for rank, doc in enumerate(results):
            # Try to get id, fallback to hash metadata, or generate one
            doc_id = doc.get("id") or doc.get("metadata", {}).get("hash") or str(uuid.uuid4())
            doc["id"] = doc_id
            
            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0.0
                doc_map[doc_id] = doc
            fused_scores[doc_id] += 1.0 / (rank + k)

    add_to_fusion(dense_results)
    add_to_fusion(sparse_results)

    sorted_docs = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[doc_id] for doc_id, _ in sorted_docs]

async def hybrid_search(query: str, top_k: int = 5) -> List[Dict]:
    fetch_k = top_k * 3
    
    # 1. Fetch Dense (Chroma)
    dense_results = []
    embeddings = await embed_documents([query])
    if embeddings:
        dense_results = await chroma_query(embeddings[0], n_results=fetch_k, score_threshold=0.0)
        
    # 2. Fetch Sparse (BM25)
    bm25_store = get_bm25_store()
    sparse_results = bm25_store.search(query, top_k=fetch_k)
    
    # 3. RRF Fusion
    fused_results = reciprocal_rank_fusion(dense_results, sparse_results)
    
    if not reranker or not fused_results:
        return fused_results[:top_k]
        
    # 4. Reranking (Cross-Encoder)
    pairs = [[query, doc.get("text", "")] for doc in fused_results]
    
    try:
        import asyncio
        # CRITICAL FIX: Wrapped CPU-bound reranker in to_thread
        scores = await asyncio.to_thread(reranker.predict, pairs)
        for doc, score in zip(fused_results, scores):
            doc["rerank_score"] = float(score)
            
            # Extract parent_content from metadata if available for the prompt builder
            meta = doc.get("metadata", {})
            if "parent_content" in meta:
                doc["parent_content"] = meta["parent_content"]
            if "filename" in meta:
                doc["filename"] = meta["filename"]
                
        reranked_results = sorted(fused_results, key=lambda x: x["rerank_score"], reverse=True)
        return reranked_results[:top_k]
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        return fused_results[:top_k]

from typing import List, Dict, Tuple
from app.rag.vectorstore.chroma_store import get_chroma_store
from app.rag.vectorstore.bm25_store import get_bm25_store
from sentence_transformers import CrossEncoder
from app.core.logging import get_logger

logger = get_logger(__name__)

# Load local cross-encoder for reranking. 
# This runs locally and does not require an API key!
try:
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    logger.info("Successfully loaded local CrossEncoder for reranking.")
except Exception as e:
    logger.error(f"Failed to load CrossEncoder: {e}")
    reranker = None

def reciprocal_rank_fusion(dense_results: List[Dict], sparse_results: List[Dict], k: int = 60) -> List[Dict]:
    """Combines Dense and Sparse results using Reciprocal Rank Fusion (RRF)."""
    fused_scores = {}
    doc_map = {}

    def add_to_fusion(results: List[Dict]):
        for rank, doc in enumerate(results):
            doc_id = doc["id"]
            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0.0
                doc_map[doc_id] = doc
            fused_scores[doc_id] += 1.0 / (rank + k)

    add_to_fusion(dense_results)
    add_to_fusion(sparse_results)

    # Sort by fused score
    sorted_docs = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[doc_id] for doc_id, _ in sorted_docs]

async def hybrid_search(query: str, top_k: int = 5) -> List[Dict]:
    """
    Performs Hybrid Search:
    1. Fetches top K from Dense (ChromaDB)
    2. Fetches top K from Sparse (BM25)
    3. Fuses them using RRF
    4. Reranks the fused list using a powerful local Cross-Encoder.
    """
    chroma_store = get_chroma_store()
    bm25_store = get_bm25_store()
    
    # 1 & 2. Retrieve from both stores (fetch more than needed for good reranking)
    fetch_k = top_k * 3
    dense_results = await chroma_store.similarity_search(query, n_results=fetch_k)
    sparse_results = bm25_store.search(query, top_k=fetch_k)
    
    # 3. RRF Fusion
    fused_results = reciprocal_rank_fusion(dense_results, sparse_results)
    
    # If we have no reranker or results are empty, just return the fused top K
    if not reranker or not fused_results:
        return fused_results[:top_k]
        
    # 4. Reranking (Cross-Encoder)
    # The Cross-Encoder takes a list of pairs: (Query, Document_Text)
    pairs = [[query, doc["text"]] for doc in fused_results]
    
    try:
        scores = reranker.predict(pairs)
        # Add scores back to the documents
        for doc, score in zip(fused_results, scores):
            doc["rerank_score"] = float(score)
            
        # Sort by rerank score
        reranked_results = sorted(fused_results, key=lambda x: x["rerank_score"], reverse=True)
        return reranked_results[:top_k]
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        # Fallback to RRF
        return fused_results[:top_k]

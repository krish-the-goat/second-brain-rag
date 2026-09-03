import os
import asyncio
import uuid
from typing import List, Dict, Optional

import structlog
from sentence_transformers import CrossEncoder

from app.rag.vectorstore.chroma_store import query as chroma_query, get_chunk_metadatas
from app.rag.embeddings.local_embedder import embed_documents
from app.rag.vectorstore.bm25_store import get_bm25_store
from app.core.cache import get_cache

logger = structlog.get_logger(__name__)

# --- Configuration ---
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RRF_K = int(os.getenv("RRF_K", "60"))
RETRIEVAL_MULTIPLIER = int(os.getenv("RETRIEVAL_MULTIPLIER", "3"))

# Load local cross-encoder for reranking (lazy-safe: if model download fails, reranking is skipped).
try:
    reranker = CrossEncoder(RERANKER_MODEL)
    logger.info("CrossEncoder loaded for reranking.", model=RERANKER_MODEL)
except Exception as e:
    logger.error(f"Failed to load CrossEncoder: {e}")
    reranker = None


def reciprocal_rank_fusion(
    dense_results: List[Dict], sparse_results: List[Dict], k: int = RRF_K
) -> List[Dict]:
    """Merge dense and sparse results using Reciprocal Rank Fusion."""
    fused_scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict] = {}

    def add_to_fusion(results: List[Dict]):
        for rank, doc in enumerate(results):
            doc_id = (
                doc.get("id")
                or doc.get("metadata", {}).get("hash")
                or str(uuid.uuid4())
            )
            doc["id"] = doc_id

            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0.0
                doc_map[doc_id] = doc
            fused_scores[doc_id] += 1.0 / (rank + k)

    add_to_fusion(dense_results)
    add_to_fusion(sparse_results)

    sorted_docs = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[doc_id] for doc_id, _ in sorted_docs]


async def hybrid_search(
    query: str, top_k: int = 5, owner_id: Optional[str] = None
) -> List[Dict]:
    """
    Full hybrid retrieval pipeline:
    1. Dense search (ChromaDB embeddings with optional owner_id filter)
    2. Sparse search (BM25 keyword matching)
    3. Reciprocal Rank Fusion
    4. Metadata hydration & per-user document isolation filter (via Chroma metadata)
    5. Cross-Encoder reranking
    6. Parent content and metadata hydration from cache and Chroma
    """
    fetch_k = top_k * RETRIEVAL_MULTIPLIER

    # 1. Dense search (ChromaDB) - scoped to owner_id if provided
    dense_results: List[Dict] = []
    embeddings = await embed_documents([query])
    if embeddings:
        filters = {"owner_id": str(owner_id)} if owner_id else None
        dense_results = await chroma_query(
            embeddings[0], n_results=fetch_k, score_threshold=0.0, filters=filters
        )

    # 2. Sparse search (BM25)
    bm25_store = get_bm25_store()
    sparse_results = await asyncio.to_thread(bm25_store.search, query, fetch_k)

    # 3. RRF Fusion
    fused_results = reciprocal_rank_fusion(dense_results, sparse_results)

    # Hydrate metadata from Chroma for chunks missing metadata (e.g. from BM25 sparse search)
    missing_ids = [doc["id"] for doc in fused_results if doc.get("id") and not doc.get("metadata")]
    if missing_ids:
        meta_map = await get_chunk_metadatas(missing_ids)
        for doc in fused_results:
            if not doc.get("metadata") and doc.get("id") in meta_map:
                doc["metadata"] = meta_map[doc["id"]]

    # User isolation: restrict fused results to owner_id if specified.
    # Because BM25/Postgres sparse store search() has no owner filter, the simplest
    # correct and least invasive approach is to filter the fused results by matching
    # the chunk's owner_id from Chroma metadata against the target owner_id. Any chunk
    # that does not belong to this owner (or has missing metadata) is excluded.
    # This guarantees a user only ever sees their own chunks without modifying
    # SQLite/Postgres store internals or retrieval fusion/rerank math.
    if owner_id:
        target_owner = str(owner_id)
        fused_results = [
            doc for doc in fused_results
            if doc.get("metadata", {}).get("owner_id") == target_owner
        ]

    if not reranker or not fused_results:
        for doc in fused_results:
            meta = doc.get("metadata", {})
            if "filename" in meta:
                doc["filename"] = meta["filename"]
            if "page_number" in meta:
                doc["page_number"] = meta["page_number"]
        return fused_results[:top_k]

    # 4. Reranking (Cross-Encoder) — CPU-bound, runs in thread pool
    pairs = [[query, doc.get("text", "")] for doc in fused_results]

    try:
        scores = await asyncio.to_thread(reranker.predict, pairs)
        for doc, score in zip(fused_results, scores):
            doc["rerank_score"] = float(score)

            # 5. Hydrate parent content from cache for prompt building
            meta = doc.get("metadata", {})
            parent_id = meta.get("parent_id")
            if parent_id:
                parent_text = await get_cache(f"parent:{parent_id}")
                if parent_text:
                    doc["parent_content"] = parent_text
            if "filename" in meta:
                doc["filename"] = meta["filename"]
            if "page_number" in meta:
                doc["page_number"] = meta["page_number"]

        reranked_results = sorted(
            fused_results, key=lambda x: x["rerank_score"], reverse=True
        )
        return reranked_results[:top_k]
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        for doc in fused_results:
            meta = doc.get("metadata", {})
            if "filename" in meta:
                doc["filename"] = meta["filename"]
            if "page_number" in meta:
                doc["page_number"] = meta["page_number"]
        return fused_results[:top_k]

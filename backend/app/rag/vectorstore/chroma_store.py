import os
import uuid
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

_client = None

def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        # In production with docker-compose, connect to the chroma container
        chroma_host = os.getenv("CHROMA_HOST", "chroma")
        chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
        try:
            _client = chromadb.HttpClient(host=chroma_host, port=chroma_port, settings=Settings(anonymized_telemetry=False))
        except Exception:
            # Fallback to local if running script directly without docker
            persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
            _client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
    return _client
    
def get_collection():
    client = get_client()
    return client.get_or_create_collection("rag_collection")

async def add_documents(docs: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
    collection = get_collection()
    
    ids = []
    for meta in metadatas:
        doc_hash = meta.get("hash", str(uuid.uuid4()))
        ids.append(doc_hash)
        
    existing = collection.get(ids=ids)["ids"]
    existing_set = set(existing)
    
    new_docs = []
    new_embs = []
    new_metas = []
    new_ids = []
    
    for i, doc_id in enumerate(ids):
        if doc_id not in existing_set:
            new_docs.append(docs[i])
            new_embs.append(embeddings[i])
            new_metas.append(metadatas[i])
            new_ids.append(doc_id)
            
    if new_ids:
        clean_metas = []
        for m in new_metas:
            clean = {}
            for k, v in m.items():
                if isinstance(v, (str, int, float, bool)):
                    clean[k] = v
                else:
                    clean[k] = str(v)
            if "doc_id" not in clean:
                clean["doc_id"] = clean.get("filename", "unknown")
            clean_metas.append(clean)
            
        collection.add(
            ids=new_ids,
            embeddings=new_embs,
            documents=new_docs,
            metadatas=clean_metas
        )

async def query(embedding: List[float], n_results: int = 5, score_threshold: float = 0.7, filters: Optional[Dict] = None) -> List[Dict]:
    collection = get_collection()
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        where=filters,
        include=["documents", "metadatas", "distances"]
    )
    
    output = []
    if not results["documents"] or not results["documents"][0]:
        return output
        
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]
    
    for doc, meta, dist in zip(docs, metas, dists):
        score = 1.0 / (1.0 + dist)
        if score >= score_threshold:
            output.append({
                "text": doc,
                "metadata": meta,
                "score": score
            })
            
    return output

async def delete_document(doc_id: str):
    collection = get_collection()
    collection.delete(where={"doc_id": doc_id})

async def list_documents() -> List[Dict]:
    collection = get_collection()
    results = collection.get(include=["metadatas"])
    metadatas = results["metadatas"]
    
    docs_map = {}
    for m in metadatas:
        doc_id = m.get("doc_id")
        if not doc_id:
            continue
        if doc_id not in docs_map:
            docs_map[doc_id] = {
                "doc_id": doc_id,
                "filename": m.get("filename", "unknown"),
                "chunk_count": 0,
                "created_at": m.get("scraped_at", m.get("created_at", "unknown"))
            }
        docs_map[doc_id]["chunk_count"] += 1
        
    return list(docs_map.values())

def get_stats() -> Dict[str, int]:
    collection = get_collection()
    count = collection.count()
    results = collection.get(include=["metadatas"])
    doc_ids = set()
    for m in results["metadatas"]:
        if "doc_id" in m:
            doc_ids.add(m["doc_id"])
            
    return {
        "total_docs": len(doc_ids),
        "total_chunks": count
    }

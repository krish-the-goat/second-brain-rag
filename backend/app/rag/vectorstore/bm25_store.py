import json
import os
import threading
from typing import List, Dict
from rank_bm25 import BM25Okapi
from app.core.logging import get_logger

logger = get_logger(__name__)

# Resolve to an absolute path so it works regardless of CWD.
# BM25_DATA_DIR defaults to /app/bm25_data inside the container (mounted as a named volume).
_data_dir = os.getenv("BM25_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "bm25_data"))
BM25_FILE_PATH = os.path.join(os.path.abspath(_data_dir), "bm25_corpus.json")


class BM25Store:
    def __init__(self):
        self._lock = threading.Lock()
        self.corpus: List[Dict[str, str]] = []
        self.bm25: BM25Okapi = None
        self._load()

    def _load(self):
        if os.path.exists(BM25_FILE_PATH):
            try:
                with open(BM25_FILE_PATH, "r") as f:
                    self.corpus = json.load(f)
                self._build_index()
                logger.info(f"Loaded BM25 index with {len(self.corpus)} chunks from {BM25_FILE_PATH}.")
            except Exception as e:
                logger.error(f"Failed to load BM25 corpus: {e}")
                self.corpus = []
        else:
            logger.info(f"No BM25 corpus found at {BM25_FILE_PATH}. Starting fresh.")

    def _save(self):
        """Write corpus atomically: write to a temp file then rename."""
        os.makedirs(os.path.dirname(BM25_FILE_PATH), exist_ok=True)
        tmp_path = BM25_FILE_PATH + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(self.corpus, f)
        os.replace(tmp_path, BM25_FILE_PATH)  # atomic on POSIX; last writer wins safely

    def _build_index(self):
        if self.corpus:
            tokenized_corpus = [doc["text"].lower().split() for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
        else:
            self.bm25 = None

    def add_documents(self, documents: List[Dict[str, str]]):
        """Add documents to the BM25 index.

        Thread-safe: acquires a lock so concurrent uploads don't lose data.
        Expected format: [{'id': '123', 'text': 'content'}, ...]
        """
        with self._lock:
            # Deduplicate by id to avoid re-adding on retry
            existing_ids = {doc["id"] for doc in self.corpus}
            new_docs = [d for d in documents if d["id"] not in existing_ids]
            if not new_docs:
                return
            self.corpus.extend(new_docs)
            self._build_index()
            self._save()
        logger.info(f"Added {len(new_docs)} documents to BM25 index (total: {len(self.corpus)}).")

    def delete_documents_by_doc_id(self, doc_id: str):
        """Remove all chunks associated with a specific doc_id from the BM25 index."""
        with self._lock:
            initial_len = len(self.corpus)
            self.corpus = [d for d in self.corpus if d.get("doc_id") != doc_id]
            if len(self.corpus) < initial_len:
                self._build_index()
                self._save()
                logger.info(f"Deleted {initial_len - len(self.corpus)} chunks from BM25 for doc_id: {doc_id}")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search the BM25 index and return the top_k matching chunks."""
        if not self.bm25 or not self.corpus:
            return []

        tokenized_query = query.lower().split()
        doc_scores = self.bm25.get_scores(tokenized_query)

        scored_docs = sorted(zip(doc_scores, self.corpus), key=lambda x: x[0], reverse=True)

        return [
            {"id": doc["id"], "text": doc["text"], "score": float(score)}
            for score, doc in scored_docs[:top_k]
            if score > 0
        ]


# Singleton
_bm25_store: BM25Store = None


def get_bm25_store() -> BM25Store:
    global _bm25_store
    if _bm25_store is None:
        _bm25_store = BM25Store()
    return _bm25_store

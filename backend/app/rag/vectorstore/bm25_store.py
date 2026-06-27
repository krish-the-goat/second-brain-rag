import json
import os
from typing import List, Dict
from rank_bm25 import BM25Okapi
from app.core.logging import get_logger

logger = get_logger(__name__)

BM25_FILE_PATH = os.path.join("chroma_data", "bm25_corpus.json")

class BM25Store:
    def __init__(self):
        self.corpus: List[Dict[str, str]] = []
        self.bm25: BM25Okapi = None
        self._load()

    def _load(self):
        if os.path.exists(BM25_FILE_PATH):
            try:
                with open(BM25_FILE_PATH, "r") as f:
                    self.corpus = json.load(f)
                self._build_index()
                logger.info(f"Loaded BM25 index with {len(self.corpus)} chunks.")
            except Exception as e:
                logger.error(f"Failed to load BM25 corpus: {e}")
                self.corpus = []
        else:
            logger.info("No BM25 corpus found. Starting fresh.")

    def _save(self):
        os.makedirs(os.path.dirname(BM25_FILE_PATH), exist_ok=True)
        with open(BM25_FILE_PATH, "w") as f:
            json.dump(self.corpus, f)

    def _build_index(self):
        if self.corpus:
            tokenized_corpus = [doc["text"].lower().split() for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
        else:
            self.bm25 = None

    def add_documents(self, documents: List[Dict[str, str]]):
        """Add documents to the BM25 index. Expected format: [{'id': '123', 'text': 'content'}]"""
        self.corpus.extend(documents)
        self._build_index()
        self._save()
        logger.info(f"Added {len(documents)} documents to BM25 index.")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search the BM25 index and return the top_k matching chunks with scores."""
        if not self.bm25 or not self.corpus:
            return []

        tokenized_query = query.lower().split()
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # Sort documents by score
        scored_docs = sorted(zip(doc_scores, self.corpus), key=lambda x: x[0], reverse=True)
        
        results = []
        for score, doc in scored_docs[:top_k]:
            if score > 0:
                results.append({"id": doc["id"], "text": doc["text"], "score": score})
                
        return results

# Singleton instance
_bm25_store = None

def get_bm25_store() -> BM25Store:
    global _bm25_store
    if _bm25_store is None:
        _bm25_store = BM25Store()
    return _bm25_store

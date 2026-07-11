import sqlite3
import os
import json
import threading
from typing import List, Dict
from app.core.logging import get_logger

logger = get_logger(__name__)

# Resolve to an absolute path so it works regardless of CWD.
_data_dir = os.getenv("BM25_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "bm25_data"))
BM25_FILE_PATH = os.path.join(os.path.abspath(_data_dir), "bm25_corpus.json")
SQLITE_DB_PATH = os.path.join(os.path.abspath(_data_dir), "bm25.db")

class BM25Store:
    def __init__(self):
        os.makedirs(_data_dir, exist_ok=True)
        self._migrate_if_needed()
        self.conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False, timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS corpus USING fts5(id UNINDEXED, text, doc_id UNINDEXED);
        """)
        self._lock = threading.Lock()

    def _migrate_if_needed(self):
        if os.path.exists(BM25_FILE_PATH) and not os.path.exists(SQLITE_DB_PATH):
            logger.info("Migrating JSON BM25 corpus to SQLite FTS5...")
            tmp_json = BM25_FILE_PATH + ".tmp_migration"
            try:
                os.rename(BM25_FILE_PATH, tmp_json)
                with open(tmp_json, "r") as f:
                    corpus = json.load(f)
                
                conn = sqlite3.connect(SQLITE_DB_PATH)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS corpus USING fts5(id UNINDEXED, text, doc_id UNINDEXED);
                """)
                conn.executemany("INSERT INTO corpus (id, text, doc_id) VALUES (?, ?, ?)", 
                    [(d["id"], d["text"], d.get("doc_id", "unknown")) for d in corpus]
                )
                conn.commit()
                conn.close()
                os.remove(tmp_json)
                logger.info("Migration successful.")
            except Exception as e:
                logger.error(f"Failed to migrate BM25 corpus: {e}")
                if os.path.exists(tmp_json):
                    os.rename(tmp_json, BM25_FILE_PATH) # Revert

    def add_documents(self, documents: List[Dict[str, str]]):
        if not documents:
            return
        with self._lock:
            # deduplicate by id
            for d in documents:
                self.conn.execute("DELETE FROM corpus WHERE id = ?", (d["id"],))
            self.conn.executemany("INSERT INTO corpus (id, text, doc_id) VALUES (?, ?, ?)",
                [(d["id"], d["text"], d.get("doc_id", "unknown")) for d in documents]
            )
            self.conn.commit()
        logger.info(f"Added {len(documents)} documents to BM25 index.")

    def delete_documents_by_doc_id(self, doc_id: str):
        with self._lock:
            self.conn.execute("DELETE FROM corpus WHERE doc_id = ?", (doc_id,))
            self.conn.commit()
        logger.info(f"Deleted chunks from BM25 for doc_id: {doc_id}")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if not query.strip():
            return []
            
        # Standardize query format (naive FTS5 escaping)
        safe_query = query.replace('"', '""').replace("'", "''")
        try:
            cursor = self.conn.execute(
                f"""
                SELECT id, text, -bm25(corpus) as score 
                FROM corpus 
                WHERE corpus MATCH ? 
                ORDER BY score DESC 
                LIMIT ?
                """, 
                (safe_query, top_k)
            )
            results = []
            for row in cursor:
                # Ensure we only return positive matching scores
                if row[2] > 0:
                    results.append({"id": row[0], "text": row[1], "score": float(row[2])})
            return results
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS5 query failed (likely syntax error with input string): {e}")
            return []
            
    def get_total_docs(self) -> int:
        cursor = self.conn.execute("SELECT COUNT(DISTINCT doc_id) FROM corpus")
        row = cursor.fetchone()
        return row[0] if row else 0

_bm25_store: BM25Store = None

def get_bm25_store() -> BM25Store:
    global _bm25_store
    if _bm25_store is None:
        _bm25_store = BM25Store()
    return _bm25_store

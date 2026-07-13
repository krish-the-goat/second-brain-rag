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
        self.conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False, timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        
        # Initialize schema
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS corpus USING fts5(id UNINDEXED, text, doc_id UNINDEXED);
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS corpus_mapping (
                rowid INTEGER PRIMARY KEY,
                chunk_id TEXT UNIQUE,
                doc_id TEXT
            );
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS document_metadata (
                doc_id TEXT PRIMARY KEY,
                filename TEXT,
                chunk_count INTEGER,
                status TEXT,
                created_at TEXT
            );
        """)
        # Create indexes for fast lookup
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_mapping_chunk_id ON corpus_mapping(chunk_id);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_mapping_doc_id ON corpus_mapping(doc_id);")
        self.conn.commit()

        self._lock = threading.Lock()
        self._migrate_if_needed()

    def _migrate_if_needed(self):
        # Fallback migration from JSON
        if os.path.exists(BM25_FILE_PATH) and not os.path.exists(SQLITE_DB_PATH):
            logger.info("Migrating JSON BM25 corpus to SQLite FTS5...")
            tmp_json = BM25_FILE_PATH + ".tmp_migration"
            try:
                os.rename(BM25_FILE_PATH, tmp_json)
                with open(tmp_json, "r") as f:
                    corpus = json.load(f)
                
                self.add_documents(corpus)
                os.remove(tmp_json)
                logger.info("Migration successful.")
            except Exception as e:
                logger.error(f"Failed to migrate BM25 corpus: {e}")
                if os.path.exists(tmp_json):
                    os.rename(tmp_json, BM25_FILE_PATH)

        # Ensure corpus_mapping is in sync with corpus (for upgrades to this schema)
        with self._lock:
            cursor = self.conn.execute("SELECT COUNT(*) FROM corpus_mapping")
            mapping_count = cursor.fetchone()[0]
            cursor = self.conn.execute("SELECT COUNT(*) FROM corpus")
            corpus_count = cursor.fetchone()[0]
            
            if mapping_count == 0 and corpus_count > 0:
                logger.info("Migrating FTS5 corpus to new corpus_mapping schema...")
                self.conn.execute("""
                    INSERT INTO corpus_mapping (rowid, chunk_id, doc_id)
                    SELECT rowid, id, doc_id FROM corpus
                """)
                self.conn.commit()
                logger.info("Mapping migration successful.")

    def add_documents(self, documents: List[Dict[str, str]]):
        if not documents:
            return
        with self._lock:
            for d in documents:
                chunk_id = d["id"]
                text = d["text"]
                doc_id = d.get("doc_id", "unknown")
                
                # Delete existing chunk if present (using O(1) rowid lookup)
                cursor = self.conn.execute("SELECT rowid FROM corpus_mapping WHERE chunk_id = ?", (chunk_id,))
                row = cursor.fetchone()
                if row:
                    old_rowid = row[0]
                    self.conn.execute("DELETE FROM corpus WHERE rowid = ?", (old_rowid,))
                    self.conn.execute("DELETE FROM corpus_mapping WHERE rowid = ?", (old_rowid,))
                
                # Insert into FTS5
                cursor = self.conn.execute(
                    "INSERT INTO corpus (id, text, doc_id) VALUES (?, ?, ?)",
                    (chunk_id, text, doc_id)
                )
                new_rowid = cursor.lastrowid
                
                # Insert into mapping
                self.conn.execute(
                    "INSERT INTO corpus_mapping (rowid, chunk_id, doc_id) VALUES (?, ?, ?)",
                    (new_rowid, chunk_id, doc_id)
                )
                
            self.conn.commit()
        logger.info(f"Added {len(documents)} documents to BM25 index.")

    def delete_documents_by_doc_id(self, doc_id: str):
        with self._lock:
            # Find all rowids for this doc_id
            cursor = self.conn.execute("SELECT rowid FROM corpus_mapping WHERE doc_id = ?", (doc_id,))
            rowids = [row[0] for row in cursor.fetchall()]
            
            for rid in rowids:
                self.conn.execute("DELETE FROM corpus WHERE rowid = ?", (rid,))
                
            self.conn.execute("DELETE FROM corpus_mapping WHERE doc_id = ?", (doc_id,))
            
            # Also clean up metadata
            self.conn.execute("DELETE FROM document_metadata WHERE doc_id = ?", (doc_id,))
            self.conn.commit()
        logger.info(f"Deleted chunks from BM25 for doc_id: {doc_id}")

    def update_document_metadata(self, doc_id: str, filename: str, chunk_count: int, status: str, created_at: str):
        with self._lock:
            self.conn.execute("""
                INSERT INTO document_metadata (doc_id, filename, chunk_count, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    filename=excluded.filename,
                    chunk_count=excluded.chunk_count,
                    status=excluded.status,
                    created_at=excluded.created_at
            """, (doc_id, filename, chunk_count, status, created_at))
            self.conn.commit()

    def get_document_metadata(self) -> List[Dict]:
        with self._lock:
            cursor = self.conn.execute("SELECT doc_id, filename, chunk_count, status, created_at FROM document_metadata")
            results = []
            for row in cursor:
                results.append({
                    "doc_id": row[0],
                    "filename": row[1],
                    "chunk_count": row[2],
                    "status": row[3],
                    "created_at": row[4]
                })
            return results

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        import re
        if not query.strip():
            return []
            
        words = [w for w in re.split(r'\W+', query) if w]
        if not words:
            return []
        safe_query = " OR ".join(words)
        
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
                if row[2] > 0:
                    results.append({"id": row[0], "text": row[1], "score": float(row[2])})
            return results
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS5 query failed (likely syntax error with input string): {e}")
            return []
            
    def get_total_docs(self) -> int:
        with self._lock:
            cursor = self.conn.execute("SELECT COUNT(*) FROM document_metadata")
            row = cursor.fetchone()
            return row[0] if row else 0

_bm25_store: BM25Store = None

def get_bm25_store() -> BM25Store:
    global _bm25_store
    if _bm25_store is None:
        _bm25_store = BM25Store()
    return _bm25_store

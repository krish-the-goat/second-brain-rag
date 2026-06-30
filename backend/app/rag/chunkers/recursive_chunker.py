import os
import uuid
import hashlib
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Key for looking up the parent chunk in the separate parent store.
# We no longer embed the full parent text inside every child's metadata (that
# multiplied storage by ~5x and bloated ChromaDB). Instead each child stores
# only a parent_id, and callers that need the parent text look it up via the
# in-memory parent store returned alongside the child chunks.
_PARENT_STORE: dict[str, str] = {}  # parent_id -> parent_text


def get_parent_text(parent_id: str) -> str:
    """Look up a parent chunk by its id. Returns empty string if not found."""
    return _PARENT_STORE.get(parent_id, "")


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Parent-Child chunking strategy for Advanced RAG.

    * Large parent chunks (default 2000 chars) are stored in _PARENT_STORE
      keyed by a UUID, so the AI can read full context at query time.
    * Small child chunks (400 chars) are stored in ChromaDB for precise
      similarity matching.
    * Each child's metadata carries only the parent_id (not the full parent
      text), avoiding O(children) duplication in the vector store.
    """
    parent_size = int(os.getenv("CHUNK_SIZE", "2000"))
    parent_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    child_size = 400
    child_overlap = 50

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=parent_size,
        chunk_overlap=parent_overlap,
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=child_size,
        chunk_overlap=child_overlap,
    )

    final_child_docs: List[Document] = []

    for doc in documents:
        parent_chunks = parent_splitter.split_text(doc.page_content)

        for p_idx, parent_text in enumerate(parent_chunks):
            parent_id = str(uuid.uuid4())
            _PARENT_STORE[parent_id] = parent_text  # lightweight in-memory store

            child_chunks = child_splitter.split_text(parent_text)

            for c_idx, child_text in enumerate(child_chunks):
                chunk_hash = hashlib.sha256(
                    f"{parent_id}_{c_idx}_{child_text}".encode()
                ).hexdigest()

                new_metadata = doc.metadata.copy()
                new_metadata["chunk_index"] = c_idx
                new_metadata["parent_index"] = p_idx
                new_metadata["parent_id"] = parent_id  # reference only — no full text
                new_metadata["hash"] = chunk_hash

                final_child_docs.append(
                    Document(page_content=child_text, metadata=new_metadata)
                )

    return final_child_docs

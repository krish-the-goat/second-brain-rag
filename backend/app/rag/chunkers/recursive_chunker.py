import os
import uuid
import hashlib
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Chunk a list of documents using Parent-Child strategy for Advanced RAG.
    Creates large parent chunks for context, and small child chunks for retrieval.
    Stores the parent context in the child's metadata.
    """
    # Parent (large) chunking
    parent_size = int(os.getenv("CHUNK_SIZE", "2000"))
    parent_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Child (small) chunking
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
    
    final_child_docs = []
    
    for doc in documents:
        # Split into parent chunks
        parent_chunks = parent_splitter.split_text(doc.page_content)
        
        for p_idx, parent_text in enumerate(parent_chunks):
            parent_id = str(uuid.uuid4())
            
            # Split parent into child chunks
            child_chunks = child_splitter.split_text(parent_text)
            
            for c_idx, child_text in enumerate(child_chunks):
                # Generate a unique deterministic hash for the child chunk based on content + parent id
                chunk_hash = hashlib.sha256(f"{parent_id}_{c_idx}_{child_text}".encode()).hexdigest()
                
                new_metadata = doc.metadata.copy()
                new_metadata["chunk_index"] = c_idx
                new_metadata["parent_index"] = p_idx
                new_metadata["parent_id"] = parent_id
                new_metadata["hash"] = chunk_hash
                # Store the parent text directly in metadata so we don't need a separate parent DB
                new_metadata["parent_content"] = parent_text
                
                # The document content itself is the CHILD text for precise retrieval matching
                final_child_docs.append(
                    Document(page_content=child_text, metadata=new_metadata)
                )
                
    return final_child_docs

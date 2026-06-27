import os
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Chunk a list of documents using RecursiveCharacterTextSplitter.
    Reads CHUNK_SIZE and CHUNK_OVERLAP from environment variables.
    Preserves parent metadata and adds chunk_index and total_chunks.
    """
    chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    chunked_docs = []
    
    for doc in documents:
        chunks = splitter.split_text(doc.page_content)
        total_chunks = len(chunks)
        
        for i, chunk_text in enumerate(chunks):
            # Create a copy of the parent metadata to avoid modifying the original
            new_metadata = doc.metadata.copy()
            new_metadata["chunk_index"] = i
            new_metadata["total_chunks"] = total_chunks
            
            chunked_docs.append(
                Document(page_content=chunk_text, metadata=new_metadata)
            )
            
    return chunked_docs

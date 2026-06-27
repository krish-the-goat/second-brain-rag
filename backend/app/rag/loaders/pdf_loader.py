import asyncio
import hashlib
from typing import List, Optional
import PyPDF2
import pdfplumber
from langchain_core.documents import Document
from app.core.exceptions import ProcessingError, UnsupportedFormatError

def _process_pdf_sync(file_path: str) -> List[Document]:
    documents = []
    
    with open(file_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        
        if reader.is_encrypted:
            raise ProcessingError("Cannot process encrypted PDF.")
            
        total_pages = len(reader.pages)
        if total_pages > 500:
            raise DocumentTooLargeError(f"PDF exceeds the maximum allowed page limit of 500 pages (found {total_pages} pages).")
            
        # PERFORMANCE FIX: Open pdfplumber ONCE outside the loop
        with pdfplumber.open(file_path) as pdf:
            for i in range(total_pages):
                page = reader.pages[i]
                text = page.extract_text() or ""
                
                # Extract tables using the already open pdfplumber instance
                plumber_page = pdf.pages[i]
                tables = plumber_page.extract_tables()
                if tables:
                    text += "\n" + "\n".join([str(t) for t in tables])
            
                # Generate hash
                page_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                
                metadata = {
                    "filename": file_path.split("/")[-1],
                    "page_number": i + 1,
                    "total_pages": total_pages,
                    "source_type": "pdf",
                    "hash": page_hash
                }
                documents.append(Document(page_content=text, metadata=metadata))
            
    return documents

async def load_pdf(file_path: str) -> List[Document]:
    """Asynchronously load a PDF and extract its text and tables."""
    return await asyncio.to_thread(_process_pdf_sync, file_path)

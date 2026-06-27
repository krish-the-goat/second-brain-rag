import os
import uuid
import tempfile
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from app.rag.loaders.pdf_loader import load_pdf
from app.rag.loaders.docx_loader import load_docx
from app.rag.loaders.web_loader import load_web
from app.rag.chunkers.recursive_chunker import chunk_documents
from app.rag.embeddings.gemini_embedder import embed_documents
from app.rag.vectorstore.chroma_store import add_documents, list_documents, delete_document
from app.core.exceptions import UnsupportedFormatError, DocumentTooLargeError
from app.core.cache import get_cache, set_cache

router = APIRouter(prefix="/documents", tags=["Documents"])

class URLUploadRequest(BaseModel):
    url: str

async def _process_file(file_path: str, filename: str, content_type: str, job_id: str):
    await set_cache(f"job:{job_id}", "processing")
    try:
        content_type_lower = content_type.lower()
        filename_lower = filename.lower()
        if "pdf" in content_type_lower or filename_lower.endswith(".pdf"):
            docs = await load_pdf(file_path)
        elif "word" in content_type_lower or "docx" in content_type_lower or filename_lower.endswith(".docx"):
            docs = await load_docx(file_path)
        else:
            raise UnsupportedFormatError(f"Unsupported format for {filename}")
            
        for doc in docs:
            doc.metadata["filename"] = filename
            
        chunks = chunk_documents(docs)
        if chunks:
            texts = [c.page_content for c in chunks]
            metadatas = [c.metadata for c in chunks]
            
            # Embed and add to Dense Store (Chroma)
            embeddings = await embed_documents(texts)
            await add_documents(texts, embeddings, metadatas)
            
            # Add to Sparse Store (BM25)
            from app.rag.vectorstore.bm25_store import get_bm25_store
            bm25_docs = []
            for i, text in enumerate(texts):
                # Use the deterministic hash we generated in chunker as the ID to sync with Chroma
                doc_id = metadatas[i].get("hash", f"{job_id}_{i}")
                bm25_docs.append({"id": doc_id, "text": text})
            get_bm25_store().add_documents(bm25_docs)

            
        await set_cache(f"job:{job_id}", "completed")
    except Exception as e:
        await set_cache(f"job:{job_id}", f"failed: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def _process_url(url: str, job_id: str):
    await set_cache(f"job:{job_id}", "processing")
    try:
        docs = await load_web(url)
        chunks = chunk_documents(docs)
        if chunks:
            texts = [c.page_content for c in chunks]
            metadatas = [c.metadata for c in chunks]
            embeddings = await embed_documents(texts)
            await add_documents(texts, embeddings, metadatas)
            
            # Add to Sparse Store (BM25)
            from app.rag.vectorstore.bm25_store import get_bm25_store
            bm25_docs = []
            for i, text in enumerate(texts):
                doc_id = metadatas[i].get("hash", f"{job_id}_{i}")
                bm25_docs.append({"id": doc_id, "text": text})
            get_bm25_store().add_documents(bm25_docs)
        await set_cache(f"job:{job_id}", "completed")
    except Exception as e:
        await set_cache(f"job:{job_id}", f"failed: {str(e)}")

@router.post("/upload")
async def upload_document(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
    
    if not file.filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")
        
    job_id = str(uuid.uuid4())
    fd, temp_path = tempfile.mkstemp()
    total_size = 0
    
    try:
        with open(temp_path, "wb") as f:
            while chunk := await file.read(8192):
                total_size += len(chunk)
                if total_size > max_size:
                    os.close(fd)
                    os.remove(temp_path)
                    raise DocumentTooLargeError(f"File exceeds max size of {max_size} bytes")
                f.write(chunk)
        os.close(fd)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e
        
    background_tasks.add_task(_process_file, temp_path, file.filename, file.content_type, job_id)
    return {"job_id": job_id, "status": "processing"}

@router.post("/url")
async def upload_url(request: URLUploadRequest, background_tasks: BackgroundTasks, req: Request):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_process_url, request.url, job_id)
    return {"job_id": job_id, "status": "processing"}

@router.get("")
async def get_documents(request: Request):
    docs = await list_documents()
    return {"documents": docs}

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, request: Request):
    status = await get_cache(f"job:{job_id}")
    if not status:
        status = "unknown"
    return {"job_id": job_id, "status": status}

@router.delete("/{doc_id}")
async def delete_doc(doc_id: str, request: Request):
    await delete_document(doc_id)
    return {"status": "deleted"}

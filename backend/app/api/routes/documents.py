import os
import uuid
import tempfile
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any

from app.rag.loaders.pdf_loader import load_pdf
from app.rag.loaders.docx_loader import load_docx
from app.rag.loaders.web_loader import load_web
from app.rag.chunkers.recursive_chunker import chunk_documents
from app.rag.embeddings.local_embedder import embed_documents
from app.rag.vectorstore.chroma_store import add_documents, list_documents, delete_document
from app.core.exceptions import UnsupportedFormatError, DocumentTooLargeError
from app.core.cache import get_cache, set_cache
from app.core.rate_limit import limiter

router = APIRouter(prefix="/documents", tags=["Documents"])

class URLUploadRequest(BaseModel):
    url: HttpUrl = Field(..., max_length=2048)

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
            from app.rag.graph.graph_extractor import extract_and_store_graph
            import asyncio
            
            bm25_docs = []
            graph_tasks = []
            
            for i, text in enumerate(texts):
                doc_id = metadatas[i].get("hash", f"{job_id}_{i}")
                bm25_docs.append({"id": doc_id, "text": text})
                
                # Extract graph only from the first few chunks to save LLM quota for testing
                if i < 3: 
                    parent_text = metadatas[i].get("parent_content", text)
                    graph_tasks.append(extract_and_store_graph(parent_text))
                    
            get_bm25_store().add_documents(bm25_docs)
            
            # Fire and await graph extraction tasks
            if graph_tasks:
                await asyncio.gather(*graph_tasks, return_exceptions=True)

            
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
            from app.rag.graph.graph_extractor import extract_and_store_graph
            import asyncio
            
            bm25_docs = []
            graph_tasks = []
            
            for i, text in enumerate(texts):
                doc_id = metadatas[i].get("hash", f"{job_id}_{i}")
                bm25_docs.append({"id": doc_id, "text": text})
                
                if i < 3: 
                    parent_text = metadatas[i].get("parent_content", text)
                    graph_tasks.append(extract_and_store_graph(parent_text))
                    
            get_bm25_store().add_documents(bm25_docs)
            
            if graph_tasks:
                await asyncio.gather(*graph_tasks, return_exceptions=True)
        await set_cache(f"job:{job_id}", "completed")
    except Exception as e:
        await set_cache(f"job:{job_id}", f"failed: {str(e)}")

@router.post("/upload")
@limiter.limit("3/minute")
async def upload_document(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    import magic
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
    
    safe_filename = os.path.basename(file.filename)
    if not safe_filename.endswith((".pdf", ".docx")):
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
        
        mime = magic.from_file(temp_path, mime=True)
        if mime not in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="Invalid file type detected.")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e
        
    background_tasks.add_task(_process_file, temp_path, safe_filename, file.content_type, job_id)
    return {"job_id": job_id, "status": "processing"}

@router.post("/url")
@limiter.limit("2/minute")
async def upload_url(body: URLUploadRequest, background_tasks: BackgroundTasks, request: Request):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_process_url, str(body.url), job_id)
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

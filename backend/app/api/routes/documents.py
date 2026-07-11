import os
import uuid
import tempfile
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any

from app.rag.vectorstore.chroma_store import list_documents, delete_document
from app.core.exceptions import DocumentTooLargeError
from app.core.cache import get_cache
from app.core.rate_limit import limiter
from app.rag.ingestion import ingestion_pipeline

router = APIRouter(prefix="/documents", tags=["Documents"])


class URLUploadRequest(BaseModel):
    url: HttpUrl = Field(..., max_length=2048)


@router.post("/upload")
@limiter.limit("3/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    import magic

    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024

    safe_filename = os.path.basename(file.filename or "")
    if not safe_filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    job_id = str(uuid.uuid4())

    fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(safe_filename)[1])
    try:
        total_size = 0
        with os.fdopen(fd, "wb") as f:
            while chunk := await file.read(8192):
                total_size += len(chunk)
                if total_size > max_size:
                    raise DocumentTooLargeError(
                        f"File exceeds maximum size of {max_size // (1024 * 1024)}MB"
                    )
                f.write(chunk)

        mime = magic.from_file(temp_path, mime=True)
        allowed_mimes = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        if mime not in allowed_mimes:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"Invalid file type detected: {mime}")

    except DocumentTooLargeError:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

    background_tasks.add_task(
        ingestion_pipeline.process_file, temp_path, safe_filename, file.content_type or "", job_id
    )
    return {"job_id": job_id, "status": "processing"}


@router.post("/url")
@limiter.limit("2/minute")
async def upload_url(
    body: URLUploadRequest,
    background_tasks: BackgroundTasks,
    request: Request,
):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(ingestion_pipeline.process_url, str(body.url), job_id)
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
    from app.rag.vectorstore.bm25_store import get_bm25_store
    from app.rag.vectorstore.chroma_store import delete_document, get_document_parents
    from app.core.cache import delete_cache
    import structlog
    
    logger = structlog.get_logger(__name__)
    
    # Clean up parent chunks from Redis
    parents = await get_document_parents(doc_id)
    for p_id in parents:
        await delete_cache(f"parent:{p_id}")
        
    await delete_document(doc_id)
    get_bm25_store().delete_documents_by_doc_id(doc_id)
    
    logger.info("Document deleted", doc_id=doc_id)
    return {"status": "deleted"}

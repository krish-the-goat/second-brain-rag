import os
import time
import uuid
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.routes import documents, chat, health, metrics
from app.core.exceptions import ProcessingError, UnsupportedFormatError, DocumentTooLargeError, ScrapingError
from app.core.logging import setup_logging
from app.core.cache import init_cache, close_cache, increment_metric, get_metric

# Initialize structlog first
setup_logging()
logger = structlog.get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Second Brain RAG...")
    await init_cache()
    
    from app.rag.vectorstore.chroma_store import get_stats
    try:
        stats = get_stats()
        logger.info("ChromaDB connected", stats=stats)
    except Exception as e:
        logger.error("ChromaDB connection failed", error=str(e))
            
    yield
    await close_cache()
    logger.info("Shutting down...")

app = FastAPI(title="Second Brain RAG API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000.0
    
    response.headers["X-Request-ID"] = request_id
    
    logger.info("HTTP Request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms)
                
    # Update average response time metric
    current_avg = await get_metric("avg_response_time_ms")
    total_reqs = await get_metric("total_http_requests")
    
    new_avg = ((current_avg * total_reqs) + duration_ms) / (total_reqs + 1)
    # Cache doesn't have a direct "set" for metrics except increment, but we can use set_cache
    from app.core.cache import set_cache
    await set_cache("avg_response_time_ms", new_avg)
    await increment_metric("total_http_requests", 1)
    
    return response

def build_rfc_7807(status: int, title: str, detail: str, req: Request):
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": str(req.url)
        }
    )

@app.exception_handler(ProcessingError)
async def processing_exception_handler(request: Request, exc: ProcessingError):
    return build_rfc_7807(400, "Processing Error", str(exc), request)

@app.exception_handler(DocumentTooLargeError)
async def doc_large_exception_handler(request: Request, exc: DocumentTooLargeError):
    return build_rfc_7807(413, "Payload Too Large", str(exc), request)

@app.exception_handler(UnsupportedFormatError)
async def unsupported_format_exception_handler(request: Request, exc: UnsupportedFormatError):
    return build_rfc_7807(415, "Unsupported Media Type", str(exc), request)

@app.exception_handler(ScrapingError)
async def scraping_exception_handler(request: Request, exc: ScrapingError):
    return build_rfc_7807(502, "Bad Gateway", str(exc), request)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc))
    if hasattr(exc, "status_code"):
        return build_rfc_7807(exc.status_code, "HTTP Error", getattr(exc, "detail", str(exc)), request)
    return build_rfc_7807(500, "Internal Server Error", "An unexpected error occurred.", request)

app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(documents.router)
app.include_router(chat.router)

@app.get("/")
async def root(request: Request):
    return {"message": "Welcome to Second Brain RAG API"}

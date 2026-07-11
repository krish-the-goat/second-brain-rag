import os
import asyncio
import structlog
from typing import List
from langchain_core.documents import Document

from app.rag.loaders.pdf_loader import load_pdf
from app.rag.loaders.docx_loader import load_docx
from app.rag.loaders.web_loader import load_web
from app.rag.chunkers.recursive_chunker import chunk_documents
from app.rag.embeddings.local_embedder import embed_documents
from app.rag.vectorstore.chroma_store import add_documents
from app.core.exceptions import UnsupportedFormatError
from app.core.cache import set_cache

logger = structlog.get_logger(__name__)

class IngestionPipeline:
    @staticmethod
    async def process_file(file_path: str, filename: str, content_type: str, job_id: str):
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

            await IngestionPipeline._process_docs(docs, job_id, filename)

            await set_cache(f"job:{job_id}", "completed")

        except Exception as e:
            logger.error(f"Ingestion failed for file {filename}: {e}")
            await set_cache(f"job:{job_id}", f"failed: {str(e)}")
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass

    @staticmethod
    async def process_url(url: str, job_id: str):
        await set_cache(f"job:{job_id}", "processing")
        try:
            docs = await load_web(url)
            await IngestionPipeline._process_docs(docs, job_id, url)
            await set_cache(f"job:{job_id}", "completed")
        except Exception as e:
            logger.error(f"Ingestion failed for URL {url}: {e}")
            await set_cache(f"job:{job_id}", f"failed: {str(e)}")

    @staticmethod
    async def _process_docs(docs: List[Document], job_id: str, source_id: str):
        chunks, parent_store = chunk_documents(docs)
        if not chunks:
            return

        for p_id, p_text in parent_store.items():
            await set_cache(f"parent:{p_id}", p_text, ttl=None)

        texts = [c.page_content for c in chunks]
        metadatas = [c.metadata for c in chunks]

        embeddings = await embed_documents(texts)
        await add_documents(texts, embeddings, metadatas)

        from app.rag.vectorstore.bm25_store import get_bm25_store
        from app.rag.graph.graph_extractor import extract_and_store_graph

        bm25_docs = []
        graph_texts = []

        for i, text in enumerate(texts):
            doc_id = metadatas[i].get("hash", f"{job_id}_{i}")
            bm25_docs.append({"id": doc_id, "text": text, "doc_id": source_id})
            if i < 3:
                parent_text = metadatas[i].get("parent_content", text)
                graph_texts.append(parent_text)

        get_bm25_store().add_documents(bm25_docs)

        sem = asyncio.Semaphore(2)
        async def bounded_extract(t: str):
            async with sem:
                try:
                    await extract_and_store_graph(t)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Graph extraction failed (non-fatal): {e}")

        if graph_texts:
            await asyncio.gather(*(bounded_extract(t) for t in graph_texts))

ingestion_pipeline = IngestionPipeline()

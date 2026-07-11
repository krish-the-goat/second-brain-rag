import asyncio
import os
import sys

# Ensure backend directory is in the python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.rag.ingestion import IngestionPipeline

async def main():
    print("Ingesting sample documents into local stores...")
    pipeline = IngestionPipeline()
    
    docs = [
        "sample_docs/sample_1_acme_handbook.pdf",
        "sample_docs/sample_2_quantum_specs.pdf"
    ]
    
    for doc in docs:
        if os.path.exists(doc):
            try:
                filename = os.path.basename(doc)
                content_type = "application/pdf" if doc.endswith(".pdf") else "application/msword"
                await pipeline.process_file(doc, filename, content_type, job_id="test_job")
                print(f"Successfully ingested {doc}")
            except Exception as e:
                print(f"Failed to ingest {doc}: {e}")
        else:
            print(f"File not found: {doc}")

if __name__ == "__main__":
    asyncio.run(main())

# 🧠 Second Brain RAG

A production-grade **Retrieval-Augmented Generation (RAG)** application built to act as your personal "Second Brain". Upload your college notes, PDFs, Word documents, and Web URLs, and instantly chat with your knowledge base. The AI provides highly accurate answers by retrieving the exact context from your documents without hallucinating.

## ✨ Features

- **Advanced RAG Pipeline:** Utilizes **Hybrid Search** (ChromaDB Dense + BM25 Sparse) combined with **Reciprocal Rank Fusion (RRF)** and **Cross-Encoder Reranking** for unparalleled retrieval accuracy.
- **Graph RAG Augmentation:** Automatically extracts Knowledge Graphs (Entities & Relationships) using LLMs and stores them in **Neo4j** to provide multi-hop relational context to your queries.
- **Document Ingestion:** Drag-and-drop support for PDFs and DOCX files, plus URL web scraping with SSRF protection.
- **Smart Chunking:** Uses Parent-Child chunking strategies to retrieve highly specific snippets while feeding broad context to the LLM.
- **Chat Interface:** A premium, ChatGPT-like chat interface with Server-Sent Events (SSE) for real-time typing/streaming of AI responses, complete with precise document citations.
- **Production-Ready Backend:** Fully asynchronous FastAPI backend featuring `gunicorn` concurrency, rate limiting, IP validation, API Key authentication, and protection against Cypher & Prompt Injection attacks.

## 🛠️ Tech Stack

**Frontend:**
- React (TypeScript) + Vite
- React Query & Axios
- Custom Glassmorphism CSS & Tailwind

**Backend & Infra:**
- Python 3.12 & FastAPI
- **LLM:** OpenRouter (Gemini 2.5 Flash / Claude)
- **Embeddings:** Local `SentenceTransformers` (`all-MiniLM-L6-v2`)
- **Vector DB:** ChromaDB (Client/Server Mode)
- **Graph DB:** Neo4j
- **Deployment:** Docker Compose, Nginx (SSE optimized), Gunicorn (4 workers)

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/krish-the-goat/second-brain-rag.git
cd second-brain-rag
```

### 2. Environment Variables
Create a `.env` file in the root of the project:
```env
OPENROUTER_API_KEY="your_api_key_here"
API_KEY="your_secure_backend_api_key"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your_secure_password"
```
*(Also add `VITE_API_KEY="your_secure_backend_api_key"` in `frontend/.env`)*

### 3. Production Deployment (Docker)
The easiest way to run the entire stack (FastAPI, Nginx, Neo4j, ChromaDB):
```bash
chmod +x deploy.sh
./deploy.sh
```
The app will be available at `http://localhost`.

### 4. Local Development
**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 📂 Project Architecture

- `/frontend` - React application source code.
- `/backend` - FastAPI server, RAG pipeline, loaders, chunkers, and ChromaDB/Neo4j logic.
- `/evaluation` - Scripts to evaluate the Context Recall and Answer Accuracy of the RAG pipeline.

## 🤝 Contribution
Feel free to open issues and pull requests to enhance the capabilities of this Second Brain RAG system!

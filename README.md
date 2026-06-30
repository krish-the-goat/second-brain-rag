# 🧠 Second Brain RAG

Welcome to **Second Brain RAG**! I built this project to solve a very real problem: we all have way too many PDFs, DOCX files, and web bookmarks scattered around, and finding specific information inside them is a nightmare. 

Instead of just building another generic wrapper around an LLM, I engineered a production-grade, highly secure **Retrieval-Augmented Generation (RAG)** system. You can feed it your documents, and it acts as your personal "Second Brain" — answering questions accurately by extracting exactly what you need, with precise citations, and zero hallucinations.

---

## 🔥 Why This Stands Out

This isn't just a basic semantic search script. It's packed with heavy engineering to make it fast, reliable, and practically bulletproof:

*   **Advanced Hybrid RAG Pipeline:** We don't just rely on vectors. This system uses **Dense Search (ChromaDB)** + **Sparse Keyword Search (BM25)**, combined with **Reciprocal Rank Fusion (RRF)**. It then pipes the results through a **Local Cross-Encoder** to rerank and surface the absolute best context.
*   **GraphRAG Augmentation:** As you upload documents, the system uses LLMs to extract entities and relationships, building a live Knowledge Graph in **Neo4j**. When you ask a question, it traverses this graph to provide multi-hop relational context!
*   **Multi-Provider LLM Fallback (Zero Downtime):** AI APIs drop constantly. If the primary provider (Gemini 2.5) hits a rate limit (429) or fails, the `LLMManager` instantly hot-swaps the payload format and falls back to **Groq (LLaMa 3.3 70B)** mid-stream without the user ever noticing.
*   **Military-Grade Security (OWASP Top 10 LLM 2025):** I took security very seriously.
    *   **Prompt Injection Defense:** User queries are strictly isolated in XML `<USER_QUERY>` tags with hardcoded behavioral boundaries.
    *   **DoS & Zip Bomb Protection:** Strict limits on PDF pages (500) and DOCX paragraphs (10,000) to prevent memory exhaustion (OOM) attacks.
    *   **SSRF Protection:** Web scraping explicitly resolves hostnames and drops local/private IPs (AWS metadata, localhost).
    *   **Data Isolation:** All database ports (Redis, Neo4j, Chroma) are strictly locked down to localhost to prevent external network exposure.
*   **Premium Chat UI:** A sleek, glassmorphism React interface featuring Server-Sent Events (SSE) for real-time text streaming, complete with clickable document citations.

---

## 🛠️ Tech Stack

*   **Frontend:** React (TypeScript), Vite, React Query, Tailwind CSS, Lucide Icons.
*   **Backend:** Python 3.12, FastAPI (Async), Gunicorn.
*   **LLMs:** Google Gemini (Primary) & Groq / LLaMa 3 (Fallback).
*   **Embeddings & Reranking:** Local `SentenceTransformers` (`all-MiniLM-L6-v2` & `ms-marco-MiniLM-L-6-v2`) — totally free and private.
*   **Databases:** ChromaDB (Vectors), Neo4j (Graph), Redis (Caching & Rate Limiting).
*   **Infrastructure:** Fully containerized with Docker Compose.

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/krish-the-goat/second-brain-rag.git
cd second-brain-rag
```

### 2. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Make sure to add your Google API key, Groq API key, and choose strong passwords for the databases.

### 3. Spin it up (Docker)
The absolute easiest way to run the entire stack is via Docker Compose:
```bash
docker-compose up -d --build
```
Once the containers are running, open your browser and go to `http://localhost:5173`. Boom, your Second Brain is ready!

---

## 🧠 How the RAG Pipeline Actually Works

If you're curious about what happens when you type a question:
1. **Query Intent:** The system takes your question and embeds it locally.
2. **Retrieval:** It searches ChromaDB (meaning/semantics) and the local BM25 store (exact keyword matches).
3. **Graph Search:** Simultaneously, it queries Neo4j for any 1-hop relationships connected to the entities in your question.
4. **Reranking:** The Dense and Sparse results are fused and reranked using a local Cross-Encoder to guarantee the best 5 chunks.
5. **Prompt Engineering:** The reranked chunks and graph context are carefully pruned and injected into a strict `SECURITY DIRECTIVE` prompt.
6. **Generation:** The payload is sent to Gemini (or Groq if Gemini fails), and the response is streamed directly back to your React UI via Server-Sent Events.

---

## 🤝 Contributing

I built this as a robust foundation, but there is always room for improvement! If you want to add RBAC (Role-Based Access Control) for multiple users, or implement multi-modal document parsing, feel free to open a PR or an issue. 

*Happy Hacking!* 🚀

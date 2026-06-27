# 🧠 Second Brain RAG

A production-grade **Retrieval-Augmented Generation (RAG)** application built to act as your personal "Second Brain". Upload your college notes, PDFs, and Word documents, and instantly chat with your knowledge base. The AI provides highly accurate answers by retrieving the exact context from your documents without hallucinating.

## ✨ Features

- **Document Ingestion:** Drag-and-drop support for PDFs and DOCX files.
- **Smart Chunking:** Uses LangChain's `RecursiveCharacterTextSplitter` to smartly chunk text without losing semantic context.
- **Vector Search Engine:** Embeddings are generated using **Gemini** and securely stored and queried in **ChromaDB**.
- **Chat Interface:** A premium, ChatGPT-like chat interface with Server-Sent Events (SSE) for real-time typing/streaming of AI responses.
- **Modern Aesthetics:** Built with a beautiful Dark Mode & Glassmorphism UI using React and Tailwind CSS.
- **Production-Ready Backend:** Fully asynchronous FastAPI backend featuring background tasks for file processing, Redis-ready caching, and custom evaluation endpoints.

## 🛠️ Tech Stack

**Frontend:**
- React (TypeScript)
- Vite
- Tailwind CSS
- Lucide React (Icons)
- React Query & Axios

**Backend:**
- Python 3.12 & FastAPI
- ChromaDB (Vector Database)
- Google Generative AI (Gemini)
- LangChain (for Text Splitters)
- PyPDF2, pdfplumber & python-docx (Document Parsing)

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/krish-the-goat/second-brain-rag.git
cd second-brain-rag
```

### 2. Backend Setup
Navigate to the backend directory and set up the Python environment:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the root of the project (copy from `.env.example`):
```bash
cp ../.env.example ../.env
```
Add your Gemini API Key in the `.env` file:
```env
GEMINI_API_KEY="your_api_key_here"
```

Start the FastAPI server:
```bash
# Make sure you are in the root directory or point PYTHONPATH correctly
uvicorn app.main:app --reload
```
The backend will run on `http://localhost:8000`.

### 3. Frontend Setup
Open a new terminal window and navigate to the frontend directory:
```bash
cd frontend
npm install
npm run dev
```
The frontend will run on `http://localhost:5173`.

## 📂 Project Architecture

- `/frontend` - React application source code.
- `/backend` - FastAPI server, including routes, RAG pipeline, loaders, chunkers, and ChromaDB logic.
- `/evaluation` - Scripts to evaluate the Context Recall and Answer Accuracy of the RAG pipeline.

## 🤝 Contribution
Feel free to open issues and pull requests to enhance the capabilities of this Second Brain RAG system!

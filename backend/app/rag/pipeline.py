import os
import structlog
from typing import List, Dict, Any, AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.rag.embeddings.gemini_embedder import embed_documents
from app.rag.vectorstore.chroma_store import query
from app.core.cache import increment_metric

logger = structlog.get_logger(__name__)

class RAGPipeline:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="models/gemini-2.0-flash", convert_system_message_to_human=True)

    async def _retrieve_context(self, question: str) -> tuple[List[Dict], float, float]:
        import time
        t0 = time.time()
        embeddings = await embed_documents([question])
        embedding_ms = (time.time() - t0) * 1000
        
        if not embeddings:
            return [], embedding_ms, 0.0
        
        query_emb = embeddings[0]
        threshold = float(os.getenv("SCORE_THRESHOLD", "0.7"))
        
        t1 = time.time()
        results = await query(query_emb, n_results=5, score_threshold=threshold)
        retrieval_ms = (time.time() - t1) * 1000
        
        return results, embedding_ms, retrieval_ms

    def _build_messages(self, question: str, chat_history: List[Dict], context_results: List[Dict]) -> List:
        context_text = "\n\n---\n\n".join([r["text"] for r in context_results])
        
        system_prompt = "You are a helpful assistant. Answer ONLY from the provided context. If unsure, say so.\n\nContext:\n" + context_text
        
        messages = [SystemMessage(content=system_prompt)]
        
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
                
        messages.append(HumanMessage(content=question))
        return messages

    def _format_citations(self, context_results: List[Dict]) -> List[Dict]:
        citations = []
        for r in context_results:
            meta = r.get("metadata", {})
            excerpt = r.get("text", "")[:200]
            citations.append({
                "filename": meta.get("filename", meta.get("url", "unknown")),
                "page_number": meta.get("page_number", meta.get("section", 1)),
                "excerpt": excerpt,
                "score": r.get("score", 0.0)
            })
        return citations

    async def _log_and_track_metrics(self, question: str, context_results: List[Dict], tokens_used: int):
        avg_score = 0.0
        if context_results:
            avg_score = sum(r.get("score", 0.0) for r in context_results) / len(context_results)
            
        cost_usd = (tokens_used / 1_000_000) * 1.25 # Approximation
        
        logger.info("RAG Query Executed",
                    question_length=len(question),
                    retrieval_count=len(context_results),
                    avg_score=avg_score,
                    tokens_used=tokens_used,
                    cost_usd=cost_usd)
                    
        await increment_metric("queries_today", 1)
        await increment_metric("total_tokens_used", tokens_used)
        await increment_metric("estimated_cost_usd", cost_usd)

    async def ask(self, question: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        import time
        t_start = time.time()
        if chat_history is None:
            chat_history = []
            
        context_results, embedding_ms, retrieval_ms = await self._retrieve_context(question)
        
        if os.getenv("MOCK_LLM", "false").lower() == "true":
            return {
                "answer": "Mocked answer due to API quota limits.",
                "citations": self._format_citations(context_results),
                "tokens_used": 10
            }
        
        messages = self._build_messages(question, chat_history, context_results)
        
        t1 = time.time()
        response = await self.llm.ainvoke(messages)
        generation_ms = (time.time() - t1) * 1000
        
        tokens_used = 0
        if response.response_metadata and "token_usage" in response.response_metadata:
            tokens_used = response.response_metadata["token_usage"].get("total_tokens", 0)
            
        await self._log_and_track_metrics(question, context_results, tokens_used)
            
        total_ms = (time.time() - t_start) * 1000
        return {
            "answer": response.content,
            "citations": self._format_citations(context_results),
            "tokens_used": tokens_used,
            "timings": {
                "embedding_ms": embedding_ms,
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
                "total_ms": total_ms
            }
        }

    async def ask_stream(self, question: str, chat_history: List[Dict] = None) -> AsyncGenerator[str, None]:
        import json
        if chat_history is None:
            chat_history = []
            
        context_results, _, _ = await self._retrieve_context(question)
        messages = self._build_messages(question, chat_history, context_results)
        
        tokens_used = 0
        
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                yield f"data: {json.dumps({'text': chunk.content})}\n\n"
                
        # Typically token usage isn't fully supported in astream across all providers 
        # But we will track a minimum approximation for streaming cost (1 token per ~4 chars output + input)
        approx_input = sum(len(m.content) for m in messages) // 4
        tokens_used = approx_input + 50 # rough estimate since stream usage data isn't robustly standardized
        await self._log_and_track_metrics(question, context_results, tokens_used)
        
        citations = self._format_citations(context_results)
        yield f"data: {json.dumps({'citations': citations, 'tokens_used': tokens_used})}\n\n"
        yield "data: [DONE]\n\n"

pipeline = RAGPipeline()

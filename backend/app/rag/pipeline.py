import os
import time
import json
import httpx
import asyncio
import structlog
from typing import List, Dict, Any, AsyncGenerator

from app.rag.retrievers.hybrid_retriever import hybrid_search
from app.rag.graph.graph_retriever import retrieve_graph_context
from app.rag.context_engineering import prune_irrelevant_context, build_dynamic_prompt
from app.core.cache import increment_metric

logger = structlog.get_logger(__name__)

class RAGPipeline:
    def __init__(self):
        # We will dynamically fetch this during requests
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "Second Brain RAG",
            "Content-Type": "application/json"
        }

    async def _retrieve_all_context(self, question: str) -> tuple[List[Dict], str, float]:
        t0 = time.time()
        
        hybrid_task = asyncio.create_task(hybrid_search(question, top_k=5))
        graph_task = asyncio.create_task(retrieve_graph_context(question))
        
        hybrid_results, graph_context = await asyncio.gather(hybrid_task, graph_task)
        
        threshold = float(os.getenv("RERANK_THRESHOLD", "-5.0"))
        pruned_hybrid = prune_irrelevant_context(hybrid_results, threshold=threshold)
        
        retrieval_ms = (time.time() - t0) * 1000
        return pruned_hybrid, graph_context, retrieval_ms

    def _build_messages(self, question: str, chat_history: List[Dict], hybrid_results: List[Dict], graph_context: str) -> List[Dict]:
        system_prompt = build_dynamic_prompt(hybrid_results, graph_context, max_tokens=4000)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in chat_history:
            if msg.get("role") in ["user", "assistant"]:
                messages.append({"role": msg.get("role"), "content": msg.get("content", "")})
                
        messages.append({"role": "user", "content": question})
        return messages

    def _format_citations(self, context_results: List[Dict]) -> List[Dict]:
        citations = []
        for r in context_results:
            text = r.get("parent_content", r.get("text", ""))[:200]
            citations.append({
                "filename": r.get("filename", "unknown"),
                "excerpt": text,
                "score": r.get("rerank_score", r.get("score", 0.0))
            })
        return citations

    async def _log_and_track_metrics(self, question: str, context_results: List[Dict], tokens_used: int):
        avg_score = sum(r.get("rerank_score", r.get("score", 0.0)) for r in context_results) / max(len(context_results), 1)
        cost_usd = (tokens_used / 1_000_000) * 1.25
        
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
        t_start = time.time()
        if chat_history is None: chat_history = []
            
        hybrid_results, graph_context, retrieval_ms = await self._retrieve_all_context(question)
        messages = self._build_messages(question, chat_history, hybrid_results, graph_context)
        
        payload = {
            "model": "google/gemini-2.5-flash",
            "messages": messages
        }
        
        t1 = time.time()
        answer = ""
        tokens_used = 0
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, headers=self._get_headers(), json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)
        except Exception as e:
            logger.error(f"OpenRouter API failed: {e}")
            answer = f"Error generating answer: {e}"
            
        generation_ms = (time.time() - t1) * 1000
        
        if tokens_used == 0:
            tokens_used = (len("".join(m["content"] for m in messages)) + len(answer)) // 4
            
        await self._log_and_track_metrics(question, hybrid_results, tokens_used)
            
        return {
            "answer": answer,
            "citations": self._format_citations(hybrid_results),
            "tokens_used": tokens_used,
            "timings": {
                "embedding_ms": 0,
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
                "total_ms": (time.time() - t_start) * 1000
            }
        }

    async def ask_stream(self, question: str, chat_history: List[Dict] = None) -> AsyncGenerator[str, None]:
        if chat_history is None: chat_history = []
            
        hybrid_results, graph_context, _ = await self._retrieve_all_context(question)
        messages = self._build_messages(question, chat_history, hybrid_results, graph_context)
        
        payload = {
            "model": "google/gemini-2.5-flash",
            "messages": messages,
            "stream": True
        }
        
        tokens_used = (sum(len(m["content"]) for m in messages)) // 4
        generated_chars = 0
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", self.api_url, headers=self._get_headers(), json=payload, timeout=30.0) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    generated_chars += len(content)
                                    yield f"data: {json.dumps({'text': content})}\n\n"
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"OpenRouter stream failed: {e}")
            yield f"data: {json.dumps({'text': f'Error: {e}'})}\n\n"
            
        tokens_used += generated_chars // 4
        await self._log_and_track_metrics(question, hybrid_results, tokens_used)
        
        citations = self._format_citations(hybrid_results)
        yield f"data: {json.dumps({'citations': citations, 'tokens_used': tokens_used})}\n\n"
        yield "data: [DONE]\n\n"

pipeline = RAGPipeline()

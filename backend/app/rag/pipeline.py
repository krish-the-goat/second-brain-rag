import os
import time
import asyncio
import structlog
from typing import List, Dict, Any, AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.rag.retrievers.hybrid_retriever import hybrid_search
from app.rag.graph.graph_retriever import retrieve_graph_context
from app.rag.context_engineering import prune_irrelevant_context, build_dynamic_prompt
from app.core.cache import increment_metric

logger = structlog.get_logger(__name__)

class RAGPipeline:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="models/gemini-2.0-flash", convert_system_message_to_human=True)

    async def _retrieve_all_context(self, question: str) -> tuple[List[Dict], str, float]:
        """
        Executes Hybrid Search and Graph Retrieval in parallel.
        Prunes irrelevant hybrid chunks.
        """
        t0 = time.time()
        
        # Parallel execution of Graph and Hybrid retrievers
        hybrid_task = asyncio.create_task(hybrid_search(question, top_k=5))
        graph_task = asyncio.create_task(retrieve_graph_context(question))
        
        hybrid_results, graph_context = await asyncio.gather(hybrid_task, graph_task)
        
        # Context Engineering: Pruning
        threshold = float(os.getenv("RERANK_THRESHOLD", "-5.0")) # MiniLM threshold tuning
        pruned_hybrid = prune_irrelevant_context(hybrid_results, threshold=threshold)
        
        retrieval_ms = (time.time() - t0) * 1000
        return pruned_hybrid, graph_context, retrieval_ms

    def _build_messages(self, question: str, chat_history: List[Dict], hybrid_results: List[Dict], graph_context: str) -> List:
        # Context Engineering: Dynamic prompt construction and token budgeting
        system_prompt = build_dynamic_prompt(hybrid_results, graph_context, max_tokens=4000)
        
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
            # We use parent_content if it exists, otherwise child text
            text = r.get("parent_content", r.get("text", ""))[:200]
            citations.append({
                "filename": r.get("filename", "unknown"),
                "excerpt": text,
                "score": r.get("rerank_score", r.get("score", 0.0))
            })
        return citations

    async def _log_and_track_metrics(self, question: str, context_results: List[Dict], tokens_used: int):
        avg_score = 0.0
        if context_results:
            avg_score = sum(r.get("rerank_score", r.get("score", 0.0)) for r in context_results) / len(context_results)
            
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
        t_start = time.time()
        if chat_history is None:
            chat_history = []
            
        hybrid_results, graph_context, retrieval_ms = await self._retrieve_all_context(question)
        
        if os.getenv("MOCK_LLM", "false").lower() == "true":
            return {
                "answer": f"Mocked Advanced RAG answer. Graph Context found: {bool(graph_context)}. Hybrid chunks: {len(hybrid_results)}.",
                "citations": self._format_citations(hybrid_results),
                "tokens_used": 10
            }
        
        messages = self._build_messages(question, chat_history, hybrid_results, graph_context)
        
        t1 = time.time()
        response = await self.llm.ainvoke(messages)
        generation_ms = (time.time() - t1) * 1000
        
        tokens_used = 0
        if response.response_metadata and "token_usage" in response.response_metadata:
            tokens_used = response.response_metadata["token_usage"].get("total_tokens", 0)
            
        await self._log_and_track_metrics(question, hybrid_results, tokens_used)
            
        total_ms = (time.time() - t_start) * 1000
        return {
            "answer": response.content,
            "citations": self._format_citations(hybrid_results),
            "tokens_used": tokens_used,
            "timings": {
                "embedding_ms": 0, # Included in retrieval_ms now
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
                "total_ms": total_ms
            }
        }

    async def ask_stream(self, question: str, chat_history: List[Dict] = None) -> AsyncGenerator[str, None]:
        import json
        if chat_history is None:
            chat_history = []
            
        hybrid_results, graph_context, _ = await self._retrieve_all_context(question)
        messages = self._build_messages(question, chat_history, hybrid_results, graph_context)
        
        tokens_used = 0
        
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                yield f"data: {json.dumps({'text': chunk.content})}\n\n"
                
        approx_input = sum(len(m.content) for m in messages) // 4
        tokens_used = approx_input + 50 
        await self._log_and_track_metrics(question, hybrid_results, tokens_used)
        
        citations = self._format_citations(hybrid_results)
        yield f"data: {json.dumps({'citations': citations, 'tokens_used': tokens_used})}\n\n"
        yield "data: [DONE]\n\n"

pipeline = RAGPipeline()

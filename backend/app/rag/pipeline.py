import os
import time
import json
import httpx
import asyncio
import structlog
import hashlib
from typing import List, Dict, Any, AsyncGenerator

from app.rag.retrievers.hybrid_retriever import hybrid_search
from app.rag.graph.graph_retriever import retrieve_graph_context
from app.rag.context_engineering import prune_irrelevant_context, build_dynamic_prompt
from app.core.cache import increment_metric, get_cache, set_cache
from app.core.llm_manager import llm_manager
from app.core.logging import sanitize_error_msg

logger = structlog.get_logger(__name__)


class RAGPipeline:
    def __init__(self):
        pass

    async def _retrieve_all_context(self, question: str) -> tuple[List[Dict], str, float]:
        t0 = time.time()
        hybrid_task = asyncio.create_task(hybrid_search(question, top_k=5))
        graph_task = asyncio.create_task(retrieve_graph_context(question))
        hybrid_results, graph_context = await asyncio.gather(hybrid_task, graph_task)

        threshold = float(os.getenv("RERANK_THRESHOLD", "-5.0"))
        pruned_hybrid = prune_irrelevant_context(hybrid_results, threshold=threshold)

        retrieval_ms = (time.time() - t0) * 1000
        return pruned_hybrid, graph_context, retrieval_ms

    def _build_payload(self, provider: str, question: str, chat_history: List[Dict], hybrid_results: List[Dict], graph_context: str) -> tuple[str, dict, dict]:
        system_prompt = build_dynamic_prompt(hybrid_results, graph_context, max_tokens=4000)
        api_key = llm_manager.get_api_key(provider)
        safe_question = question.replace("<", "&lt;").replace(">", "&gt;")
        
        if provider == "gemini":
            stream_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key={api_key}"
            headers = {"Content-Type": "application/json"}
            
            contents = []
            import html
            for msg in chat_history:
                if msg.get("role") in ["user", "assistant", "model"]:
                    safe_content = html.escape(msg.get("content", ""))
                    role_tag = "USER" if msg["role"] == "user" else "ASSISTANT"
                    wrapped_content = f"<HISTORY_TURN_{role_tag}>\n{safe_content}\n</HISTORY_TURN_{role_tag}>"
                    contents.append({
                        "role": "model" if msg["role"] in ["assistant", "model"] else "user",
                        "parts": [{"text": wrapped_content}],
                    })
            contents.append({"role": "user", "parts": [{"text": f"<USER_QUERY>\n{safe_question}\n</USER_QUERY>"}]})
            
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
            }
            return stream_url, headers, payload
            
        elif provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            messages = [{"role": "system", "content": system_prompt}]
            import html
            for msg in chat_history:
                if msg.get("role") in ["user", "assistant", "model"]:
                    safe_content = html.escape(msg.get("content", ""))
                    role_tag = "USER" if msg["role"] == "user" else "ASSISTANT"
                    wrapped_content = f"<HISTORY_TURN_{role_tag}>\n{safe_content}\n</HISTORY_TURN_{role_tag}>"
                    messages.append({
                        "role": "assistant" if msg["role"] in ["assistant", "model"] else "user",
                        "content": wrapped_content
                    })
            messages.append({"role": "user", "content": f"<USER_QUERY>\n{safe_question}\n</USER_QUERY>"})
            
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages
            }
            return url, headers, payload

        raise ValueError(f"Unknown provider: {provider}")

    def _format_citations(self, context_results: List[Dict]) -> List[Dict]:
        citations = []
        for r in context_results:
            text = r.get("parent_content", r.get("text", ""))[:200]
            citations.append({
                "filename": r.get("filename", "unknown"),
                "excerpt": text,
                "score": r.get("rerank_score", r.get("score", 0.0)),
            })
        return citations

    async def _log_and_track_metrics(self, question: str, context_results: List[Dict], tokens_used: int):
        avg_score = sum(r.get("rerank_score", r.get("score", 0.0)) for r in context_results) / max(len(context_results), 1)
        cost_usd = (tokens_used / 1_000_000) * 1.25

        logger.info(
            "RAG Query Executed",
            question_length=len(question),
            question_hash=hashlib.sha256(question.encode()).hexdigest()[:8],
            retrieval_count=len(context_results),
            avg_score=avg_score,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

        await increment_metric("queries_today", 1)
        await increment_metric("total_tokens_used", tokens_used)
        await increment_metric("estimated_cost_usd", cost_usd)

    @staticmethod
    def _make_cache_key(question: str, chat_history: List[Dict]) -> str:
        try:
            history_str = json.dumps(chat_history, default=str)
        except TypeError:
            history_str = str(chat_history)
        tenant_salt = os.getenv("API_KEY", "default")
        return "query_cache:" + hashlib.sha256(f"{tenant_salt}_{question}_{history_str}".encode()).hexdigest()

    async def ask(self, question: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        t_start = time.time()
        if chat_history is None:
            chat_history = []

        cache_key = self._make_cache_key(question, chat_history)
        cached_result = await get_cache(cache_key)
        if cached_result:
            logger.info("Semantic Cache Hit", cache_key=cache_key)
            cached_result["timings"]["total_ms"] = (time.time() - t_start) * 1000
            return cached_result

        hybrid_results, graph_context, retrieval_ms = await self._retrieve_all_context(question)
        
        t1 = time.time()
        answer = ""
        tokens_used = 0
        max_retries = int(os.getenv("MAX_API_RETRIES", "3"))

        for attempt in range(max_retries):
            provider = llm_manager.get_active_provider()
            url, headers, payload = self._build_payload(provider, question, chat_history, hybrid_results, graph_context)
            if provider == "gemini":
                # For non-streaming ask, adjust the URL
                api_key = llm_manager.get_api_key(provider)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                    if response.status_code == 429:
                        llm_manager.switch_to_fallback(provider)
                        if attempt < max_retries - 1:
                            wait = 2 ** attempt
                            logger.warning(f"ask 429 on attempt {attempt + 1}, waiting {wait}s")
                            await asyncio.sleep(wait)
                            continue
                    response.raise_for_status()
                    data = response.json()
                    
                    if provider == "gemini":
                        if data.get("candidates"):
                            answer = data["candidates"][0]["content"]["parts"][0]["text"]
                        else:
                            answer = "No response from Gemini API."
                        tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 0)
                    else:
                        answer = data["choices"][0]["message"]["content"]
                        tokens_used = data.get("usage", {}).get("total_tokens", 0)
                        
                    break # Success
            except httpx.HTTPStatusError as e:
                logger.error(f"{provider} API HTTP error", status=e.response.status_code, body=sanitize_error_msg(e.response.text[:300]))
                answer = f"API Error ({e.response.status_code}). Check server logs."
                if e.response.status_code != 429:
                    break
            except Exception as e:
                logger.error(f"{provider} API failed", error_type=e.__class__.__name__)
                answer = "Error generating answer. Check server logs."
                break

        generation_ms = (time.time() - t1) * 1000

        if tokens_used == 0:
            tokens_used = (len(str(payload)) + len(answer)) // 4

        await self._log_and_track_metrics(question, hybrid_results, tokens_used)

        result = {
            "answer": answer,
            "citations": self._format_citations(hybrid_results),
            "tokens_used": tokens_used,
            "timings": {
                "embedding_ms": 0,
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
                "total_ms": (time.time() - t_start) * 1000,
            },
        }

        if "Error" not in answer and "API Error" not in answer:
            await set_cache(cache_key, result, ttl=86400)

        return result

    async def ask_stream(self, question: str, chat_history: List[Dict] = None) -> AsyncGenerator[str, None]:
        if chat_history is None:
            chat_history = []

        cache_key = self._make_cache_key(question, chat_history)
        cached_result = await get_cache(cache_key)
        if cached_result:
            logger.info("Semantic Stream Cache Hit", cache_key=cache_key)
            words = cached_result["answer"].split(" ")
            for i, word in enumerate(words):
                content = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'text': content})}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'citations': cached_result['citations'], 'tokens_used': cached_result['tokens_used']})}\n\n"
            yield "data: [DONE]\n\n"
            return

        hybrid_results, graph_context, _ = await self._retrieve_all_context(question)
        
        generated_chars = 0
        full_answer = ""
        stream_succeeded = False
        max_retries = int(os.getenv("MAX_API_RETRIES", "3"))

        try:
            for attempt in range(max_retries):
                provider = llm_manager.get_active_provider()
                url, headers, payload = self._build_payload(provider, question, chat_history, hybrid_results, graph_context)
                
                if provider == "groq":
                    payload["stream"] = True

                try:
                    async with httpx.AsyncClient() as client:
                        async with client.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
                            if response.status_code == 429:
                                llm_manager.switch_to_fallback(provider)
                                if attempt < max_retries - 1:
                                    wait = 2 ** attempt
                                    logger.warning(f"Stream 429 on attempt {attempt + 1}, waiting {wait}s")
                                    await asyncio.sleep(wait)
                                    continue
                                else:
                                    response.raise_for_status()
                                    
                            response.raise_for_status()

                            async for line in response.aiter_lines():
                                if not line.startswith("data: "):
                                    continue
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    content = ""
                                    if provider == "gemini":
                                        parts = chunk.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                                        if parts:
                                            content = parts[0].get("text", "")
                                    elif provider == "groq":
                                        choices = chunk.get("choices", [])
                                        if choices:
                                            content = choices[0].get("delta", {}).get("content", "")
                                            
                                    if content:
                                        generated_chars += len(content)
                                        full_answer += content
                                        yield f"data: {json.dumps({'text': content})}\n\n"
                                except Exception:
                                    pass  # partial / non-JSON SSE line

                            stream_succeeded = True
                            break  # clean exit — do not retry

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        llm_manager.switch_to_fallback(provider)
                        wait = 2 ** attempt
                        logger.warning(f"Stream HTTPStatusError 429 on attempt {attempt + 1}, waiting {wait}s")
                        await asyncio.sleep(wait)
                        continue
                    raise  # re-raise for the outer handler

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                msg = "\n\n⚠️ **API Rate Limit Exceeded.** You've hit the rate limits for all fallback providers."
            else:
                logger.error(f"API stream HTTP error", status=e.response.status_code)
                msg = f"Stream error ({e.response.status_code}). Check server logs."
            yield f"data: {json.dumps({'text': msg})}\n\n"
        except Exception as e:
            logger.error("API stream failed", error_type=e.__class__.__name__)
            yield f"data: {json.dumps({'text': 'Streaming error occurred. Check server logs.'})}\n\n"

        tokens_used = generated_chars // 4
        await self._log_and_track_metrics(question, hybrid_results, tokens_used)

        citations = self._format_citations(hybrid_results)
        yield f"data: {json.dumps({'citations': citations, 'tokens_used': tokens_used})}\n\n"
        yield "data: [DONE]\n\n"

        if stream_succeeded and full_answer:
            result = {
                "answer": full_answer,
                "citations": citations,
                "tokens_used": tokens_used,
                "timings": {"embedding_ms": 0, "retrieval_ms": 0, "generation_ms": 0, "total_ms": 0},
            }
            await set_cache(cache_key, result, ttl=86400)


pipeline = RAGPipeline()

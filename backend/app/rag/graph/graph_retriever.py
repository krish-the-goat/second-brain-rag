import os
import json
import httpx
import asyncio
from app.rag.graph.neo4j_manager import get_neo4j_manager
from app.core.logging import get_logger, sanitize_error_msg
from app.core.llm_manager import llm_manager

logger = get_logger(__name__)

QUERY_PROMPT = """
You are an intelligent router. Given the user's question, identify the SINGLE most important entity (Noun/Name) that we should lookup in our Knowledge Graph.
Return a JSON object: {"entity": "Entity Name"}
If no clear entity exists, return {"entity": null}.
"""

async def retrieve_graph_context(question: str) -> str:
    """
    1. Extracts the main entity from the question via fallback LLM.
    2. Queries Neo4j for that entity's relationships.
    3. Formats the subgraph into a context string.
    """
    max_retries = int(os.getenv("MAX_API_RETRIES", "3"))
    result_text = "{}"

    for attempt in range(max_retries):
        provider = llm_manager.get_active_provider()
        api_key = llm_manager.get_api_key(provider)
        
        if not api_key:
            return ""

        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "systemInstruction": {"parts": [{"text": QUERY_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": f"Question: {question}"}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            }
        else:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": QUERY_PROMPT},
                    {"role": "user", "content": f"Question: {question}"}
                ]
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=15.0)
                
                if response.status_code == 429:
                    llm_manager.switch_to_fallback(provider)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                        
                response.raise_for_status()
                data = response.json()
                
                if provider == "gemini":
                    if "candidates" in data and len(data["candidates"]) > 0:
                        result_text = data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    if "choices" in data and len(data["choices"]) > 0:
                        result_text = data["choices"][0]["message"]["content"]
                        
                break # Success
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 429:
                logger.error(f"Graph retrieval HTTP error: {sanitize_error_msg(str(e))}")
                break
        except Exception as e:
            logger.error(f"Graph retrieval failed: {e}")
            break

    try:
        data = json.loads(result_text)
        entity_name = data.get("entity")
        if not entity_name:
            return ""
            
        logger.info(f"Graph Search querying entity: {entity_name}")
        
        manager = get_neo4j_manager()
        relationships = await asyncio.to_thread(manager.get_related_context, entity_name)
        
        if not relationships:
            return ""
            
        context_lines = [f"KNOWLEDGE GRAPH CONTEXT FOR '{entity_name}':"]
        for rel in relationships:
            line = f"- {rel['source']} [{rel['relationship']}] {rel['target']} (Context: {rel['context']})"
            context_lines.append(line)
            
        return "\n".join(context_lines)
        
    except Exception as e:
        logger.error(f"Graph retrieval parsing failed: {e}")
        return ""

import os
import json
import httpx
import asyncio
from typing import List, Dict
from app.rag.graph.neo4j_manager import get_neo4j_manager
from app.core.logging import get_logger, sanitize_error_msg
from app.core.llm_manager import llm_manager

logger = get_logger(__name__)

PROMPT = """
You are a highly intelligent Knowledge Graph extractor.
Given the following text, extract the main Entities (nodes) and their Relationships (edges).
Return ONLY a valid JSON object with the following structure:
{
    "entities": [
        {"name": "Entity Name", "type": "Person/Organization/Concept", "description": "Brief context"}
    ],
    "relationships": [
        {"source": "Entity 1", "target": "Entity 2", "type": "WORKS_FOR, USES, RELATED_TO, etc", "context": "Why they are related"}
    ]
}
If no relevant entities are found, return empty lists.
"""

async def extract_and_store_graph(text: str):
    """Extracts a knowledge graph from text using LLM fallback and stores it in Neo4j."""
    max_retries = int(os.getenv("MAX_API_RETRIES", "3"))
    result_text = None

    for attempt in range(max_retries):
        provider = llm_manager.get_active_provider()
        api_key = llm_manager.get_api_key(provider)
        
        if not api_key:
            logger.error(f"{provider} API key not set — skipping graph extraction.")
            return

        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "systemInstruction": {"parts": [{"text": PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": f"Text:\n{text}"}]}],
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
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": f"Text:\n{text}"}
                ]
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                
                if response.status_code == 429:
                    llm_manager.switch_to_fallback(provider)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                        
                response.raise_for_status()
                api_response = response.json()

                if provider == "gemini":
                    if "candidates" not in api_response or not api_response["candidates"]:
                        logger.warning("Graph extraction: no candidates in Gemini response.")
                        break
                    result_text = api_response["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    result_text = api_response["choices"][0]["message"]["content"]
                    
                break # Success

        except httpx.HTTPStatusError as e:
            if e.response.status_code != 429:
                logger.error(f"Graph extraction HTTP error: {sanitize_error_msg(str(e))}")
                break
        except Exception as e:
            logger.error(f"Graph extraction failed: {e}")
            break

    if not result_text:
        return

    try:
        graph_data = json.loads(result_text)
    except json.JSONDecodeError as parse_err:
        logger.error(f"Graph extraction: failed to parse JSON: {parse_err}")
        return

    manager = get_neo4j_manager()

    for entity in graph_data.get("entities", []):
        await asyncio.to_thread(
            manager.add_entity,
            label=entity.get("type", "Entity").replace(" ", ""),
            name=entity.get("name"),
            description=entity.get("description", ""),
        )

    for rel in graph_data.get("relationships", []):
        rel_type = (
            rel.get("type", "RELATED_TO")
            .upper()
            .replace(" ", "_")
            .replace("-", "_")
        )
        await asyncio.to_thread(
            manager.add_relationship,
            source_name=rel.get("source"),
            target_name=rel.get("target"),
            relationship_type=rel_type,
            context=rel.get("context", ""),
        )

    logger.info(
        f"Graph extraction stored {len(graph_data.get('entities', []))} entities "
        f"and {len(graph_data.get('relationships', []))} relationships."
    )

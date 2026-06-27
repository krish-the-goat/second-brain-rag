import os
import json
import httpx
from typing import List, Dict
from app.rag.graph.neo4j_manager import get_neo4j_manager
from app.core.logging import get_logger

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
    """
    Extracts graph data from text using OpenRouter LLM and stores it in Neo4j.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("No OpenRouter API key found.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "Second Brain RAG",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.5-flash", 
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Text:\n{text}"}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            result_json = response.json()
            
            content = result_json["choices"][0]["message"]["content"]
            data = json.loads(content)
            
            manager = get_neo4j_manager()
            
            for entity in data.get("entities", []):
                manager.add_entity(
                    label=entity.get("type", "Entity").replace(" ", ""),
                    name=entity.get("name"),
                    description=entity.get("description", "")
                )
                
            for rel in data.get("relationships", []):
                manager.add_relationship(
                    source_name=rel.get("source"),
                    target_name=rel.get("target"),
                    relationship_type=rel.get("type"),
                    context=rel.get("context", "")
                )
                
            logger.info(f"Extracted and stored {len(data.get('entities', []))} entities and {len(data.get('relationships', []))} relationships via OpenRouter.")
            
    except Exception as e:
        logger.error(f"Graph extraction failed: {e}")

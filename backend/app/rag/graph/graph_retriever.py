import os
import json
import httpx
from app.rag.graph.neo4j_manager import get_neo4j_manager
from app.core.logging import get_logger

logger = get_logger(__name__)

QUERY_PROMPT = """
You are an intelligent router. Given the user's question, identify the SINGLE most important entity (Noun/Name) that we should lookup in our Knowledge Graph.
Return a JSON object: {"entity": "Entity Name"}
If no clear entity exists, return {"entity": null}.
"""

async def retrieve_graph_context(question: str) -> str:
    """
    1. Extracts the main entity from the question via OpenRouter.
    2. Queries Neo4j for that entity's relationships.
    3. Formats the subgraph into a context string.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return ""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "Second Brain RAG",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {"role": "system", "content": QUERY_PROMPT},
            {"role": "user", "content": f"Question: {question}"}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15.0
            )
            response.raise_for_status()
            result_json = response.json()
            
            content = result_json["choices"][0]["message"]["content"]
            data = json.loads(content)
            
            entity_name = data.get("entity")
            if not entity_name:
                return ""
                
            logger.info(f"Graph Search querying entity: {entity_name}")
            
            manager = get_neo4j_manager()
            relationships = manager.get_related_context(entity_name)
            
            if not relationships:
                return ""
                
            context_lines = [f"KNOWLEDGE GRAPH CONTEXT FOR '{entity_name}':"]
            for rel in relationships:
                line = f"- {rel['source']} [{rel['relationship']}] {rel['target']} (Context: {rel['context']})"
                context_lines.append(line)
                
            return "\n".join(context_lines)
            
    except Exception as e:
        logger.error(f"Graph retrieval failed via OpenRouter: {e}")
        return ""

import json
import asyncio
from app.rag.graph.neo4j_manager import get_neo4j_manager
from app.core.logging import get_logger
from app.core.llm_manager import llm_manager

logger = get_logger(__name__)

EXTRACTION_PROMPT = """\
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
    """Extracts a knowledge graph from text using the unified LLM interface and stores it in Neo4j."""
    result_text = await llm_manager.generate(
        system_prompt=EXTRACTION_PROMPT,
        user_content=f"Text:\n{text}",
        json_mode=True,
        timeout=30.0,
    )

    if not result_text:
        return

    try:
        graph_data = json.loads(result_text)
    except json.JSONDecodeError as e:
        logger.error(f"Graph extraction: failed to parse JSON: {e}")
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

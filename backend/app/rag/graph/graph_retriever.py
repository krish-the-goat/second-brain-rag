import json
import asyncio
from app.rag.graph.neo4j_manager import get_neo4j_manager
from app.core.logging import get_logger
from app.core.llm_manager import llm_manager

logger = get_logger(__name__)

ENTITY_EXTRACTION_PROMPT = """\
You are an intelligent router. Given the user's question, identify the SINGLE most important entity (Noun/Name) that we should lookup in our Knowledge Graph.
Return a JSON object: {"entity": "Entity Name"}
If no clear entity exists, return {"entity": null}.
"""


async def retrieve_graph_context(question: str) -> str:
    """
    1. Extracts the main entity from the question via the unified LLM interface.
    2. Queries Neo4j for that entity's relationships.
    3. Formats the subgraph into a context string.
    """
    result_text = await llm_manager.generate(
        system_prompt=ENTITY_EXTRACTION_PROMPT,
        user_content=f"Question: {question}",
        json_mode=True,
        timeout=15.0,
    )

    if not result_text:
        return ""

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
            line = (
                f"- {rel['source']} [{rel['relationship']}] {rel['target']} "
                f"(Context: {rel['context']})"
            )
            context_lines.append(line)

        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Graph retrieval parsing failed: {e}")
        return ""

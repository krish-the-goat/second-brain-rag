import os
import json
import google.generativeai as genai
from app.rag.graph.neo4j_manager import get_neo4j_manager
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

QUERY_PROMPT = """
You are an intelligent router. Given the user's question, identify the SINGLE most important entity (Noun/Name) that we should lookup in our Knowledge Graph.
Return a JSON object: {"entity": "Entity Name"}
If no clear entity exists, return {"entity": null}.
"""

async def retrieve_graph_context(question: str) -> str:
    """
    1. Extracts the main entity from the question.
    2. Queries Neo4j for that entity's relationships.
    3. Formats the subgraph into a context string.
    """
    try:
        response = model.generate_content(
            f"{QUERY_PROMPT}\n\nQuestion: {question}",
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        
        data = json.loads(response.text)
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
        logger.error(f"Graph retrieval failed: {e}")
        return ""

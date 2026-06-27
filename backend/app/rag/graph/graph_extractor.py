import os
import json
from typing import List, Dict
import google.generativeai as genai
from app.rag.graph.neo4j_manager import get_neo4j_manager
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

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
    Extracts graph data from text using LLM and stores it in Neo4j.
    NOTE: Due to LLM quota constraints, this should only be called on highly dense/important chunks, 
    or batched appropriately in production.
    """
    try:
        response = model.generate_content(
            f"{PROMPT}\n\nText:\n{text}",
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        
        data = json.loads(response.text)
        
        manager = get_neo4j_manager()
        
        # Insert Entities
        for entity in data.get("entities", []):
            manager.add_entity(
                label=entity.get("type", "Entity").replace(" ", ""),
                name=entity.get("name"),
                description=entity.get("description", "")
            )
            
        # Insert Relationships
        for rel in data.get("relationships", []):
            manager.add_relationship(
                source_name=rel.get("source"),
                target_name=rel.get("target"),
                relationship_type=rel.get("type"),
                context=rel.get("context", "")
            )
            
        logger.info(f"Extracted and stored {len(data.get('entities', []))} entities and {len(data.get('relationships', []))} relationships.")
        
    except Exception as e:
        logger.error(f"Graph extraction failed: {e}")

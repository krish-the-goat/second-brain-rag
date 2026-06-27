import os
import re
from neo4j import GraphDatabase
from app.core.logging import get_logger

logger = get_logger(__name__)

class Neo4jManager:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info("Successfully connected to Neo4j.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def add_entity(self, label: str, name: str, description: str = ""):
        if not self.driver:
            return
            
        # CRITICAL FIX: Cypher Injection protection
        clean_label = re.sub(r'[^a-zA-Z0-9_]', '', label)
        if not clean_label:
            clean_label = "Entity"
            
        query = (
            f"MERGE (e:{clean_label} {{name: $name}}) "
            "ON CREATE SET e.description = $description "
            "RETURN e"
        )
        with self.driver.session() as session:
            session.run(query, name=name, description=description)

    def add_relationship(self, source_name: str, target_name: str, relationship_type: str, context: str = ""):
        if not self.driver:
            return
            
        # CRITICAL FIX: Cypher Injection protection
        clean_type = re.sub(r'[^a-zA-Z0-9_]', '', relationship_type.upper().replace(" ", "_"))
        if not clean_type:
            clean_type = "RELATED_TO"
            
        query = (
            "MATCH (a {name: $source}) "
            "MATCH (b {name: $target}) "
            f"MERGE (a)-[r:{clean_type}]->(b) "
            "ON CREATE SET r.context = $context "
            "RETURN type(r)"
        )
        with self.driver.session() as session:
            session.run(query, source=source_name, target=target_name, context=context)

    def get_related_context(self, entity_name: str) -> list:
        """Retrieves 1-hop relationships for a given entity to build context."""
        if not self.driver:
            return []
            
        query = (
            "MATCH (a {name: $name})-[r]-(b) "
            "RETURN a.name AS source, type(r) AS relationship, b.name AS target, r.context AS context "
            "LIMIT 10"
        )
        results = []
        with self.driver.session() as session:
            result = session.run(query, name=entity_name)
            for record in result:
                results.append({
                    "source": record["source"],
                    "relationship": record["relationship"],
                    "target": record["target"],
                    "context": record.get("context", "")
                })
        return results

# Singleton pattern
_manager = None

def get_neo4j_manager() -> Neo4jManager:
    global _manager
    if _manager is None:
        _manager = Neo4jManager()
    return _manager

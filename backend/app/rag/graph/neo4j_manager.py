import os
import re
import time
from neo4j import GraphDatabase
from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_CONNECT_RETRIES = 5
_RETRY_DELAY_S = 3


class Neo4jManager:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")

        self.driver = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"Initialized Neo4j driver for {uri} (lazy connection).")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def add_entity(self, label: str, name: str, description: str = ""):
        if not self.driver or not name:
            return

        clean_label = re.sub(r"[^a-zA-Z0-9_]", "", label) or "Entity"

        query = (
            f"MERGE (e:{clean_label} {{name: $name}}) "
            "ON CREATE SET e.description = $description "
            "RETURN e"
        )
        with self.driver.session() as session:
            session.run(query, name=name, description=description)

    def add_relationship(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str,
        context: str = "",
    ):
        if not self.driver or not source_name or not target_name:
            return

        clean_type = (
            re.sub(r"[^a-zA-Z0-9_]", "", relationship_type.upper().replace(" ", "_"))
            or "RELATED_TO"
        )

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
        """Returns 1-hop relationships for an entity to build graph context."""
        if not self.driver:
            return []

        query = (
            "MATCH (a {name: $name})-[r]-(b) "
            "RETURN a.name AS source, type(r) AS relationship, b.name AS target, r.context AS context "
            "LIMIT 10"
        )
        results = []
        with self.driver.session() as session:
            for record in session.run(query, name=entity_name):
                results.append(
                    {
                        "source": record["source"],
                        "relationship": record["relationship"],
                        "target": record["target"],
                        "context": record.get("context", ""),
                    }
                )
        return results


# Singleton
_manager: Neo4jManager = None


def get_neo4j_manager() -> Neo4jManager:
    global _manager
    if _manager is None:
        _manager = Neo4jManager()
    return _manager

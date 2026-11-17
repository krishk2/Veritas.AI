import os
import socket
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
from veritas.core.interfaces import IGraphRepository

load_dotenv()

logger = logging.getLogger("veritas.neo4j_service")

class Neo4jGraphRepository(IGraphRepository):
    """Neo4j implementation of the Trace-the-Source Graph Repository."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "")
        self._driver = None
        self._connection_failed = False

    def _get_driver(self):
        if self._driver is not None:
            return self._driver

        if not self.password or self._connection_failed:
            return None

        # Quick socket pre-check only for local host to avoid 6-second TCP timeout on closed local ports
        is_local = "localhost" in self.uri or "127.0.0.1" in self.uri
        if is_local:
            try:
                with socket.create_connection(("127.0.0.1", 7687), timeout=0.15):
                    pass
            except Exception:
                self._connection_failed = True
                logger.info("Local Neo4j port 7687 is unreachable. Bypassing graph persistence.")
                return None

        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password),
                connection_timeout=3.0
            )
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            return self._driver
        except Exception as e:
            logger.warning(f"Neo4j connection failed ({e}). Graph persistence will use in-memory fallback.")
            self._driver = None
            self._connection_failed = True
            return None

    def is_available(self) -> bool:
        return self._get_driver() is not None

    def record_provenance(
        self,
        claim_id: str,
        claim: str,
        verdict: str,
        confidence: float,
        status: str,
        sources: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        credibility_report: List[Dict[str, Any]]
    ) -> bool:
        driver = self._get_driver()
        if not driver:
            return False

        domain_status_map = {c.get("domain", ""): c.get("status", "Neutral") for c in (credibility_report or [])}

        cypher_query = """
        MERGE (c:Claim {id: $claim_id})
        SET c.text = $claim,
            c.verdict = $verdict,
            c.confidence = $confidence,
            c.status = $status,
            c.updated_at = datetime()

        WITH c
        UNWIND $sources AS src
        MERGE (s:Source {url: src.url})
        ON CREATE SET s.title = src.title, s.snippet = src.snippet
        MERGE (c)-[:INVESTIGATED_SOURCE]->(s)

        WITH c, src, s
        WHERE src.domain <> ""
        MERGE (d:Domain {name: src.domain})
        SET d.status = src.domain_status
        MERGE (s)-[:PUBLISHED_BY]->(d)

        WITH c
        UNWIND $evidence AS ev
        CREATE (e:Evidence {
            sentence: ev.sentence,
            label: ev.label,
            score: ev.score
        })
        MERGE (c)-[:HAS_EVIDENCE {label: ev.label}]->(e)
        """

        prepared_sources = []
        for s in (sources or []):
            url = s.get("url", "")
            domain = url.split("//")[-1].split("/")[0] if "//" in url else ""
            prepared_sources.append({
                "url": url,
                "title": s.get("title", ""),
                "snippet": s.get("snippet", ""),
                "domain": domain,
                "domain_status": domain_status_map.get(domain, "Neutral")
            })

        params = {
            "claim_id": claim_id,
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "status": status,
            "sources": prepared_sources,
            "evidence": evidence or []
        }

        try:
            with driver.session() as session:
                session.run(cypher_query, params)
            logger.info(f"Provenance graph recorded in Neo4j for claim {claim_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to record Neo4j provenance: {e}")
            return False

    def get_subgraph(self, claim_id: str) -> Dict[str, Any]:
        driver = self._get_driver()
        if not driver:
            return {
                "connected": False,
                "message": "Neo4j is not connected or configured.",
                "nodes": [],
                "edges": []
            }

        query = """
        MATCH (c:Claim {id: $claim_id})
        OPTIONAL MATCH (c)-[r1:INVESTIGATED_SOURCE]->(s:Source)
        OPTIONAL MATCH (s)-[r2:PUBLISHED_BY]->(d:Domain)
        OPTIONAL MATCH (c)-[r3:HAS_EVIDENCE]->(e:Evidence)
        RETURN c, collect(DISTINCT s) AS sources, collect(DISTINCT d) AS domains,
               collect(DISTINCT e) AS evidences,
               collect(DISTINCT r1) AS rels_sources,
               collect(DISTINCT r2) AS rels_domains,
               collect(DISTINCT r3) AS rels_evidences
        """

        nodes = []
        edges = []
        node_ids = set()

        try:
            with driver.session() as session:
                result = session.run(query, {"claim_id": claim_id}).single()
                if not result or not result["c"]:
                    return {"connected": True, "nodes": [], "edges": []}

                def _clean_props(p: dict) -> dict:
                    cleaned = {}
                    for k, v in dict(p).items():
                        if hasattr(v, "iso_format"):
                            cleaned[k] = v.iso_format()
                        elif hasattr(v, "to_native"):
                            cleaned[k] = str(v.to_native())
                        elif isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                            cleaned[k] = v
                        else:
                            cleaned[k] = str(v)
                    return cleaned

                c = result["c"]
                c_props = _clean_props(c)
                claim_node_id = f"claim_{c_props.get('id', claim_id)}"
                nodes.append({
                    "id": claim_node_id,
                    "label": "Claim",
                    "type": "claim",
                    "title": c_props.get("text", "")[:100],
                    "verdict": c_props.get("verdict"),
                    "confidence": c_props.get("confidence"),
                    "properties": c_props
                })
                node_ids.add(claim_node_id)

                for s in result["sources"]:
                    if s:
                        s_props = _clean_props(s)
                        s_id = f"source_{abs(hash(s_props.get('url', '')))}"
                        if s_id not in node_ids:
                            nodes.append({
                                "id": s_id,
                                "label": "Source",
                                "type": "source",
                                "title": s_props.get("title", ""),
                                "url": s_props.get("url", ""),
                                "properties": s_props
                            })
                            node_ids.add(s_id)
                        edges.append({"source": claim_node_id, "target": s_id, "label": "INVESTIGATED_SOURCE"})

                for d in result["domains"]:
                    if d:
                        d_props = _clean_props(d)
                        d_id = f"domain_{d_props.get('name', '')}"
                        if d_id not in node_ids:
                            nodes.append({
                                "id": d_id,
                                "label": "Domain",
                                "type": "domain",
                                "domain": d_props.get("name", ""),
                                "properties": d_props
                            })
                            node_ids.add(d_id)
                        for s in result["sources"]:
                            if s and d_props.get('name') and d_props['name'] in s.get('url', ''):
                                edges.append({"source": f"source_{abs(hash(s.get('url', '')))}", "target": d_id, "label": "PUBLISHED_BY"})

                for e in result["evidences"]:
                    if e:
                        e_props = _clean_props(e)
                        e_id = f"evidence_{abs(hash(e_props.get('sentence', '')))}"
                        if e_id not in node_ids:
                            nodes.append({
                                "id": e_id,
                                "label": "Evidence",
                                "type": "evidence",
                                "title": e_props.get("sentence", "")[:90],
                                "verdict": e_props.get("label"),
                                "score": e_props.get("score"),
                                "properties": e_props
                            })
                            node_ids.add(e_id)
                        edges.append({"source": claim_node_id, "target": e_id, "label": f"HAS_EVIDENCE ({e_props.get('label', '')})"})

            return {
                "connected": True,
                "claim_id": claim_id,
                "nodes": nodes,
                "edges": edges
            }
        except Exception as e:
            logger.error(f"Error fetching Neo4j subgraph for claim {claim_id}: {e}")
            return {
                "connected": False,
                "error": str(e),
                "nodes": [],
                "edges": []
            }

# Global default instance
_default_graph_repo = Neo4jGraphRepository()

def get_graph_repository() -> IGraphRepository:
    return _default_graph_repo

# Functional aliases for backward compatibility
def get_neo4j_driver():
    return _default_graph_repo._get_driver()

def is_neo4j_available() -> bool:
    return _default_graph_repo.is_available()

def record_provenance_graph(*args, **kwargs) -> bool:
    return _default_graph_repo.record_provenance(*args, **kwargs)

def get_claim_subgraph(claim_id: str) -> Dict[str, Any]:
    return _default_graph_repo.get_subgraph(claim_id)

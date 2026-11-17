from fastapi import APIRouter, Depends
from veritas.core.interfaces import IGraphRepository
from veritas.core.container import container

router = APIRouter(prefix="/api/v1/claims", tags=["Trace-the-Source Graph"])

@router.get("/{claim_id}/graph")
def get_provenance_graph(
    claim_id: str,
    graph_repo: IGraphRepository = Depends(container.get_graph_repository)
):
    """
    Returns the Neo4j Trace-the-Source provenance graph in Cytoscape/D3 compatible node-edge JSON.
    """
    return graph_repo.get_subgraph(claim_id)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.core.database import get_db
from backend.app.services.relationship_graph import build_ecosystem_networkx_graph

router = APIRouter(prefix="/graph", tags=["Relationship Graph"])

@router.get("/ecosystem")
def get_relationship_graph(
    highlight_fdr_id: Optional[int] = Query(None),
    institution_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns NetworkX generated React Flow graph nodes and edges.
    Highlights multi-entity links: Trust -> Institution -> FDR -> Bank -> Signatory.
    Flags unusual relationship patterns (e.g., cross-institution duplicate FDR collisions).
    """
    return build_ecosystem_networkx_graph(db, highlight_fdr_id=highlight_fdr_id, filter_institution_id=institution_id)

@router.get("/fdr/{fdr_id}")
def get_fdr_subgraph(
    fdr_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns focused ego-network subgraph for a specific FDR instrument.
    """
    return build_ecosystem_networkx_graph(db, highlight_fdr_id=fdr_id)


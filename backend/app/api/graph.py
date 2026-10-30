from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.core.database import get_db
from backend.app.services.relationship_graph import build_ecosystem_networkx_graph

router = APIRouter(prefix="/graph", tags=["Relationship Graph"])

@router.get("/ecosystem")
def get_relationship_graph(
    highlight_fdr_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns NetworkX generated React Flow graph nodes and edges.
    Highlights multi-entity links: Trust -> Institution -> FDR -> Bank -> Signatory.
    """
    return build_ecosystem_networkx_graph(db, highlight_fdr_id=highlight_fdr_id)


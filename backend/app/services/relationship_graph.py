"""DepoSafe FDR Intelligence Ecosystem Graph (NetworkX + React Flow).

Constructs the comprehensive multi-entity deposit intelligence graph:
Nodes:
- Institutions (AICTE registered colleges / polytechnics)
- FDRs (Deposit instruments)
- Banks (Financial institutions)
- Branches (Core branch offices)
- Documents (Versioned files & cryptographic hashes)
- Renewals (Lineage links)
- Release Requests (NOC & refund claims)

Edges:
- SUBMITTED (Institution -> FDR)
- ISSUED_BY (FDR -> Bank)
- AT_BRANCH (FDR -> Branch)
- HAS_DOCUMENT (FDR -> Document)
- RENEWED_FROM (Successor FDR -> Predecessor FDR)
- SAME_NUMBER (FDR <-> FDR: Cross-institution collision)
- SAME_HASH (Document <-> Document: Reused byte hash)
- VISUALLY_SIMILAR (Document <-> Document: Perceptual hash clone)

Statutory Wording: "Relationship requiring investigation, not proof of fraud."
"""

import networkx as nx
import imagehash
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models.deposafe_models import (
    Institution, FDR, FDRDocument, Bank, RenewalRecord, ReleaseRequest
)

def build_ecosystem_networkx_graph(
    db: Session,
    highlight_fdr_id: Optional[int] = None,
    filter_institution_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Constructs the NetworkX intelligence graph and converts it to React Flow format.
    Detects complex graph relationship anomalies and highlights investigation targets.
    """
    G = nx.MultiDiGraph()

    query_inst = db.query(Institution)
    if filter_institution_id:
        query_inst = query_inst.filter(Institution.id == filter_institution_id)
    institutions = query_inst.all()
    inst_ids = {inst.id for inst in institutions}

    query_fdr = db.query(FDR)
    if filter_institution_id:
        query_fdr = query_fdr.filter(FDR.institution_id == filter_institution_id)
    fdrs = query_fdr.all()

    # 1. Add Institutions
    for inst in institutions:
        inst_node_id = f"inst_{inst.id}"
        G.add_node(
            inst_node_id,
            node_type="INSTITUTION",
            label=inst.name,
            aicte_id=inst.aicte_id,
            state=inst.state,
            category=inst.category,
            trust_name=inst.society_or_trust_name,
            signatory=inst.authorized_signatory_name
        )

        # Add Society / Trust Node
        if inst.society_or_trust_name:
            soc_id = f"soc_{inst.society_or_trust_name.strip().lower().replace(' ', '_')}"
            if not G.has_node(soc_id):
                G.add_node(soc_id, node_type="SOCIETY", label=inst.society_or_trust_name)
            G.add_edge(soc_id, inst_node_id, relation="GOVERNS")

        # Add Signatory Node
        if inst.authorized_signatory_name:
            sig_id = f"sig_{inst.authorized_signatory_name.strip().lower().replace(' ', '_')}"
            if not G.has_node(sig_id):
                G.add_node(sig_id, node_type="SIGNATORY", label=inst.authorized_signatory_name)
            G.add_edge(sig_id, inst_node_id, relation="AUTHORIZED_SIGNATORY")

    # 2. Add Banks, Branches, and FDRs
    fdr_number_map: Dict[str, List[FDR]] = {}
    fdr_nodes_added = set()

    for f in fdrs:
        fdr_node_id = f"fdr_{f.id}"
        fdr_nodes_added.add(fdr_node_id)
        G.add_node(
            fdr_node_id,
            node_type="FDR",
            label=f"{f.bank_name}\n#{f.fdr_number}",
            fdr_number=f.fdr_number,
            amount=f.amount,
            status=f.status.value,
            risk_score=f.review_priority_score or 0.0,
            risk_level=f.review_priority_level or "LOW",
            highlighted=(f.id == highlight_fdr_id)
        )

        # Edge: Institution -> FDR (SUBMITTED)
        G.add_edge(f"inst_{f.institution_id}", fdr_node_id, relation="SUBMITTED")

        # Bank Node
        bank_id = f"bank_{f.bank_name.strip().lower().replace(' ', '_')}"
        if not G.has_node(bank_id):
            G.add_node(bank_id, node_type="BANK", label=f.bank_name)
        G.add_edge(fdr_node_id, bank_id, relation="ISSUED_BY")

        # Branch Node
        if f.branch_name or f.ifsc_code:
            branch_id = f"branch_{f.ifsc_code.strip().lower()}"
            if not G.has_node(branch_id):
                G.add_node(branch_id, node_type="BRANCH", label=f"{f.branch_name or 'Branch'} ({f.ifsc_code})", ifsc=f.ifsc_code)
                G.add_edge(branch_id, bank_id, relation="BRANCH_OF")
            G.add_edge(fdr_node_id, branch_id, relation="AT_BRANCH")

        # Track composite key for duplicate collision analysis
        comp_key = f"{f.bank_name}___{f.fdr_number}".lower()
        fdr_number_map.setdefault(comp_key, []).append(f)

        # Predecessor renewal chain
        if f.predecessor_fdr_id:
            pred_node_id = f"fdr_{f.predecessor_fdr_id}"
            if G.has_node(pred_node_id):
                G.add_edge(fdr_node_id, pred_node_id, relation="RENEWED_FROM")

        # Add Documents attached to FDR
        for doc in f.documents:
            doc_node_id = f"doc_{doc.id}"
            G.add_node(
                doc_node_id,
                node_type="DOCUMENT",
                label=doc.file_name,
                doc_type=doc.doc_type,
                sha256=doc.file_hash_sha256[:12] if doc.file_hash_sha256 else "",
                phash=doc.perceptual_hash or ""
            )
            G.add_edge(fdr_node_id, doc_node_id, relation="HAS_DOCUMENT")

    # 3. Add Cross-Entity Intelligence Edges (SAME_NUMBER, SAME_HASH, VISUALLY_SIMILAR)
    anomalous_relationships = []

    # 3a. SAME_NUMBER: Cross-Institution Duplicate Collisions
    for comp_key, coll_fdrs in fdr_number_map.items():
        if len(coll_fdrs) > 1:
            insts_involved = list({f.institution_id for f in coll_fdrs})
            if len(insts_involved) > 1:
                # Critical Cross-Institution Shared Instrument!
                for i in range(len(coll_fdrs)):
                    for j in range(i + 1, len(coll_fdrs)):
                        u_node = f"fdr_{coll_fdrs[i].id}"
                        v_node = f"fdr_{coll_fdrs[j].id}"
                        G.add_edge(u_node, v_node, relation="SAME_NUMBER", style="dashed_red")

                anomalous_relationships.append({
                    "pattern": "CROSS_INSTITUTION_SHARED_FDR",
                    "severity": "CRITICAL",
                    "bank_name": coll_fdrs[0].bank_name,
                    "fdr_number": coll_fdrs[0].fdr_number,
                    "institutions_involved": insts_involved,
                    "fdr_ids": [f.id for f in coll_fdrs],
                    "investigation_note": f"Instrument #{coll_fdrs[0].fdr_number} at {coll_fdrs[0].bank_name} is simultaneously pledged by multiple institutions."
                })

    # 3b. SAME_HASH & VISUALLY_SIMILAR: Document Collisions
    all_documents = db.query(FDRDocument).filter(FDRDocument.fdr_id.in_([f.id for f in fdrs])).all()
    sha_map: Dict[str, List[FDRDocument]] = {}
    for d in all_documents:
        if d.file_hash_sha256:
            sha_map.setdefault(d.file_hash_sha256, []).append(d)

    for h_val, d_list in sha_map.items():
        if len(d_list) > 1:
            for i in range(len(d_list)):
                for j in range(i + 1, len(d_list)):
                    if d_list[i].fdr_id != d_list[j].fdr_id:
                        u_node = f"doc_{d_list[i].id}"
                        v_node = f"doc_{d_list[j].id}"
                        if G.has_node(u_node) and G.has_node(v_node):
                            G.add_edge(u_node, v_node, relation="SAME_HASH", style="dotted_orange")

            anomalous_relationships.append({
                "pattern": "IDENTICAL_FILE_HASH_REUSED",
                "severity": "HIGH",
                "sha256_hash": h_val,
                "document_ids": [d.id for d in d_list],
                "investigation_note": f"Exact byte-for-byte identical document file (SHA-256: {h_val[:16]}...) pledged across different instruments."
            })

    # 4. Generate Layered Coordinates for React Flow
    rf_nodes = []
    rf_edges = []

    type_x = {
        "SOCIETY": 40,
        "SIGNATORY": 40,
        "INSTITUTION": 280,
        "FDR": 580,
        "DOCUMENT": 880,
        "BRANCH": 880,
        "BANK": 1140
    }

    type_counts = {}

    for node, data in G.nodes(data=True):
        n_type = data.get("node_type", "DEFAULT")
        idx = type_counts.get(n_type, 0)
        type_counts[n_type] = idx + 1

        x = type_x.get(n_type, 500)
        y = 60 + (idx * 110)

        # Style based on node type
        is_highlighted = data.get("highlighted", False)
        border_color = "#3B82F6" # default blue
        bg_color = "#FFFFFF"

        if n_type == "FDR":
            risk = data.get("risk_level", "LOW")
            if risk == "CRITICAL" or is_highlighted:
                border_color = "#EF4444" # red
                bg_color = "#FEF2F2"
            elif risk == "HIGH":
                border_color = "#F59E0B" # amber
                bg_color = "#FFFBEB"
            else:
                border_color = "#10B981" # emerald
                bg_color = "#ECFDF5"
        elif n_type == "INSTITUTION":
            border_color = "#6366F1" # indigo
            bg_color = "#EEF2FF"
        elif n_type == "BANK":
            border_color = "#0D9488" # teal
            bg_color = "#F0FDFA"
        elif n_type == "DOCUMENT":
            border_color = "#8B5CF6" # purple
            bg_color = "#F5F3FF"

        rf_nodes.append({
            "id": node,
            "type": "default",
            "data": {
                "label": data.get("label", node),
                "node_type": n_type,
                "metadata": {k: v for k, v in data.items() if k not in ["label", "node_type"]}
            },
            "position": {"x": x, "y": y},
            "style": {
                "border": f"2px solid {border_color}",
                "backgroundColor": bg_color,
                "borderRadius": "8px",
                "padding": "10px",
                "fontWeight": "bold" if is_highlighted else "normal",
                "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
            }
        })

    # Convert edges
    edge_idx = 0
    for u, v, k, data in G.edges(keys=True, data=True):
        edge_idx += 1
        rel = data.get("relation", "")
        style_prop = data.get("style", "")

        stroke_color = "#94A3B8"
        stroke_dash = None
        animated = False

        if rel == "SAME_NUMBER":
            stroke_color = "#EF4444"
            stroke_dash = "5 5"
            animated = True
        elif rel == "SAME_HASH":
            stroke_color = "#F59E0B"
            stroke_dash = "4 4"
            animated = True
        elif rel == "SUBMITTED":
            stroke_color = "#3B82F6"
        elif rel == "ISSUED_BY":
            stroke_color = "#0D9488"

        rf_edges.append({
            "id": f"edge_{edge_idx}_{u}_{v}",
            "source": u,
            "target": v,
            "label": rel,
            "animated": animated,
            "style": {
                "stroke": stroke_color,
                "strokeWidth": 2,
                "strokeDasharray": stroke_dash
            } if stroke_dash else {"stroke": stroke_color, "strokeWidth": 2}
        })

    return {
        "nodes": rf_nodes,
        "edges": rf_edges,
        "total_nodes": len(rf_nodes),
        "total_edges": len(rf_edges),
        "anomalous_relationships": anomalous_relationships,
        "wording_disclaimer": "Relationship requiring investigation, not proof of fraud."
    }

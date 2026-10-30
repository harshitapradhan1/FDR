import networkx as nx
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import Institution, FDR

def build_ecosystem_networkx_graph(db: Session, highlight_fdr_id: int = None) -> Dict[str, Any]:
    """
    Constructs a NetworkX relationship graph of the AICTE deposit ecosystem:
    Trust/Society -> Institution -> FDR -> Bank & Branch -> Signatory.
    Detects anomalies: cross-institution FDR sharing, high degree hubs, multi-trust signatories.
    Returns React Flow formatted nodes and edges.
    """
    G = nx.MultiDiGraph()

    institutions = db.query(Institution).all()
    fdrs = db.query(FDR).all()

    # We build mappings
    societies = set()
    banks = set()
    signatories = set()

    for inst in institutions:
        G.add_node(f"inst_{inst.id}", node_type="INSTITUTION", label=inst.name, aicte_id=inst.aicte_id, category=inst.category)
        if inst.society_or_trust_name:
            soc_id = f"soc_{inst.society_or_trust_name.strip().lower()}"
            societies.add((soc_id, inst.society_or_trust_name))
            G.add_edge(soc_id, f"inst_{inst.id}", relation="OPERATES")

        if inst.authorized_signatory_name:
            sig_id = f"sig_{inst.authorized_signatory_name.strip().lower()}"
            signatories.add((sig_id, inst.authorized_signatory_name))
            G.add_edge(sig_id, f"inst_{inst.id}", relation="AUTHORIZED_SIGNATORY")

    for soc_id, soc_name in societies:
        G.add_node(soc_id, node_type="SOCIETY", label=soc_name)

    for sig_id, sig_name in signatories:
        G.add_node(sig_id, node_type="SIGNATORY", label=sig_name)

    for f in fdrs:
        fdr_node_id = f"fdr_{f.id}"
        G.add_node(
            fdr_node_id,
            node_type="FDR",
            label=f"{f.bank_name} #{f.fdr_number[-6:]}",
            fdr_number=f.fdr_number,
            amount=f.amount,
            status=f.status.value,
            risk_score=f.review_priority_score,
            risk_level=f.review_priority_level
        )
        G.add_edge(f"inst_{f.institution_id}", fdr_node_id, relation="PLEDGED")

        bank_id = f"bank_{f.bank_name.strip().lower()}"
        banks.add((bank_id, f.bank_name))
        G.add_edge(fdr_node_id, bank_id, relation="ISSUED_BY")

        # If it's a renewal chain
        if f.predecessor_fdr_id:
            G.add_edge(f"fdr_{f.predecessor_fdr_id}", fdr_node_id, relation="RENEWED_AS")

    for b_id, b_name in banks:
        G.add_node(b_id, node_type="BANK", label=b_name)

    # Anomaly Detection via Graph Analysis:
    anomalies = []
    
    # 1. Multi-institution shared FDR check (in-degree of FDR from institutions > 1)
    for node, data in G.nodes(data=True):
        if data.get("node_type") == "FDR":
            in_insts = [u for u, v, k, d in G.in_edges(node, keys=True, data=True) if d.get("relation") == "PLEDGED"]
            if len(in_insts) > 1:
                anomalies.append({
                    "type": "SHARED_FDR_CROSS_INSTITUTION",
                    "fdr_node": node,
                    "institutions": in_insts,
                    "description": f"FDR node {node} is linked to {len(in_insts)} different institutions!"
                })

    # 2. Shared Signatory across disconnected societies
    for sig_id, sig_name in signatories:
        out_insts = [v for u, v, k, d in G.out_edges(sig_id, keys=True, data=True) if d.get("relation") == "AUTHORIZED_SIGNATORY"]
        if len(out_insts) > 1:
            anomalies.append({
                "type": "COMMON_SIGNATORY_MULTIPLE_INSTITUTIONS",
                "signatory": sig_name,
                "institutions": out_insts,
                "description": f"Signatory '{sig_name}' represents {len(out_insts)} institutions."
            })

    # Convert to React Flow format with automated layered layout positions
    rf_nodes = []
    rf_edges = []

    # Simple layered column layout
    type_col_x = {
        "SOCIETY": 60,
        "SIGNATORY": 60,
        "INSTITUTION": 360,
        "FDR": 660,
        "BANK": 960
    }

    type_counters = {"SOCIETY": 0, "SIGNATORY": 0, "INSTITUTION": 0, "FDR": 0, "BANK": 0}

    for node_id, data in G.nodes(data=True):
        ntype = data.get("node_type", "DEFAULT")
        col_x = type_col_x.get(ntype, 200)
        idx = type_counters.get(ntype, 0)
        type_counters[ntype] = idx + 1
        pos_y = 60 + (idx * 110)

        # Highlight if requested
        is_highlighted = (highlight_fdr_id is not None and node_id == f"fdr_{highlight_fdr_id}")

        rf_nodes.append({
            "id": node_id,
            "type": "default",
            "position": {"x": col_x, "y": pos_y},
            "data": {
                "label": f"{data.get('label', node_id)}",
                "node_type": ntype,
                "details": data,
                "is_highlighted": is_highlighted
            },
            "style": {
                "border": "2px solid #FF9933" if is_highlighted else ("#DC2626" if data.get("risk_level") in ["HIGH", "CRITICAL"] else "#1B365D"),
                "backgroundColor": "#FFF7ED" if is_highlighted else ("#FEF2F2" if data.get("risk_level") in ["HIGH", "CRITICAL"] else "#FFFFFF"),
                "borderRadius": "8px",
                "padding": "10px",
                "fontSize": "12px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.08)",
                "width": 180
            }
        })

    edge_counter = 0
    for u, v, k, d in G.edges(keys=True, data=True):
        edge_counter += 1
        relation = d.get("relation", "")
        rf_edges.append({
            "id": f"e_{u}_{v}_{edge_counter}",
            "source": u,
            "target": v,
            "label": relation,
            "animated": relation in ["PLEDGED", "RENEWED_AS"],
            "style": {
                "stroke": "#1B365D" if relation != "RENEWED_AS" else "#138808",
                "strokeWidth": 2
            }
        })

    return {
        "nodes": rf_nodes,
        "edges": rf_edges,
        "graph_metrics": {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "anomalies_detected": len(anomalies),
            "anomalies_list": anomalies
        }
    }


"""
Cytoscape-based interactive network and flowchart components for
molecular pathways, management algorithms, and treatment sequences.
"""

from __future__ import annotations

import dash_cytoscape as cyto

cyto.load_extra_layouts()


_VIVID_STYLESHEET = [
    {
        "selector": "node",
        "style": {
            "background-color": "#6366f1",
            "label": "data(label)",
            "font-size": "11px",
            "color": "#1e293b",
            "text-valign": "center",
            "text-halign": "center",
            "border-width": 2,
            "border-color": "#4f46e5",
            "width": "label",
            "height": "label",
            "padding": "10px",
            "shape": "round-rectangle",
        },
    },
    {
        "selector": "node[type='targetable']",
        "style": {
            "background-color": "#10b981",
            "border-color": "#059669",
            "font-weight": "bold",
        },
    },
    {
        "selector": "node[type='drug']",
        "style": {
            "background-color": "#ec4899",
            "border-color": "#db2777",
            "shape": "ellipse",
        },
    },
    {
        "selector": "node[type='pathway']",
        "style": {
            "background-color": "#f59e0b",
            "border-color": "#d97706",
            "shape": "rectangle",
            "width": 140,
            "height": 50,
        },
    },
    {
        "selector": "node[type='decision']",
        "style": {
            "background-color": "#3b82f6",
            "border-color": "#2563eb",
            "shape": "diamond",
        },
    },
    {
        "selector": "node[type='treatment']",
        "style": {
            "background-color": "#8b5cf6",
            "border-color": "#7c3aed",
            "shape": "round-rectangle",
        },
    },
    {
        "selector": "node[type='outcome']",
        "style": {
            "background-color": "#ef4444",
            "border-color": "#dc2626",
            "shape": "ellipse",
        },
    },
    {
        "selector": "edge",
        "style": {
            "width": 2,
            "line-color": "#cbd5e1",
            "target-arrow-color": "#cbd5e1",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 1.2,
        },
    },
    {
        "selector": "edge[type='activates']",
        "style": {"line-color": "#10b981", "target-arrow-color": "#10b981"},
    },
    {
        "selector": "edge[type='inhibits']",
        "style": {"line-color": "#ef4444", "target-arrow-color": "#ef4444",
                  "line-style": "dashed"},
    },
    {
        "selector": "edge[type='binds']",
        "style": {"line-color": "#6366f1", "target-arrow-color": "#6366f1",
                  "width": 3},
    },
    {
        "selector": ":selected",
        "style": {"border-width": 3, "border-color": "#f59e0b"},
    },
]


def _build_cyto(elements: list[dict], layout_name: str = "breadthfirst",
                min_zoom: float = 0.3, max_zoom: float = 3.0,
                height: str = "420px") -> cyto.Cytoscape:
    return cyto.Cytoscape(
        id={"type": "cyto", "index": layout_name},
        layout={"name": layout_name, "animate": True, "animationDuration": 500},
        style={"width": "100%", "height": height, "border": "1px solid #e2e8f0",
               "borderRadius": "12px", "background": "#fafbfc"},
        elements=elements,
        stylesheet=_VIVID_STYLESHEET,
        minZoom=min_zoom,
        maxZoom=max_zoom,
        responsive=True,
        userPanningEnabled=True,
        userZoomingEnabled=True,
        boxSelectionEnabled=False,
        autoungrabify=False,
    )


def molecular_network(data: dict) -> cyto.Cytoscape | None:
    """Cytoscape network for molecular pathways and gene interactions.

    Expected data format:
    {
        "nodes": [{"id": "PI3K", "label": "PI3K", "type": "pathway"}, ...],
        "edges": [{"source": "RTK", "target": "PI3K", "type": "activates"}, ...]
    }
    """
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    if not nodes:
        return None
    elements = []
    for n in nodes:
        elements.append({
            "data": {
                "id": n["id"], "label": n.get("label", n["id"]),
                "type": n.get("type", "pathway"),
            },
        })
    for e in edges:
        elements.append({
            "data": {
                "source": e["source"], "target": e["target"],
                "type": e.get("type", ""), "label": e.get("label", ""),
            },
        })
    return _build_cyto(elements, layout_name="breadthfirst", height="480px")


def pathway_flowchart(data: dict) -> cyto.Cytoscape | None:
    """Cytoscape flowchart for treatment decision trees.

    Expected data format:
    {
        "nodes": [{"id": "n1", "label": "PS 0-1", "type": "decision"}, ...],
        "edges": [{"source": "n1", "target": "n2", "label": "Yes"}, ...]
    }
    """
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    if not nodes:
        return None
    elements = []
    for n in nodes:
        elements.append({
            "data": {
                "id": n["id"], "label": n.get("label", n["id"]),
                "type": n.get("type", "decision"),
            },
        })
    for e in edges:
        elements.append({
            "data": {
                "source": e["source"], "target": e["target"],
                "label": e.get("label", ""), "type": e.get("type", ""),
            },
        })
    return _build_cyto(elements, layout_name="dagre", height="400px")


def management_flowchart(data: dict) -> cyto.Cytoscape | None:
    """Management algorithm flowchart from structured pathway data."""
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    if not nodes:
        return None
    elements = []
    for n in nodes:
        elements.append({
            "data": {
                "id": n["id"], "label": n.get("label", n["id"]),
                "type": n.get("type", "treatment"),
            },
        })
    for e in edges:
        elements.append({
            "data": {
                "source": e["source"], "target": e["target"],
                "label": e.get("label", ""), "type": e.get("type", ""),
            },
        })
    return _build_cyto(elements, layout_name="breadthfirst", height="380px")

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.cards import disease_grid
from app.components.filters import search_bar
from app.data.loader import get_sites

def layout() -> list:
    sites = get_sites()
    return [
        html.Div([
            html.H2("Oncology Interactive Handbook", className="display-6 mb-2"),
            html.P(
                f"Browse {len(sites)} disease sites, {sum(s.get('regimen_count', 0) for s in sites)} regimens, "
                "with staging, RT doses, key trials, and clinical pearls.",
                className="lead text-muted mb-4",
            ),
            search_bar(search_id="home-search"),
        ], className="text-center py-4"),
        html.Div(id="disease-grid-container", children=disease_grid(sites)),
    ]

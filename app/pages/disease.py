from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.navigation import breadcrumb, generate_toc, sidebar_nav
from app.components.section_renderer import render_handbook
from app.data.loader import get_handbook, get_site, get_regimens_for_site, site_exists


def layout(site_id: str) -> list:
    if not site_exists(site_id):
        return [
            dbc.Alert(f"Disease site '{site_id}' not found.", color="danger"),
            html.A("Back to Home", href="/", className="btn btn-outline-primary"),
        ]

    site = get_site(site_id)
    handbook = get_handbook(site_id)
    toc = generate_toc(handbook)
    regimen_count = len(get_regimens_for_site(site_id))

    return [
        breadcrumb([
            ("Home", "/"),
            (site["display_name"], ""),
        ]),

        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("Sections", className="mb-3"),
                    sidebar_nav(toc),
                ], className="sticky-sidebar p-3"),
            ], xs=12, md=3, lg=2, className="sidebar-col"),

            dbc.Col([
                html.Div(id="disease-header", children=[
                    html.H2(site["display_name"], className="mb-1"),
                    dbc.Badge(f"Archetype {site.get('archetype', '?')}", color="primary", className="me-2"),
                    dbc.Badge(f"{regimen_count} regimens", color="secondary", className="me-2"),
                    dbc.Badge(site.get("id", ""), color="light"),
                    html.P(site.get("description", ""), className="text-muted mt-2"),
                ]),

                html.Hr(),

                html.Div(id="disease-cta", className="mb-4", children=[
                    dbc.Button(
                        [html.I(className="bi bi-table me-1"), "View Regimens"],
                        href=f"/regimens/{site_id}",
                        color="primary",
                        className="me-2",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-bar-chart me-1"), "Trial Evidence"],
                        href=f"/trials/{site_id}",
                        color="success",
                    ),
                ]),

                html.Div(id="disease-content", children=render_handbook(handbook)),
            ], xs=12, md=9, lg=10, className="content-col"),
        ]),
    ]

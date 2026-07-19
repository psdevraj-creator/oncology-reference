from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.filters import search_bar, filter_bar
from app.components.navigation import breadcrumb
from app.components.tables import create_table
from app.data.loader import (
    get_all_settings,
    get_all_modalities,
    get_all_biomarkers,
    get_regimens_for_site,
    get_regimens_df,
    get_site,
    site_exists,
)
from app.data.transforms import flatten_regimens_for_table


REGIMEN_DISPLAY_COLS = [
    {"name": "Regimen", "id": "regimen_name"},
    {"name": "Setting", "id": "setting"},
    {"name": "Modality", "id": "Modality"},
    {"name": "Drugs", "id": "Drugs"},
    {"name": "Biomarkers", "id": "Biomarkers"},
    {"name": "Evidence", "id": "evidence_level"},
    {"name": "Category", "id": "guideline_category"},
]


def layout(site_id: str | None = None) -> list:
    if site_id:
        if not site_exists(site_id):
            return [
                dbc.Alert(f"Disease site '{site_id}' not found.", color="danger"),
                html.A("Back to Home", href="/", className="btn btn-outline-primary"),
            ]
        site = get_site(site_id)
        df = get_regimens_for_site(site_id)
        title = f"Regimens: {site['display_name']}"
        crumbs = [("Home", "/"), (site["display_name"], f"/disease/{site_id}"), ("Regimens", "")]
    else:
        df = get_regimens_df()
        title = "All Regimens"
        crumbs = [("Home", "/"), ("Regimens", "")]

    df_flat = flatten_regimens_for_table(df)
    table_cols = [c for c in REGIMEN_DISPLAY_COLS if c["id"] in df_flat.columns]
    store_data = df_flat.to_dict("records")

    return [
        breadcrumb(crumbs),
        html.H3(title, className="mb-3"),

        dbc.Row([
            dbc.Col(search_bar(
                placeholder="Search regimens, drugs, biomarkers...",
                search_id="regimen-search",
            ), xs=12),
        ]),

        filter_bar(
            settings=get_all_settings(site_id),
            modalities=get_all_modalities(site_id),
            biomarkers=get_all_biomarkers(site_id),
        ),

        dcc.Store(id="regimen-store", data=store_data),

        html.Div(id="regimen-table-container", children=[
            create_table(
                data=store_data,
                columns=table_cols,
                id="regimen-table",
                row_selectable="single",
                selected_rows=[],
                page_size=20,
            ),
        ]),

        html.Div(id="regimen-detail", className="mt-4"),
    ]


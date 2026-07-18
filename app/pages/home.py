from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.cards import category_sections
from app.data.category_map import SYSTEMS, group_sites_by_system
from app.data.loader import get_sites


def _quick_jump_pills() -> html.Div:
    options = [{"label": "All", "value": "all"}]
    for key, info in sorted(SYSTEMS.items(), key=lambda x: x[1]["order"]):
        options.append({"label": info["name"], "value": key})
    return html.Div([
        dbc.RadioItems(
            id="quick-jump",
            options=options,
            value="all",
            inline=True,
            className="quick-jump-radio",
        ),
    ], className="quick-jump-strip")


def _stat_strip(site_count: int, regimen_count: int, system_count: int) -> html.Div:
    return html.Div([
        dbc.Badge(f"{site_count} Disease Sites", className="stat-badge rounded-pill"),
        dbc.Badge(f"{regimen_count:,} Regimens", className="stat-badge rounded-pill"),
        dbc.Badge("41 Handbooks", className="stat-badge rounded-pill"),
        dbc.Badge(f"{system_count} Systems", className="stat-badge rounded-pill"),
    ], className="stat-strip")


def layout() -> list:
    sites = get_sites()
    total_regimens = sum(s.get("regimen_count", 0) for s in sites)
    grouped = group_sites_by_system(sites)

    return [
        html.Div([
            html.Div([
                html.H1("Oncology Handbook", className="hero-title-light"),
                html.P(
                    "Staging, regimens, RT doses, key trials, biomarkers, and FRCR pearls — "
                    "structured and searchable across 41 disease sites.",
                    className="hero-subtitle-light",
                ),
                html.Div([
                    dbc.Input(
                        id="home-search",
                        type="search",
                        placeholder="Search diseases, regimens, biomarkers, settings...",
                        className="hero-search-input",
                        debounce=True,
                    ),
                    html.I(className="hero-search-icon"),
                ], className="hero-search-wrapper"),
            ], className="hero-inner"),
        ], className="hero-section-light"),

        _stat_strip(len(sites), total_regimens, len(SYSTEMS)),

        _quick_jump_pills(),

        html.Div(id="disease-grid-container", children=category_sections(grouped)),
    ]

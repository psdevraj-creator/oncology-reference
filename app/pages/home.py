from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.cards import disease_grid
from app.data.loader import get_sites


def _stat_card(number: str, label: str, icon: str, color: str) -> dbc.Col:
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.Div(icon, className="stat-icon", style={"color": color}),
                html.Div(number, className="stat-number"),
                html.Div(label, className="stat-label"),
            ]),
            className="stat-card shadow-sm text-center h-100",
        ),
        xs=6, sm=6, md=3,
        className="mb-3",
    )


def layout() -> list:
    sites = get_sites()
    total_regimens = sum(s.get("regimen_count", 0) for s in sites)
    archetypes = sorted(set(s.get("archetype", "?") for s in sites if s.get("archetype")))

    return [
        html.Div([
            html.Div([
                html.H1("Oncology Handbook", className="hero-title"),
                html.P(
                    "Interactive clinical reference for radiation & medical oncology. "
                    "Staging, regimens, RT doses, key trials, biomarkers, and FRCR pearls — "
                    "structured and searchable.",
                    className="hero-subtitle",
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
        ], className="hero-section"),

        dbc.Row([
            _stat_card("41", "Disease Sites", "", "#1a5276"),
            _stat_card(f"{total_regimens:,}", "Regimens", "", "#2c7ba0"),
            _stat_card("41", "Handbooks", "", "#27ae60"),
            _stat_card(str(len(archetypes)), "Archetypes", "", "#e67e22"),
        ], className="stats-row g-3"),

        html.Hr(className="section-divider"),

        html.Div([
            html.H3("Browse by Disease Site", className="section-title"),
            html.P(
                "Select a disease to explore structured handbook content — staging tables, "
                "RT dose frameworks, key trial summaries, systemic therapy regimens, "
                "complications, follow-up schedules, and clinical pearls.",
                className="section-description",
            ),
        ], className="section-header"),

        html.Div(id="disease-grid-container", children=disease_grid(sites)),
    ]

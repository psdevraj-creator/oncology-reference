from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.navigation import breadcrumb
from app.components.trial_viz import (
    render_forest_plot,
    render_pubmed_search_widget,
    render_trial_card,
)
from app.data.loader import (
    get_handbook,
    get_pubmed_data,
    get_site,
    site_exists,
)


def _collect_trials(site_id: str) -> list[dict]:
    handbook = get_handbook(site_id)
    if not handbook:
        return []
    return handbook.get("key_trials", []) or []


def layout(site_id: str | None = None) -> list:
    if site_id:
        if not site_exists(site_id):
            return [
                dbc.Alert(f"Disease site '{site_id}' not found.", color="danger"),
                html.A("Back to Home", href="/", className="btn btn-outline-primary"),
            ]
        site = get_site(site_id)
        trials = _collect_trials(site_id)
        title = f"Trial Evidence: {site['display_name']}"
        crumbs = [
            ("Home", "/"),
            (site["display_name"], f"/disease/{site_id}"),
            ("Trial Evidence", ""),
        ]
    else:
        trials = []
        for s in [s for s in [_get_site_for_id(sid) for sid in _get_all_site_ids()] if s]:
            pass
        title = "Trial Evidence — All Sites"
        crumbs = [("Home", "/"), ("Trial Evidence", "")]

    trial_cards = []
    for i, t in enumerate(trials):
        name = t.get("acronym") or t.get("trial_name", "")
        pubmed = get_pubmed_data(name) if name else None
        trial_cards.append(render_trial_card(t, pubmed, i))

    return [
        breadcrumb(crumbs),
        html.H3(title, className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5(f"{len(trials)} Key Trials", className="mb-1"),
                    html.P(
                        "Hazard ratios and confidence intervals extracted from handbook data. "
                        "PubMed abstracts supplement published evidence.",
                        className="text-muted small",
                    ),
                ], className="mb-3"),

                render_forest_plot(trials) if trials else html.P(
                    "No trial outcome data available for this site.", className="text-muted"
                ),
            ], xs=12, lg=8),
            dbc.Col([
                render_pubmed_search_widget(),
            ], xs=12, lg=4),
        ]),

        html.Hr(),

        html.H5("Trial Summaries", className="mb-3"),
        html.Div(trial_cards) if trial_cards else html.P(
            "No trial data available.", className="text-muted"
        ),
    ]


def _get_all_site_ids():
    from app.data.loader import get_sites
    return [s["id"] for s in get_sites()]


def _get_site_for_id(sid):
    from app.data.loader import get_site
    return get_site(sid)

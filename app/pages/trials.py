from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.navigation import breadcrumb
from app.components.trial_viz import (
    render_forest_plot,
    render_orr_waterfall,
    render_phase_donut,
    render_pubmed_search_widget,
    render_survival_bars,
    render_trial_card,
    render_trial_timeline,
)
from app.components.evidence_viz import render_evidence_dashboard
from app.data.loader import (
    get_handbook,
    get_pubmed_data,
    get_regimens_for_site,
    get_regimens_df,
    get_site,
    site_exists,
)


def _collect_all_trials(site_id: str | None) -> list[dict]:
    trials: list[dict] = []
    seen: set[str] = set()

    if site_id:
        handbook = get_handbook(site_id)
        kt = handbook.get("key_trials", []) if handbook else []
        for t in (kt if isinstance(kt, list) else []):
            if not isinstance(t, dict):
                continue
            acronym = (t.get("acronym") or "").strip()
            if acronym and acronym not in seen:
                seen.add(acronym)
                trials.append(t)

        df = get_regimens_for_site(site_id)
        for _, row in df.iterrows():
            td = row.get("trial_data")
            if not isinstance(td, dict):
                continue
            name = str(td.get("trial_name", "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            trials.append({
                "acronym": name,
                "trial_name": name,
                "phase": str(td.get("phase", "")) if td.get("phase") else "",
                "n_patients": str(td.get("n_patients", "")) if td.get("n_patients") else "",
                "key_result": str(td.get("os_hr") or td.get("pfs_hr") or ""),
            })
    else:
        for sid in [s["id"] for s in [_get_site_for_id(sid) for sid in _get_all_ids()] if s]:
            pass

    return trials


def layout(site_id: str | None = None) -> list:
    if site_id:
        if not site_exists(site_id):
            return [
                dbc.Alert(f"Disease site '{site_id}' not found.", color="danger"),
                html.A("Back to Home", href="/", className="btn btn-outline-primary"),
            ]
        site = get_site(site_id)
        trials = _collect_all_trials(site_id)
        title = f"Trial Evidence: {site['display_name']}"
        crumbs = [("Home", "/"), (site["display_name"], f"/disease/{site_id}"), ("Trial Evidence", "")]
    else:
        trials = _collect_all_trials(None)
        title = "Trial Evidence — All Sites"
        crumbs = [("Home", "/"), ("Trial Evidence", "")]

    handbook_trials = []
    regimen_trials = []
    for t in trials:
        if t.get("key_result") or t.get("population"):
            handbook_trials.append(t)
        else:
            regimen_trials.append(t)

    all_with_data = [t for t in trials if t.get("key_result") or t.get("phase") or t.get("year") or t.get("n")]

    trial_cards = []
    for i, t in enumerate(trials):
        name = t.get("acronym") or t.get("trial_name", "")
        pubmed = get_pubmed_data(name) if name else None
        trial_cards.append(render_trial_card(t, pubmed, i))

    return [
        breadcrumb(crumbs),
        html.H3(title, className="mb-3"),

        html.P(
            f"{len(handbook_trials)} handbook trials + {len(regimen_trials)} regimen-referenced trials = "
            f"{len(trials)} total unique trials for this site.",
            className="text-muted small mb-3",
        ),

        dbc.Row([
            dbc.Col(render_phase_donut(all_with_data), xs=12, md=4),
            dbc.Col(render_survival_bars(all_with_data), xs=12, md=8),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(render_forest_plot(all_with_data, height=450), xs=12, lg=8),
            dbc.Col(render_pubmed_search_widget(), xs=12, lg=4),
        ]),

        dbc.Row([
            dbc.Col(render_orr_waterfall(all_with_data), xs=12, md=6),
            dbc.Col(render_trial_timeline(all_with_data), xs=12, md=6),
        ], className="mb-3"),

        html.Hr(),
        html.H5("Evidence Dashboard", className="mb-3"),
        render_evidence_dashboard(all_with_data),

        html.Hr(),
        html.H5(f"Trial Summaries ({len(trials)})", className="mb-3"),
        html.Div(trial_cards) if trial_cards else html.P("No trial data available.", className="text-muted"),
    ]


def _get_all_ids():
    from app.data.loader import get_sites
    return [s["id"] for s in get_sites()]


def _get_site_for_id(sid):
    from app.data.loader import get_site
    return get_site(sid)

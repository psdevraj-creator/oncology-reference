from typing import Any, Optional

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.tables import create_table


def _table_label(description: str, max_len: int = 200) -> str:
    if len(description) > max_len:
        return description[: max_len - 3] + "..."
    return description


def render_t_stages(t_stages: list[dict[str, Any]]) -> list:
    if not t_stages:
        return [html.P("No T-stage data available.", className="text-muted")]
    rows = []
    for s in t_stages:
        rows.append(html.Tr([
            html.Td(html.Strong(s.get("stage", s.get("category", "")))),
            html.Td(s.get("description", "")),
        ]))
    return [
        html.H5("T Categories", className="mt-3"),
        dbc.Table(
            [html.Thead(html.Tr([html.Th("Category"), html.Th("Description")]))]
            + [html.Tbody(rows)],
            bordered=True, hover=True, size="sm", className="staging-table",
        ),
    ]


def render_n_stages(n_stages: list[dict[str, Any]]) -> list:
    if not n_stages:
        return [html.P("No N-stage data available.", className="text-muted")]
    rows = []
    for s in n_stages:
        rows.append(html.Tr([
            html.Td(html.Strong(s.get("stage", s.get("category", "")))),
            html.Td(s.get("description", "")),
        ]))
    return [
        html.H5("N Categories", className="mt-3"),
        dbc.Table(
            [html.Thead(html.Tr([html.Th("Category"), html.Th("Description")]))]
            + [html.Tbody(rows)],
            bordered=True, hover=True, size="sm", className="staging-table",
        ),
    ]


def render_m_stages(m_stages: list[dict[str, Any]]) -> list:
    if not m_stages:
        return [html.P("No M-stage data available.", className="text-muted")]
    rows = []
    for s in m_stages:
        rows.append(html.Tr([
            html.Td(html.Strong(s.get("stage", s.get("category", "")))),
            html.Td(s.get("description", "")),
        ]))
    return [
        html.H5("M Categories", className="mt-3"),
        dbc.Table(
            [html.Thead(html.Tr([html.Th("Category"), html.Th("Description")]))]
            + [html.Tbody(rows)],
            bordered=True, hover=True, size="sm", className="staging-table",
        ),
    ]


def render_stage_groups(stage_groups: list[dict[str, Any]]) -> list:
    if not stage_groups:
        return [html.P("No stage group data available.", className="text-muted")]
    cols = ["Stage", "T", "N", "M", "5-Year Survival", "Treatment Intent"]
    rows = []
    for sg in stage_groups:
        rows.append({
            "Stage": sg.get("group", sg.get("stage", "")),
            "T": sg.get("t", sg.get("criteria", "")),
            "N": sg.get("n", ""),
            "M": sg.get("m", ""),
            "5-Year Survival": sg.get("five_yr_survival", ""),
            "Treatment Intent": sg.get("treatment_intent", ""),
        })
    return [
        html.H5("Stage Groupings", className="mt-3"),
        create_table(
            data=rows,
            columns=[{"name": c, "id": c} for c in cols],
            page_size=25,
            filter_action="none",
        ),
    ]


def render_staging(staging: dict[str, Any]) -> list:
    if not staging:
        return [html.P("No staging data available.", className="text-muted")]
    components: list = [
        html.H4("Staging", className="section-heading"),
        html.P(staging.get("system", ""), className="text-muted"),
    ]
    t_stages = staging.get("t_stages") or staging.get("t_categories", [])
    n_stages = staging.get("n_stages") or staging.get("n_categories", [])
    m_stages = staging.get("m_stages") or staging.get("m_categories", [])
    stage_groups = staging.get("stage_groups") or staging.get("stage_groupings", [])

    components.extend(render_t_stages(t_stages))
    components.extend(render_n_stages(n_stages))
    components.extend(render_m_stages(m_stages))
    components.extend(render_stage_groups(stage_groups))

    pearls = staging.get("staging_pearls", [])
    if pearls:
        components.append(html.H5("Staging Pearls", className="mt-3"))
        components.append(html.Ul([html.Li(p) for p in pearls]))

    return components


def render_radiation_therapy(rt: dict[str, Any]) -> list:
    if not rt:
        return []
    components = [
        html.H4("Radiation Therapy", className="section-heading"),
        html.P(rt.get("role", ""), className="text-muted"),
    ]
    principles = rt.get("principles", [])
    if principles:
        components.append(html.H6("Principles"))
        components.append(html.Ul([html.Li(p) for p in principles]))

    dose_frameworks = rt.get("dose_frameworks", [])
    if dose_frameworks:
        components.append(html.H6("Dose Frameworks", className="mt-3"))
        components.append(create_table(
            data=dose_frameworks,
            page_size=15,
            filter_action="none",
        ))

    approaches = rt.get("approaches", [])
    if approaches:
        components.append(html.H6("Approaches", className="mt-3"))
        components.append(create_table(
            data=approaches,
            page_size=15,
            filter_action="none",
        ))

    return components


def render_trials(key_trials: list[dict[str, Any]]) -> list:
    if not key_trials:
        return []

    from app.components.trial_viz import render_forest_plot, render_trial_card
    from app.data.loader import get_pubmed_data

    components = [html.H4("Key Trials", className="section-heading")]

    forest = render_forest_plot(key_trials)
    components.append(forest)

    components.append(html.H5("Trial Summaries", className="mt-4 mb-3"))
    for i, t in enumerate(key_trials):
        name = t.get("acronym") or t.get("trial_name", "")
        pubmed = get_pubmed_data(name) if name else None
        components.append(render_trial_card(t, pubmed, i))

    return components


def render_prognosis(prognosis: dict[str, Any]) -> list:
    if not prognosis:
        return []
    components = [
        html.H4("Prognosis", className="section-heading"),
        html.P(prognosis.get("overall", ""), className="text-muted"),
    ]
    by_stage = prognosis.get("by_stage", [])
    if by_stage:
        components.append(html.H6("By Stage", className="mt-3"))
        components.append(create_table(
            data=by_stage,
            page_size=15,
            filter_action="none",
        ))
    factors = prognosis.get("prognostic_factors", [])
    if factors:
        components.append(html.H6("Prognostic Factors"))
        components.append(html.Ul([html.Li(f) for f in factors]))
    return components

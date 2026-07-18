from typing import Any, Optional

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from app.data.loader import get_pubmed_data as _get_pubmed


def _parse_hr(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    return None


def _parse_ci(value: Any) -> tuple[Optional[float], Optional[float]]:
    if value is None:
        return None, None
    s = str(value).strip().strip("()[]").strip()
    parts = s.replace(",", " ").split()
    if len(parts) >= 2:
        try:
            return float(parts[0]), float(parts[-1])
        except ValueError:
            pass
    try:
        return float(parts[0]), None
    except (ValueError, IndexError):
        pass
    return None, None


def render_forest_plot(
    trials: list[dict[str, Any]],
    height: int = 500,
) -> html.Div:
    if not trials:
        return html.Div("No trial outcome data available for forest plot.", className="text-muted p-3")

    plot_data: list[dict] = []
    for t in trials:
        hr = _parse_hr(t.get("os_hr") or t.get("pfs_hr") or t.get("dfs_hr"))
        ci_lo, ci_hi = None, None
        ci_raw = t.get("os_ci") or t.get("pfs_ci") or t.get("dfs_ci")
        if ci_raw:
            ci_lo, ci_hi = _parse_ci(ci_raw)
        if hr is not None:
            plot_data.append({
                "trial": t.get("acronym") or t.get("trial_name", "?"),
                "hr": hr,
                "ci_lo": ci_lo if ci_lo is not None else hr * 0.75,
                "ci_hi": ci_hi if ci_hi is not None else hr * 1.35,
                "endpoint": "OS" if t.get("os_hr") else "PFS" if t.get("pfs_hr") else "DFS" if t.get("dfs_hr") else "?",
                "n": t.get("n") or t.get("n_patients", ""),
            })

    if not plot_data:
        return html.Div("No numerical HR data available for forest plot.", className="text-muted p-3")

    df = pd.DataFrame(plot_data)
    df = df.sort_values("hr")
    df["error_lo"] = df["hr"] - df["ci_lo"]
    df["error_hi"] = df["ci_hi"] - df["hr"]
    df["color"] = df["hr"].apply(lambda x: "#27ae60" if x < 0.85 else "#e67e22" if x < 1.0 else "#c0392b" if x > 1.15 else "#7f8c8d")
    df["label"] = df.apply(
        lambda r: f"<b>{r['trial']}</b><br>HR={r['hr']:.2f} (95% CI {r['ci_lo']:.2f}–{r['ci_hi']:.2f})<br>{r['endpoint']}  N={r['n']}",
        axis=1,
    )

    fig = go.Figure()

    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["hr"]],
            y=[row["trial"]],
            mode="markers",
            marker=dict(size=12, color=row["color"], line=dict(width=1.5, color="white")),
            error_x=dict(
                type="data",
                symmetric=False,
                array=[row["error_hi"]],
                arrayminus=[row["error_lo"]],
                thickness=2,
                width=4,
                color=row["color"],
            ),
            name=row["trial"],
            hovertemplate=row["label"],
            showlegend=False,
        ))

    fig.add_vline(x=1.0, line_dash="dash", line_color="#95a5a6", line_width=1.5, annotation_text="HR=1")

    fig.update_layout(
        xaxis_title="Hazard Ratio",
        xaxis=dict(type="log", tickformat=".2f", range=[-0.5, 1.2]),
        yaxis=dict(autorange="reversed"),
        height=min(height, max(250, len(df) * 28)),
        margin=dict(l=10, r=10, t=10, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=12, family="Segoe UI, system-ui, sans-serif"),
        hovermode="closest",
    )

    return html.Div([
        html.H5("Trial Forest Plot", className="mb-2"),
        dcc.Graph(figure=fig, config={"displayModeBar": True, "toImageButtonOptions": {"format": "png"}}),
    ], className="forest-plot-container")


def render_trial_card(
    trial: dict[str, Any],
    pubmed_data: Optional[dict] = None,
    index: int = 0,
) -> dbc.Card:
    acronym = trial.get("acronym", trial.get("trial_name", "?"))
    year = trial.get("year", "")
    phase = trial.get("phase", "")
    n_val = trial.get("n") or trial.get("n_patients", "")
    population = trial.get("population", "")
    intervention = trial.get("intervention", "")
    comparator = trial.get("comparator", "")
    endpoint = trial.get("primary_endpoint", "")
    key_result = trial.get("key_result", "")
    practice_change = trial.get("practice_change", "")

    header_parts = [acronym]
    if year:
        header_parts.append(f"({year})")
    if phase:
        header_parts.append(f"Phase {phase}")
    if n_val:
        header_parts.append(f"N={n_val}")

    badge_row = []
    if year:
        badge_row.append(dbc.Badge(year, color="dark", className="me-1"))
    if phase:
        badge_row.append(dbc.Badge(f"Phase {phase}", color="info", className="me-1"))
    if n_val:
        badge_row.append(dbc.Badge(f"N={n_val}", color="secondary", className="me-1"))
    if pubmed_data and pubmed_data.get("pmid"):
        badge_row.append(html.A(
            dbc.Badge("PubMed", color="success", className="me-1"),
            href=f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_data['pmid']}",
            target="_blank",
            className="text-decoration-none",
        ))

    body_items = []
    if population:
        body_items.append(html.P([html.Strong("Population: "), population], className="mb-1 small"))
    if intervention:
        body_items.append(html.P([html.Strong("Intervention: "), intervention], className="mb-1 small"))
    if comparator:
        body_items.append(html.P([html.Strong("Comparator: "), comparator], className="mb-1 small"))
    if endpoint:
        body_items.append(html.P([html.Strong("Primary Endpoint: "), endpoint], className="mb-1 small"))
    if key_result:
        body_items.append(html.P([html.Strong("Key Result: "), key_result], className="mb-1 small"))

    if practice_change:
        body_items.append(dbc.Alert(practice_change, color="success", className="mt-2 mb-0 py-2 small"))

    abstract_section = None
    if pubmed_data and pubmed_data.get("abstract"):
        abstract_section = dbc.Accordion([
            dbc.AccordionItem(
                html.P(pubmed_data["abstract"][:800] + ("..." if len(pubmed_data.get("abstract", "")) > 800 else ""), className="small text-muted"),
                title="Abstract",
                item_id=f"abstract-{index}",
            ),
        ], start_collapsed=True, className="mt-2")

    children = [
        html.Div(badge_row, className="mb-2"),
        *body_items,
    ]
    if abstract_section:
        children.append(abstract_section)

    return dbc.Card(
        dbc.CardBody(children),
        className="trial-card shadow-sm mb-3",
        style={"borderLeft": "4px solid #2c7ba0"},
    )


def render_trial_outcomes_comparison(trial_data: dict[str, Any]) -> html.Div:
    if not trial_data or not isinstance(trial_data, dict):
        return html.Div()

    trial_name = trial_data.get("trial_name", "")
    phase = trial_data.get("phase", "")
    n_patients = trial_data.get("n_patients", "")

    header = []
    if trial_name:
        header.append(html.H6(trial_name, className="mb-1"))
    if phase or n_patients:
        parts = []
        if phase:
            parts.append(f"Phase {phase}")
        if n_patients:
            parts.append(f"N={n_patients}")
        header.append(html.P(", ".join(parts), className="text-muted small"))

    outcomes = []
    metrics = [
        ("OS", "os_median_experimental", "os_median_control", "os_hr", "os_ci"),
        ("PFS", "pfs_median_experimental", "pfs_median_control", "pfs_hr", "pfs_ci"),
        ("DFS", "dfs_median_experimental", "dfs_median_control", "dfs_hr", "dfs_ci"),
        ("ORR", "orr_experimental", "orr_control", None, None),
    ]

    for label, exp_key, ctrl_key, hr_key, ci_key in metrics:
        exp_val = trial_data.get(exp_key)
        ctrl_val = trial_data.get(ctrl_key)
        hr_val = trial_data.get(hr_key) if hr_key else None

        if not exp_val and not ctrl_val:
            continue

        cols = []
        if exp_val:
            cols.append(dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.Div("Experimental", className="text-muted small text-uppercase"),
                        html.Div(str(exp_val), className="fw-bold h5 mb-0"),
                    ]),
                    className="border-primary",
                ),
                width=4,
            ))
        if ctrl_val:
            cols.append(dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.Div("Control", className="text-muted small text-uppercase"),
                        html.Div(str(ctrl_val), className="fw-bold h5 mb-0"),
                    ]),
                    className="border-secondary",
                ),
                width=4,
            ))
        if hr_val:
            hr_f = _parse_hr(hr_val)
            ci_str = ""
            if ci_key:
                ci_val = trial_data.get(ci_key, "")
                if ci_val:
                    ci_str = f" ({ci_val})"
            hr_color = "#27ae60" if (hr_f and hr_f < 0.9) else "#7f8c8d"
            cols.append(dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.Div("HR" + ci_str, className="text-muted small text-uppercase"),
                        html.Div(str(hr_val), className="fw-bold h5 mb-0", style={"color": hr_color}),
                    ]),
                    className="border-info",
                ),
                width=4,
            ))

        if cols:
            outcomes.append(html.Div([
                html.Div(label, className="fw-bold small mt-2 mb-1"),
                dbc.Row(cols, className="g-2"),
            ]))

    if not outcomes:
        return html.Div()

    return html.Div([
        *header,
        *outcomes,
    ], className="trial-outcomes-comparison mb-3")


def render_pubmed_search_widget() -> html.Div:
    return html.Div([
        html.H5("Live PubMed Search", className="mb-2"),
        dbc.InputGroup([
            dbc.Input(
                id="pubmed-search-input",
                type="text",
                placeholder="Search PubMed for clinical trials (e.g. KEYNOTE-522, SBRT lung)...",
                className="form-control",
            ),
            dbc.Button("Search", id="pubmed-search-btn", color="primary", n_clicks=0),
        ], className="mb-3"),
        html.Div(id="pubmed-search-results"),
        html.Div(id="pubmed-search-status"),
    ], className="pubmed-search-widget mb-4 p-3 bg-light rounded")

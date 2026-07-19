"""
Evidence Visualization Component
Integrates parsed abstract outcomes + NCT verified data into Plotly/dbc charts.
Provides trial evidence summaries for the Dash app.

Usage:
    from app.components.evidence_viz import (
        render_trial_evidence_card,
        render_outcomes_table,
        render_forest_summary,
        render_enrollment_chart,
        render_toxicity_heatmap,
    )
"""

import json
from pathlib import Path
from typing import Optional

import dash_bootstrap_components as dbc
import pandas as pd
from dash import dcc, html

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PUBMED_DIR = DATA_DIR / "pubmed"
OUTCOMES_DIR = DATA_DIR / "abstract_outcomes"
NCT_DIR = DATA_DIR / "nct"


# ── Loaders ────────────────────────────────────────────────────

def _load_outcomes(pmid: str) -> Optional[dict]:
    fp = OUTCOMES_DIR / f"{pmid}.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _load_pubmed_cache(trial_name: str) -> Optional[dict]:
    import re
    safe = re.sub(r"[^a-z0-9_]", "_", trial_name.lower().strip())
    safe = re.sub(r"_+", "_", safe).strip("_")[:80]
    fp = PUBMED_DIR / f"{safe}.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _load_nct_data(trial_name: str) -> Optional[dict]:
    import re
    safe = re.sub(r"[^a-z0-9_]", "_", trial_name.lower().strip())
    safe = re.sub(r"_+", "_", safe).strip("_")[:80]
    fp = NCT_DIR / f"{safe}.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


# ── Evidence card ──────────────────────────────────────────────

def render_trial_evidence_card(trial_name: str, trial_data: Optional[dict] = None) -> html.Div:
    """Render a comprehensive trial evidence card with NCT, PubMed, and parsed outcomes."""
    pubmed = _load_pubmed_cache(trial_name)
    nct = _load_nct_data(trial_name)

    pmid = pubmed.get("pmid", "") if pubmed else ""
    outcomes = _load_outcomes(pmid) if pmid else None

    cards = []

    # PMID badge row
    badge_row = []
    if pubmed:
        badge_row.append(dbc.Badge("PubMed", color="primary", className="me-1"))
        badge_row.append(dbc.Badge(f"PMID:{pubmed['pmid']}", color="success", className="me-1 rounded-pill"))
        if pubmed.get("year"):
            badge_row.append(dbc.Badge(pubmed["year"], color="dark", className="me-1 rounded-pill"))
    if nct:
        badge_row.append(dbc.Badge(f"NCT Verified", color="warning", className="me-1 rounded-pill"))
    if outcomes and (outcomes.get("hr") or outcomes.get("orr") or outcomes.get("os_median")):
        badge_row.append(dbc.Badge("Parsed Outcomes", color="info", className="me-1 rounded-pill"))

    if badge_row:
        cards.append(html.Div(badge_row, className="mb-2"))

    # Trial info
    if pubmed:
        title = pubmed.get("title", trial_name)
        journal = pubmed.get("journal", "")
        authors = pubmed.get("authors", [])
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        doi = pubmed.get("doi", "")

        cards.append(html.H6(title, className="mb-1"))
        if journal or author_str:
            cards.append(html.P(f"{journal}. {author_str}", className="text-muted small mb-2"))
        if doi:
            cards.append(html.A(f"DOI: {doi}", href=f"https://doi.org/{doi}", target="_blank",
                                className="small text-decoration-none mb-2 d-block"))

    # Outcomes summary
    if outcomes:
        outcome_badges = []
        if outcomes.get("os_median"):
            outcome_badges.append(dbc.Badge(f"OS: {outcomes['os_median']} mo", color="danger", className="me-1"))
        if outcomes.get("pfs_median"):
            outcome_badges.append(dbc.Badge(f"PFS: {outcomes['pfs_median']} mo", color="warning", className="me-1"))
        if outcomes.get("orr"):
            outcome_badges.append(dbc.Badge(f"ORR: {outcomes['orr']}%", color="success", className="me-1"))
        if outcomes.get("hr"):
            hr_text = f"HR: {outcomes['hr']}"
            if outcomes.get("hr_ci_lo") and outcomes.get("hr_ci_hi"):
                hr_text += f" ({outcomes['hr_ci_lo']}-{outcomes['hr_ci_hi']})"
            outcome_badges.append(dbc.Badge(hr_text, color="primary", className="me-1"))
        if outcomes.get("enrollment"):
            outcome_badges.append(dbc.Badge(f"N={outcomes['enrollment']}", color="secondary", className="me-1"))
        if outcome_badges:
            cards.append(html.Div(outcome_badges, className="mb-2"))

    # NCT enrollment + phase
    if nct:
        nct_items = []
        if nct.get("nct_id"):
            nct_items.append(html.A(f"NCT: {nct['nct_id']}", href=f"https://clinicaltrials.gov/study/{nct['nct_id']}",
                                    target="_blank", className="small text-decoration-none me-3"))
        if nct.get("enrollment"):
            nct_items.append(html.Span(f"Enrolled: {nct['enrollment']}", className="small text-muted me-3"))
        if nct.get("phase"):
            nct_items.append(html.Span(f"Phase: {', '.join(nct['phase'])}", className="small text-muted"))
        if nct.get("has_results"):
            nct_items.append(dbc.Badge("CT.gov Results", color="warning", className="ms-2 rounded-pill"))
        if nct_items:
            cards.append(html.Div(nct_items, className="mb-2"))

    # Abstract accordion
    if pubmed and pubmed.get("abstract"):
        abstract_text = pubmed["abstract"]
        cards.append(dbc.Accordion([
            dbc.AccordionItem(
                html.P(abstract_text[:1200] + ("..." if len(abstract_text) > 1200 else ""),
                       className="small text-muted"),
                title="Abstract",
                item_id=f"abs-{trial_name[:20]}",
            ),
        ], start_collapsed=True, className="mb-2"))

    return html.Div(cards, className="evidence-card")


# ── Outcomes table ─────────────────────────────────────────────

def render_outcomes_table(trials: list[dict]) -> html.Div:
    """Render a comparison table of trial outcomes across multiple trials."""
    if not trials:
        return html.Div("No trial data available", className="text-muted p-3")

    rows = []
    for trial in trials:
        name = trial.get("trial_name", trial.get("name", "?"))
        pubmed = _load_pubmed_cache(name)
        pmid = pubmed.get("pmid", "") if pubmed else ""
        outcomes = _load_outcomes(pmid) if pmid else {}

        rows.append({
            "Trial": name[:40],
            "Phase": outcomes.get("phase", trial.get("phase", "")),
            "N": outcomes.get("enrollment", trial.get("n", trial.get("n_patients", ""))),
            "OS (mo)": outcomes.get("os_median", ""),
            "PFS (mo)": outcomes.get("pfs_median", ""),
            "ORR (%)": outcomes.get("orr", ""),
            "HR": f"{outcomes.get('hr','')}" if outcomes.get('hr') else "",
            "PMID": pmid,
        })

    df = pd.DataFrame(rows)

    table = dbc.Table.from_dataframe(
        df,
        striped=True,
        bordered=True,
        hover=True,
        size="sm",
        className="evidence-table mb-0",
    )

    return html.Div(table, className="evidence-table-wrapper")


# ── Forest plot (HR comparison) ────────────────────────────────

def render_forest_summary(trials: list[dict], height: int = 450) -> html.Div:
    import plotly.graph_objects as go
    """Forest plot comparing hazard ratios across trials."""
    if not trials:
        return html.Div("No trial data for forest plot", className="text-muted p-3")

    labels = []
    hrs = []
    ci_los = []
    ci_his = []
    colors = []

    for trial in trials:
        name = trial.get("trial_name", trial.get("name", "?"))
        pubmed = _load_pubmed_cache(name)
        pmid = pubmed.get("pmid", "") if pubmed else ""
        outcomes = _load_outcomes(pmid) if pmid else {}

        hr = (trial.get("hr") or outcomes.get("hr"))
        ci_lo = trial.get("os_ci_lo") or trial.get("hr_ci_lo") or outcomes.get("hr_ci_lo")
        ci_hi = trial.get("os_ci_hi") or trial.get("hr_ci_hi") or outcomes.get("hr_ci_hi")

        if hr:
            try:
                hr = float(hr)
            except (ValueError, TypeError):
                continue

            labels.append(name[:35])
            hrs.append(hr)
            ci_los.append(float(ci_lo) if ci_lo else hr - 0.1)
            ci_his.append(float(ci_hi) if ci_hi else hr + 0.1)
            colors.append("#10b981" if hr < 1 else "#ef4444" if hr > 1 else "#6b7280")

    if not hrs:
        return html.Div("No HR data for forest plot", className="text-muted p-3")

    fig = go.Figure()

    for i in range(len(labels)):
        fig.add_trace(go.Scatter(
            x=[hrs[i]],
            y=[labels[i]],
            mode="markers",
            marker=dict(size=10, color=colors[i]),
            name=labels[i],
            showlegend=False,
            hovertemplate=f"{labels[i]}<br>HR: {hrs[i]:.2f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[ci_los[i], ci_his[i]],
            y=[labels[i], labels[i]],
            mode="lines",
            line=dict(color=colors[i], width=2),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.add_vline(x=1.0, line_dash="dash", line_color="gray", annotation_text="HR=1")

    fig.update_layout(
        height=min(height, max(200, len(labels) * 30 + 80)),
        margin=dict(l=10, r=30, t=30, b=10),
        xaxis_title="Hazard Ratio",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=11),
    )

    return html.Div([
        html.H6("Hazard Ratio Comparison", className="mb-2"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])


# ── Enrollment comparison chart ────────────────────────────────

def render_enrollment_chart(trials: list[dict], height: int = 350) -> html.Div:
    import plotly.express as px
    """Horizontal bar chart comparing trial enrollment sizes."""
    if not trials:
        return html.Div("", className="p-3")

    labels = []
    enrollments = []

    for trial in trials:
        name = trial.get("trial_name", trial.get("name", "?"))
        pubmed = _load_pubmed_cache(name)
        pmid = pubmed.get("pmid", "") if pubmed else ""
        outcomes = _load_outcomes(pmid) if pmid else {}
        nct = _load_nct_data(name)

        n = outcomes.get("enrollment") or nct.get("enrollment") or trial.get("n") or trial.get("n_patients")
        if n:
            try:
                n = int(str(n).replace(",", ""))
            except (ValueError, TypeError):
                continue
            labels.append(name[:35])
            enrollments.append(n)

    if not enrollments:
        return html.Div("No enrollment data", className="text-muted p-3")

    fig = px.bar(
        x=enrollments, y=labels, orientation="h",
        labels={"x": "Patients Enrolled", "y": ""},
        color=enrollments, color_continuous_scale="Blues",
    )
    fig.update_layout(
        height=min(height, max(200, len(labels) * 25 + 60)),
        margin=dict(l=10, r=20, t=30, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=11),
        coloraxis_showscale=False,
    )

    return html.Div([
        html.H6("Trial Enrollment Comparison", className="mb-2"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])


# ── Toxicity heatmap ───────────────────────────────────────────

def render_toxicity_heatmap(trials: list[dict], height: int = 400) -> html.Div:
    import plotly.graph_objects as go
    """Heatmap of grade 3+ toxicities across trials."""
    if not trials:
        return html.Div("", className="p-3")

    all_events = set()
    trial_data = {}

    for trial in trials:
        name = trial.get("trial_name", trial.get("name", "?"))
        pubmed = _load_pubmed_cache(name)
        pmid = pubmed.get("pmid", "") if pubmed else ""
        outcomes = _load_outcomes(pmid) if pmid else {}
        tox = outcomes.get("toxicities", [])

        if tox:
            trial_data[name[:25]] = {t["event"].strip()[:30]: t["rate"] for t in tox}
            all_events.update(trial_data[name[:25]].keys())

    if not trial_data or not all_events:
        return html.Div("No toxicity data available", className="text-muted p-3")

    events = sorted(all_events)[:15]
    trial_names = list(trial_data.keys())

    z = []
    for event in events:
        row = []
        for tn in trial_names:
            row.append(trial_data[tn].get(event, 0))
        z.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=z, x=trial_names, y=events,
        colorscale="Reds", zmin=0, zmax=100,
        hovertemplate="Trial: %{x}<br>Toxicity: %{y}<br>Rate: %{z}%<extra></extra>",
    ))

    fig.update_layout(
        height=min(height, max(200, len(events) * 22 + 80)),
        margin=dict(l=10, r=20, t=30, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=10),
    )

    return html.Div([
        html.H6("Grade 3+ Toxicity Rates (%)", className="mb-2"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])


# ── Trial evidence dashboard ───────────────────────────────────

def render_evidence_dashboard(trials: list[dict]) -> html.Div:
    """Full evidence dashboard for a set of trials."""
    if not trials:
        return html.Div("No trial data to display", className="text-muted p-4")

    # Compute stats
    with_hr = 0
    with_os = 0
    with_orr = 0
    for t in trials:
        name = t.get("trial_name", t.get("name", ""))
        pubmed = _load_pubmed_cache(name)
        pmid = pubmed.get("pmid", "") if pubmed else ""
        outcomes = _load_outcomes(pmid) if pmid else {}
        if outcomes.get("hr"): with_hr += 1
        if outcomes.get("os_median"): with_os += 1
        if outcomes.get("orr"): with_orr += 1

    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(str(len(trials)), className="text-center mb-0"),
            html.P("Trials", className="text-center text-muted small mb-0"),
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(str(with_hr), className="text-center mb-0"),
            html.P("With HR Data", className="text-center text-muted small mb-0"),
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(str(with_os), className="text-center mb-0"),
            html.P("With OS Data", className="text-center text-muted small mb-0"),
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H3(str(with_orr), className="text-center mb-0"),
            html.P("With ORR Data", className="text-center text-muted small mb-0"),
        ])), width=3),
    ], className="mb-3")

    children = [stats]

    # Forest plot
    forest = render_forest_summary(trials)
    children.append(dbc.Card(dbc.CardBody(forest), className="mb-3"))

    # Enrollment chart
    enroll = render_enrollment_chart(trials)
    children.append(dbc.Card(dbc.CardBody(enroll), className="mb-3"))

    # Outcomes table
    outcomes_tbl = render_outcomes_table(trials)
    children.append(dbc.Card(dbc.CardBody([
        html.H6("Outcomes Summary", className="mb-2"),
        outcomes_tbl,
    ]), className="mb-3"))

    # Toxicity heatmap
    tox = render_toxicity_heatmap(trials)
    children.append(dbc.Card(dbc.CardBody(tox), className="mb-3"))

    return html.Div(children)

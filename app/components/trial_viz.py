import re
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


def parse_outcomes_from_text(key_result: str) -> dict[str, Any]:
    if not key_result:
        return {}
    text = str(key_result)

    out: dict[str, Any] = {}

    hr_match = re.search(
        r'(?:HR|hazard\s*ratio)\s*[:=]?\s*([\d.]+)\s*(?:\(?\s*95%\s*CI\s*[:=\s]*([\d.]+)\s*[-–—to]+\s*([\d.]+)\s*\)?)?',
        text, re.IGNORECASE,
    )
    if hr_match:
        try:
            out["hr"] = float(hr_match.group(1))
        except (ValueError, TypeError):
            pass
        if hr_match.group(2) and hr_match.group(3):
            try:
                out["ci_lo"] = float(hr_match.group(2))
                out["ci_hi"] = float(hr_match.group(3))
            except (ValueError, TypeError):
                pass

    alt_ci = re.search(
        r'(?:HR|hazard\s*ratio)\s*[:=]\s*([\d.]+)\s*\(([\d.]+)[,;]?\s*([\d.]+)\s*[-–—to]+\s*([\d.]+)\)',
        text, re.IGNORECASE,
    )
    if alt_ci and not out.get("ci_lo"):
        try:
            out["ci_lo"] = float(alt_ci.group(3))
            out["ci_hi"] = float(alt_ci.group(4))
        except (ValueError, TypeError):
            pass

    os_match = re.search(
        r'(?:median\s+)?OS\s*[:.]?\s*([\d.]+)\s*(?:months?|mo|m)?\s*(?:vs\.?|versus|compared to|v\.?)\s*([\d.]+)\s*(?:months?|mo|m)?',
        text, re.IGNORECASE,
    )
    if os_match:
        try:
            out["os_exp"] = float(os_match.group(1))
            out["os_ctrl"] = float(os_match.group(2))
            out["endpoint"] = "OS"
        except (ValueError, TypeError):
            pass

    pfs_match = re.search(
        r'(?:median\s+)?PFS\s*[:.]?\s*([\d.]+)\s*(?:months?|mo|m)?\s*(?:vs\.?|versus|compared to|v\.?)\s*([\d.]+)\s*(?:months?|mo|m)?',
        text, re.IGNORECASE,
    )
    if pfs_match:
        try:
            out["pfs_exp"] = float(pfs_match.group(1))
            out["pfs_ctrl"] = float(pfs_match.group(2))
            if not out.get("endpoint"):
                out["endpoint"] = "PFS"
        except (ValueError, TypeError):
            pass

    orr_match = re.search(
        r'(?:ORR|overall\s*response\s*rate)\s*[:.]?\s*([\d.]+)\s*%\s*(?:vs\.?|versus|compared to|v\.?)\s*([\d.]+)\s*%?',
        text, re.IGNORECASE,
    )
    if orr_match:
        try:
            out["orr_exp"] = float(orr_match.group(1))
            out["orr_ctrl"] = float(orr_match.group(2))
        except (ValueError, TypeError):
            pass

    p_match = re.search(r'(?:p\s*[=<]\s*|P\s*[=<]\s*)([\d.]+)', text)
    if p_match:
        try:
            out["p_value"] = float(p_match.group(1))
        except (ValueError, TypeError):
            pass

    sig = out.get("p_value")
    if sig and sig <= 0.05:
        out["significant"] = True
    elif out.get("hr") and out.get("ci_hi") and out["ci_hi"] < 1.0:
        out["significant"] = True

    return out


def _enrich_trial(trial: dict) -> dict:
    enriched = dict(trial)
    kr = trial.get("key_result", "")
    parsed = parse_outcomes_from_text(kr)
    if parsed:
        enriched.update(parsed)
    enriched["_has_num"] = bool(parsed)
    return enriched


def _trial_short_label(trial: dict) -> str:
    name = trial.get("acronym") or trial.get("trial_name") or "?"
    name = str(name)[:40]
    return name


def render_forest_plot(trials: list[dict[str, Any]], height: int = 500) -> html.Div:
    plot_data: list[dict] = []
    for t in trials:
        enriched = _enrich_trial(t)
        hr = enriched.get("hr")
        if hr is None:
            continue
        ci_lo = enriched.get("ci_lo", hr * 0.75)
        ci_hi = enriched.get("ci_hi", hr * 1.35)
        plot_data.append({
            "trial": _trial_short_label(t),
            "hr": hr,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "endpoint": enriched.get("endpoint", "?"),
            "n": t.get("n") or t.get("n_patients", ""),
            "significant": enriched.get("significant", False),
            "year": t.get("year", ""),
        })

    if not plot_data:
        return html.Div("No hazard ratio data available for forest plot — outcomes are embedded in trial text descriptions.", className="text-muted p-3")

    df = pd.DataFrame(plot_data).sort_values("hr")
    df["error_lo"] = df["hr"] - df["ci_lo"]
    df["error_hi"] = df["ci_hi"] - df["hr"]
    df["color"] = df.apply(
        lambda r: "#27ae60" if r["significant"] and r["hr"] < 0.85 else "#e67e22" if r["hr"] < 1.0 else "#c0392b" if r["hr"] > 1.15 else "#7f8c8d",
        axis=1,
    )
    df["label"] = df.apply(
        lambda r: (f"<b>{r['trial']}</b> ({r.get('year','')})<br>"
                   f"HR={r['hr']:.2f} (95% CI {r['ci_lo']:.2f}-{r['ci_hi']:.2f})<br>"
                   f"Endpoint: {r['endpoint']}  N={r['n']}"),
        axis=1,
    )

    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["hr"]], y=[row["trial"]],
            mode="markers",
            marker=dict(size=12, color=row["color"], line=dict(width=1.5, color="white")),
            error_x=dict(type="data", symmetric=False,
                         array=[row["error_hi"]], arrayminus=[row["error_lo"]],
                         thickness=2, width=4, color=row["color"]),
            name=row["trial"],
            hovertemplate=row["label"],
            showlegend=False,
        ))

    fig.add_vline(x=1.0, line_dash="dash", line_color="#95a5a6", line_width=1.5,
                  annotation_text="HR=1 (null)", annotation_position="top")

    fig.update_layout(
        title="Hazard Ratio Forest Plot",
        xaxis_title="Hazard Ratio (log scale)",
        xaxis=dict(type="log", tickformat=".2f"),
        yaxis=dict(autorange="reversed"),
        height=min(height, max(250, len(df) * 28)),
        margin=dict(l=10, r=10, t=40, b=40),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=12, family="Segoe UI, system-ui, sans-serif"),
        hovermode="closest",
    )

    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": True, "toImageButtonOptions": {"format": "png"}}),
    ], className="forest-plot-container")


def render_survival_bars(trials: list[dict[str, Any]], height: int = 400) -> html.Div:
    rows = []
    for t in trials:
        enriched = _enrich_trial(t)
        name = _trial_short_label(t)
        if enriched.get("os_exp") and enriched.get("os_ctrl"):
            rows.append({"trial": name, "value": enriched["os_exp"], "group": "Experimental"})
            rows.append({"trial": name, "value": enriched["os_ctrl"], "group": "Control"})
        elif enriched.get("pfs_exp") and enriched.get("pfs_ctrl"):
            rows.append({"trial": name, "value": enriched["pfs_exp"], "group": "Experimental"})
            rows.append({"trial": name, "value": enriched["pfs_ctrl"], "group": "Control"})

    if len(rows) < 2:
        return html.Div("No survival comparison data available.", className="text-muted p-3")

    df = pd.DataFrame(rows)
    fig = px.bar(
        df, x="trial", y="value", color="group", barmode="group",
        color_discrete_map={"Experimental": "#1a5276", "Control": "#95a5a6"},
        title="Median Survival Comparison (months)",
        labels={"value": "Months", "trial": "", "group": ""},
        height=min(height, max(250, len(df) // 2 * 40)),
    )
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=11, family="Segoe UI, system-ui, sans-serif"),
        legend=dict(orientation="h", yanchor="top", y=-0.15),
        margin=dict(l=10, r=10, t=40, b=40),
    )
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": True, "toImageButtonOptions": {"format": "png"}}),
    ], className="mb-3")


def render_phase_donut(trials: list[dict[str, Any]], height: int = 320) -> html.Div:
    counts: dict[str, int] = {}
    for t in trials:
        phase = str(t.get("phase", "")).strip().upper()
        if not phase or phase == "NONE":
            phase = "Unknown"
        elif "I" in phase and "II" in phase and "III" in phase:
            phase = "I-III"
        elif "III" in phase:
            phase = "Phase III"
        elif "II" in phase:
            phase = "Phase II"
        elif "I" in phase:
            phase = "Phase I"
        else:
            phase = "Unknown"
        counts[phase] = counts.get(phase, 0) + 1

    if not counts:
        return html.Div("", className="p-3")

    colors = {"Phase III": "#1a5276", "Phase II": "#2c7ba0", "Phase I": "#7fb3d5", "I-III": "#e67e22", "Unknown": "#bdc3c7"}
    labels = list(counts.keys())
    values = list(counts.values())
    color_list = [colors.get(l, "#bdc3c7") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=color_list),
        textinfo="label+value",
        textfont=dict(size=10),
    ))
    fig.update_layout(
        title="Evidence by Phase",
        height=height, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white",
        font=dict(size=11, family="Segoe UI, system-ui, sans-serif"),
        showlegend=False,
    )
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])


def render_trial_timeline(trials: list[dict[str, Any]], height: int = 350) -> html.Div:
    rows = []
    for t in trials:
        year = t.get("year", "")
        if not year:
            continue
        try:
            y = int(str(year).strip()[:4])
        except ValueError:
            continue
        phase = str(t.get("phase", "")).strip()
        rows.append({
            "trial": _trial_short_label(t),
            "year": y,
            "phase": phase if phase else "Unknown",
            "n": t.get("n") or t.get("n_patients", 10),
        })

    if not rows:
        return html.Div("", className="p-3")

    df = pd.DataFrame(rows)
    fig = px.scatter(
        df, x="year", y=[0] * len(df),
        color="phase", size="n",
        hover_name="trial",
        title="Trial Publication Timeline",
        labels={"year": "Year", "phase": "Phase"},
        height=height,
    )
    fig.update_traces(marker=dict(opacity=0.8, line=dict(width=0.5, color="white")))
    fig.update_yaxes(visible=False, showticklabels=False)
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=11, family="Segoe UI, system-ui, sans-serif"),
        margin=dict(l=10, r=10, t=40, b=40),
        legend=dict(orientation="h", yanchor="top", y=-0.15),
    )
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": True, "toImageButtonOptions": {"format": "png"}}),
    ])


def render_orr_waterfall(trials: list[dict[str, Any]], height: int = 400) -> html.Div:
    rows = []
    for t in trials:
        enriched = _enrich_trial(t)
        rr = enriched.get("orr_exp")
        if rr is None:
            td = t.get("trial_data", {})
            if isinstance(td, dict) and td.get("orr_experimental"):
                try:
                    rr = float(td["orr_experimental"])
                except (ValueError, TypeError):
                    pass
        if rr is not None:
            rows.append({"trial": _trial_short_label(t), "ORR (%)": rr})

    if not rows:
        return html.Div("", className="p-3")

    df = pd.DataFrame(rows).sort_values("ORR (%)", ascending=False).head(20)
    colors = ["#1a5276"] * len(df)

    fig = go.Figure(go.Bar(
        x=df["ORR (%)"], y=df["trial"], orientation="h",
        marker=dict(color=colors),
        text=df["ORR (%)"].apply(lambda x: f"{x:.0f}%"),
        textposition="outside",
    ))
    fig.update_layout(
        title="Objective Response Rate (Top 20)",
        xaxis_title="ORR (%)",
        height=min(height, max(250, len(df) * 22)),
        margin=dict(l=10, r=50, t=40, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=11, family="Segoe UI, system-ui, sans-serif"),
    )
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": True, "toImageButtonOptions": {"format": "png"}}),
    ])


def render_trial_card(trial: dict[str, Any], pubmed_data: Optional[dict] = None, index: int = 0) -> dbc.Card:
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

    badge_row = []
    if year:
        badge_row.append(dbc.Badge(str(year), color="dark", className="me-1 rounded-pill"))
    if phase:
        badge_row.append(dbc.Badge(f"Phase {phase}", color="info", className="me-1 rounded-pill"))
    if n_val:
        badge_row.append(dbc.Badge(f"N={n_val}", color="secondary", className="me-1 rounded-pill"))

    enriched = _enrich_trial(trial)
    if enriched.get("significant"):
        badge_row.append(dbc.Badge("Significant", color="success", className="me-1 rounded-pill"))
    if enriched.get("hr"):
        endpoint_label = enriched.get("endpoint", "HR")
        ci_text = ""
        if enriched.get("ci_lo") and enriched.get("ci_hi"):
            ci_text = f" ({enriched['ci_lo']:.2f}-{enriched['ci_hi']:.2f})"
        badge_row.append(dbc.Badge(f"{endpoint_label} {enriched['hr']:.2f}{ci_text}", color="primary", className="me-1 rounded-pill"))

    if pubmed_data and pubmed_data.get("pmid"):
        badge_row.append(html.A(
            dbc.Badge(f"PMID:{pubmed_data['pmid']}", color="success", className="me-1 rounded-pill"),
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
        html.H5(acronym, className="trial-card-title mb-1"),
        html.Div(badge_row, className="mb-2"),
        *body_items,
    ]
    if abstract_section:
        children.append(abstract_section)

    return dbc.Card(dbc.CardBody(children), className="trial-card shadow-sm mb-3",
                    style={"borderLeft": "4px solid #2c7ba0"})


def render_trial_outcomes_comparison(trial_data: dict[str, Any]) -> html.Div:
    if not trial_data or not isinstance(trial_data, dict):
        return html.Div()

    trial_name = trial_data.get("trial_name", "")
    phase = trial_data.get("phase", "")
    n_patients = trial_data.get("n_patients", "")

    header = []
    if trial_name:
        header.append(html.H6(str(trial_name), className="mb-1"))
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

        if not exp_val and not ctrl_val and not hr_val:
            continue

        cols = []
        if exp_val:
            cols.append(dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("Experimental", className="text-muted small text-uppercase"),
                html.Div(str(exp_val), className="fw-bold h5 mb-0"),
            ]), className="border-primary"), width=4))
        if ctrl_val:
            cols.append(dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("Control", className="text-muted small text-uppercase"),
                html.Div(str(ctrl_val), className="fw-bold h5 mb-0"),
            ]), className="border-secondary"), width=4))
        if hr_val:
            hr_f = _parse_hr(hr_val)
            ci_str = ""
            if ci_key:
                ci_val = trial_data.get(ci_key, "")
                if ci_val:
                    ci_str = f" ({ci_val})"
            hr_color = "#27ae60" if (hr_f and hr_f < 0.9) else "#7f8c8d"
            cols.append(dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("HR" + ci_str, className="text-muted small text-uppercase"),
                html.Div(str(hr_val), className="fw-bold h5 mb-0", style={"color": hr_color}),
            ]), className="border-info"), width=4))

        if cols:
            outcomes.append(html.Div([
                html.Div(label, className="fw-bold small mt-2 mb-1"),
                dbc.Row(cols, className="g-2"),
            ]))

    if not outcomes:
        return html.Div()

    return html.Div([*header, *outcomes], className="trial-outcomes-comparison mb-3")


def render_pubmed_search_widget() -> html.Div:
    return html.Div([
        html.H5("Live PubMed Search", className="mb-2"),
        dbc.InputGroup([
            dbc.Input(id="pubmed-search-input", type="text",
                      placeholder="Search PubMed for clinical trials...",
                      className="form-control"),
            dbc.Button("Search", id="pubmed-search-btn", color="primary", n_clicks=0),
        ], className="mb-3"),
        html.Div(id="pubmed-search-results"),
        html.Div(id="pubmed-search-status"),
    ], className="pubmed-search-widget mb-4 p-3 bg-light rounded")

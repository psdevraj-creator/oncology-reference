"""
Vibrant Plotly chart generators for handbook sections.
All charts use a custom vibrant healthcare template with animated transitions.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

VIBRANT_TEMPLATE = go.layout.Template()
VIBRANT_TEMPLATE.layout.update(
    font_family="'Segoe UI', system-ui, -apple-system, sans-serif",
    font_color="#1e293b",
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    colorway=[
        "#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6",
        "#8b5cf6", "#ef4444", "#14b8a6", "#f97316", "#06b6d4",
    ],
    xaxis=dict(showgrid=True, gridcolor="#e2e8f0", zeroline=False, linecolor="#cbd5e1"),
    yaxis=dict(showgrid=True, gridcolor="#e2e8f0", zeroline=False, linecolor="#cbd5e1"),
    hoverlabel=dict(bgcolor="#1e293b", font_size=13, font_family="'Segoe UI', sans-serif"),
)

CHART_CONFIG = {
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "sendDataToCloud"],
    "displaylogo": False,
    "responsive": True,
    "toImageButtonOptions": {"format": "png", "filename": "chart"},
}


def _responsive_layout(fig: go.Figure, title: str = "", height: int = 380) -> go.Figure:
    fig.update_layout(
        template=VIBRANT_TEMPLATE,
        title=dict(text=title, font=dict(size=16, color="#1e293b"), x=0.01),
        margin=dict(l=20, r=20, t=40 if title else 20, b=20),
        height=height,
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def epidemiology_chart(data: dict) -> go.Figure | None:
    """Incidence/mortality grouped bar chart."""
    labels = data.get("labels", [])
    incidence = data.get("incidence", [])
    mortality = data.get("mortality", [])
    if not labels:
        return None
    fig = go.Figure([
        go.Bar(name="Incidence", x=labels, y=incidence, marker_color="#6366f1",
               hovertemplate="%{y:,} cases<extra>Incidence</extra>"),
        go.Bar(name="Mortality", x=labels, y=mortality, marker_color="#ef4444",
               hovertemplate="%{y:,} deaths<extra>Mortality</extra>"),
    ])
    fig.update_layout(barmode="group")
    return _responsive_layout(fig, title="Epidemiology Overview")


def incidence_bar(data: dict) -> go.Figure | None:
    """Single-metric incidence bar chart."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    if not labels:
        return None
    fig = px.bar(x=labels, y=values, labels={"x": "", "y": data.get("y_label", "Cases")},
                 color_discrete_sequence=["#6366f1"])
    fig.update_traces(hovertemplate="%{y:,}<extra></extra>")
    return _responsive_layout(fig, title=data.get("title", ""))


def subtypes_sunburst(data: dict) -> go.Figure | None:
    """Sunburst chart for cancer subtypes."""
    labels = data.get("labels", [])
    parents = data.get("parents", [])
    values = data.get("values", [])
    if not labels:
        return None
    fig = px.sunburst(
        names=labels, parents=parents, values=values,
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.update_traces(textinfo="label+percent entry", hovertemplate="%{label}<br>%{value}%<extra></extra>")
    return _responsive_layout(fig, title="Subtype Distribution", height=420)


def risk_waterfall(data: dict) -> go.Figure | None:
    """Risk factor waterfall chart showing attributable risk."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    if not labels:
        return None
    colors = ["#10b981" if v > 0 else "#ef4444" for v in values]
    fig = go.Figure(go.Waterfall(
        name="", orientation="h", measure=["relative"] * len(labels),
        y=labels, x=values, text=[f"{v:+.1f}%" for v in values],
        connector=dict(mode="between", line=dict(color="#cbd5e1", width=1)),
        decreasing=dict(marker=dict(color="#ef4444")),
        increasing=dict(marker=dict(color="#10b981")),
        totals=dict(marker=dict(color="#6366f1")),
    ))
    return _responsive_layout(fig, title="Risk Factor Impact", height=380)


def survival_bars(data: dict) -> go.Figure | None:
    """Grouped bar chart for survival metrics per trial/regimen."""
    labels = data.get("labels", [])
    os_vals = data.get("os", [])
    pfs_vals = data.get("pfs", [])
    if not labels:
        return None
    fig = go.Figure()
    if os_vals:
        fig.add_trace(go.Bar(name="Overall Survival (mo)", x=labels, y=os_vals,
                              marker_color="#6366f1"))
    if pfs_vals:
        fig.add_trace(go.Bar(name="PFS (mo)", x=labels, y=pfs_vals,
                              marker_color="#f59e0b"))
    fig.update_layout(barmode="group")
    return _responsive_layout(fig, title="Survival Comparison")


def complication_bars(data: dict) -> go.Figure | None:
    """Horizontal bar chart for complication incidence."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    severities = data.get("severities", [])
    if not labels:
        return None
    color_map = {"mild": "#10b981", "moderate": "#f59e0b", "severe": "#ef4444",
                 "life-threatening": "#7c3aed"}
    colors = [color_map.get(s, "#3b82f6") for s in severities]
    fig = go.Figure(go.Bar(
        y=labels, x=values, orientation="h",
        marker_color=colors,
        text=[f"{v}%" for v in values], textposition="auto",
        hovertemplate="%{y}: %{x}%<extra></extra>",
    ))
    fig.update_layout(xaxis_title="Incidence (%)")
    return _responsive_layout(fig, title="Complication Rates", height=380)


def prognosis_bars(data: dict) -> go.Figure | None:
    """5-year OS bar chart by stage."""
    stages = data.get("stages", [])
    os5 = data.get("os_5yr", [])
    if not stages:
        return None
    colors = ["#10b981", "#f59e0b", "#f97316", "#ef4444", "#7c3aed"]
    if len(stages) > len(colors):
        colors = colors * (len(stages) // len(colors) + 1)
    colors = colors[:len(stages)]
    fig = go.Figure(go.Bar(
        x=stages, y=os5, marker_color=colors,
        text=[f"{v}%" for v in os5], textposition="outside",
        hovertemplate="Stage %{x}: %{y}% 5-yr OS<extra></extra>",
    ))
    fig.update_layout(yaxis_title="5-Year Overall Survival (%)", yaxis_range=[0, 105])
    return _responsive_layout(fig, title="5-Year Survival by Stage")


def phase_donut(data: dict) -> go.Figure | None:
    """Trial phase distribution donut chart."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    if not labels:
        return None
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker_colors=["#6366f1", "#ec4899", "#f59e0b", "#10b981"],
        textinfo="label+percent", textfont_size=12,
        hovertemplate="Phase %{label}: %{value} trials<extra></extra>",
    ))
    return _responsive_layout(fig, title="Trial Phase Distribution", height=340)


def trial_timeline(data: dict) -> go.Figure | None:
    """Publication timeline scatter chart."""
    trials = data.get("labels", [])
    years = data.get("years", [])
    n_vals = data.get("n_patients", [])
    if not trials:
        return None
    sizes = [(max(n, 100) ** 0.4) * 5 for n in n_vals] if n_vals else [12] * len(trials)
    fig = go.Figure(go.Scatter(
        x=years, y=list(range(len(trials))), mode="markers+text",
        text=trials, textposition="top center", textfont=dict(size=10),
        marker=dict(size=sizes, color="#6366f1", opacity=0.8,
                     line=dict(color="#1e293b", width=1)),
        hovertemplate="%{text}<br>Year: %{x}<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                      xaxis_title="Year")
    return _responsive_layout(fig, title="Trial Publication Timeline", height=300)


def trial_bubble(data: dict) -> go.Figure | None:
    """Bubble chart: trial sample size vs effect size."""
    trials = data.get("labels", [])
    n_vals = data.get("n_patients", [])
    effect = data.get("effect_sizes", [])
    if not trials:
        return None
    fig = go.Figure(go.Scatter(
        x=n_vals, y=effect, mode="markers+text",
        text=trials, textposition="top center", textfont=dict(size=9),
        marker=dict(size=[max(n, 50) ** 0.5 for n in n_vals] if n_vals else 15,
                     color="#ec4899", opacity=0.75,
                     line=dict(color="#1e293b", width=1)),
        hovertemplate="%{text}<br>N=%{x}<br>HR=%{y}<extra></extra>",
    ))
    fig.update_layout(xaxis_title="Sample Size", yaxis_title="Hazard Ratio",
                      yaxis=dict(type="log" if any(e <= 0.5 for e in effect) else "linear"))
    return _responsive_layout(fig, title="Trial Size vs Effect", height=340)


def orr_waterfall(data: dict) -> go.Figure | None:
    """ORR waterfall bar chart (top 20)."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    if not labels:
        return None
    colors = ["#10b981" if v >= 50 else "#f59e0b" if v >= 20 else "#ef4444" for v in values]
    fig = go.Figure(go.Bar(
        y=labels[:20], x=values[:20], orientation="h", marker_color=colors[:20],
        text=[f"{v}%" for v in values[:20]], textposition="auto",
    ))
    fig.update_layout(xaxis_title="Objective Response Rate (%)")
    return _responsive_layout(fig, title="Objective Response Rates", height=400)


def forest_plot(data: dict) -> go.Figure | None:
    """High-quality forest plot for hazard ratios."""
    trials = data.get("labels", [])
    hrs = data.get("hrs", [])
    ci_low = data.get("ci_low", [])
    ci_high = data.get("ci_high", [])
    if not trials:
        return None
    fig = go.Figure()
    colors = ["#10b981" if hr < 1 else "#ef4444" for hr in hrs]
    fig.add_trace(go.Scatter(
        x=hrs, y=trials, mode="markers",
        marker=dict(color=colors, size=10, line=dict(color="#1e293b", width=1)),
        error_x=dict(
            type="data", symmetric=False,
            arrayminus=[h - c for h, c in zip(hrs, ci_low)],
            array=[c - h for h, c in zip(hrs, ci_high)],
            color="#64748b", thickness=2, width=6,
        ),
        hovertemplate="%{y}<br>HR: %{x:.2f} (95% CI)<extra></extra>",
    ))
    fig.add_vline(x=1, line_dash="dash", line_color="#64748b", line_width=1)
    fig.update_layout(xaxis_title="Hazard Ratio (log scale)", xaxis_type="log",
                      margin=dict(l=20, r=20, t=40, b=20))
    return _responsive_layout(fig, title="Forest Plot", height=350)

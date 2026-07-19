"""
Vibrant handbook section renderers using dmc, Plotly, Cytoscape, and ag-grid.
Each renderer takes (value) — the raw handbook value — and returns a list of Dash components.
All renderers fall back gracefully if enriched cache is missing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import dcc, html

from app.components.viz.charts import (
    complication_bars,
    epidemiology_chart,
    incidence_bar,
    prognosis_bars,
    subtypes_sunburst,
)
from app.components.viz.dashboards import (
    alert_gradient,
    animated_counter,
    gradient_hero_card,
    progress_ring,
    timeline_component,
    vibrantsym_card,
)
from app.components.viz.pathways import management_flowchart

REWRITTEN_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "rewritten" / "sections"
if not REWRITTEN_DIR.exists():
    import sys as _sys
    if getattr(_sys, "frozen", False):
        REWRITTEN_DIR = Path(_sys._MEIPASS) / "data" / "rewritten" / "sections"
    elif not REWRITTEN_DIR.exists():
        pass


def _load_enriched(site_id: str | None, section: str) -> dict | None:
    if not site_id:
        return None
    path = REWRITTEN_DIR / site_id / f"{section}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


_TITLE_KEYS = ["name", "title", "factor", "complication", "situation", "procedure",
               "test", "test_name", "intent", "regimen_name", "pathway", "category"]
_BODY_KEYS = ["detail", "description", "content", "body", "text", "notes",
              "management", "key_message", "evidence", "summary", "rationale",
              "indications", "recommendation", "overview"]


def _dict_to_card(item: dict, icon: str = "bi-file-medical",
                  color: str = "#6366f1", extra_badges: list | None = None) -> dmc.Paper:
    """Universal dict renderer: detects title/body from any key set, never dumps raw JSON."""
    title = ""
    body_parts = []

    # Find title from known keys
    for k in _TITLE_KEYS:
        if k in item and item[k]:
            title = str(item[k])
            break
    if not title:
        # Use first short string key as title
        for k, v in item.items():
            if isinstance(v, str) and len(v) < 100:
                title = v
                break

    # Build body from remaining keys
    for k, v in item.items():
        if k == title or (isinstance(v, str) and v == title):
            continue
        if isinstance(v, str) and v.strip():
            if k in _BODY_KEYS or len(v) > 50:
                body_parts.append(v)
            else:
                body_parts.append(f"**{k.replace('_', ' ').title()}**: {v}")
        elif isinstance(v, (list, dict)):
            body_parts.append(str(v))

    # Extra badges (type, strength, frequency, severity)
    extras = list(extra_badges or [])
    for k in ["type", "strength", "frequency", "severity", "category"]:
        if k in item and item[k]:
            c = color.replace("#", "") if color else "blue"
            extras.append(dmc.Badge(str(item[k]), color=c if isinstance(item[k], str) else "gray",
                                     variant="light", size="sm"))

    return vibrantsym_card(
        title=title or "Details",
        body="\n\n".join(body_parts) if body_parts else json.dumps(item, ensure_ascii=False, indent=1),
        icon=icon,
        color=color,
        extra=extras if extras else None,
    )


# ── Epidemiology ──────────────────────────────────────────────────────

def render_epidemiology(value, site_id: str = "") -> list:
    components = [html.H3("Epidemiology", className="section-heading")]
    if not isinstance(value, dict):
        return components + [dcc.Markdown(str(value), className="section-text")]

    stats = []
    for key, label, icon, color in [
        ("incidence", "Annual Incidence", "bi-people-fill", "#6366f1"),
        ("mortality", "Annual Mortality", "bi-graph-down-arrow", "#ef4444"),
        ("trends", "Trend & Projections", "bi-graph-up", "#f59e0b"),
    ]:
        val = value.get(key, "")
        if isinstance(val, str) and val.strip():
            stats.append(animated_counter(label, val, icon, color))

    if stats:
        components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2, "md": 3}, spacing="md", children=stats))

    for key, heading, icon in [
        ("incidence", "Incidence", "bi-bar-chart"),
        ("mortality", "Mortality", "bi-graph-down"),
        ("trends", "Trends", "bi-activity"),
        ("demographics", "Demographics", "bi-globe2"),
    ]:
        val = value.get(key, "")
        if isinstance(val, str) and val.strip():
            components.append(
                dmc.Blockquote(
                    dcc.Markdown(val, className="section-text"),
                    cite=heading, icon=html.I(className=f"bi {icon}"),
                    className="definition-blockquote",
                )
            )
    return components


# ── Subtypes ──────────────────────────────────────────────────────────

def render_subtypes(value, site_id: str = "") -> list:
    components = [html.H3("Subtypes", className="section-heading")]
    if not isinstance(value, list) or not value:
        return components

    # Try enriched cache for sunburst data
    if site_id:
        enriched = _load_enriched(site_id, "subtypes")
        if enriched and enriched.get("sunburst_data"):
            sd = enriched["sunburst_data"]
            try:
                fig = subtypes_sunburst({"labels": sd["labels"], "parents": sd["parents"], "values": sd["values"]})
                if fig:
                    components.append(dcc.Graph(figure=fig, config={"displayModeBar": False}, className="mb-4"))
            except Exception:
                pass

    # Subtype cards (always render, no chart dependency)
    cards = []
    colors = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6"]
    for i, s in enumerate(value):
        if isinstance(s, dict):
            cards.append(vibrantsym_card(
                title=s.get("name", f"Subtype {i+1}"),
                body=s.get("description", "") or s.get("detail", ""),
                icon="bi-clipboard2-pulse",
                color=colors[i % len(colors)],
                extra=[dmc.Badge(s.get("frequency", ""), color=colors[i % len(colors)].replace("#", ""), variant="light")]
                if s.get("frequency") else None,
            ))
    if cards:
        components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
    return components


# ── Molecular Pathogenesis ────────────────────────────────────────────

def render_molecular_pathogenesis(value: str, site_id: str = "") -> list:
    components = [html.H3("Molecular Pathogenesis", className="section-heading")]
    if not isinstance(value, str) or not value.strip():
        return components

    if site_id:
        enriched = _load_enriched(site_id, "molecular_pathogenesis")
        if enriched and enriched.get("sections"):
            net_enriched = enriched.get("network", {})
            if net_enriched.get("nodes"):
                from app.components.viz.pathways import molecular_network
                net = molecular_network(net_enriched)
                if net:
                    components.append(
                        dmc.Paper(dcc.Loading(net), shadow="sm", radius="md", p="sm", className="mb-4",
                                  style={"overflow": "hidden"})
                    )
            for sec in enriched["sections"]:
                components.append(
                    dmc.Blockquote(
                        dcc.Markdown(sec["content"], className="section-text"),
                        cite=sec.get("heading", "Pathway"),
                        className="definition-blockquote",
                    )
                )
            return components

    paragraphs = [p.strip() for p in value.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        components.append(
            dmc.Paper(
                dcc.Markdown(value, className="section-text"),
                shadow="xs", radius="md", p="lg", withBorder=True,
                className="definition-paper",
            )
        )
        return components

    items = []
    pathway_keywords = ["pathway", "signaling", "receptor", "kinase", "mutation",
                        "DNA repair", "cell cycle", "apoptosis", "invasion", "immune"]
    for p in paragraphs:
        heading = "Pathway"
        for kw in pathway_keywords:
            if kw.lower() in p.lower():
                heading = kw.title()
                break
        items.append(
            dmc.AccordionItem(
                value=heading.lower().replace(" ", "-"),
                children=[
                    dmc.AccordionControl(heading),
                    dmc.AccordionPanel(dcc.Markdown(p, className="section-text")),
                ],
            )
        )

    components.append(
        dmc.Accordion(chevronPosition="right", variant="contained", radius="md",
                       children=items, className="mb-4")
    )
    return components


# ── Risk Factors ──────────────────────────────────────────────────────

def render_risk_factors(value: list, site_id: str = "") -> list:
    components = [html.H3("Risk Factors", className="section-heading")]
    if not isinstance(value, list) or not value:
        return components

    type_colors = {"Genetic": "#ef4444", "Lifestyle": "#f59e0b", "Environmental": "#3b82f6",
                   "Demographic": "#6366f1", "Medical": "#ec4899", "Hormonal": "#8b5cf6"}
    cards = []
    for rf in value:
        if isinstance(rf, dict):
            rtype = rf.get("type", "")
            color = type_colors.get(rtype, "#64748b")
            extra = []
            if rf.get("strength"):
                extra.append(dmc.Badge(rf["strength"], color=color.replace("#", ""), variant="filled", size="sm"))
            if rf.get("type"):
                extra.append(dmc.Badge(rf["type"], color="gray", variant="outline", size="sm"))
            cards.append(vibrantsym_card(
                title=rf.get("factor", ""),
                body=rf.get("detail", ""),
                icon="bi-shield-exclamation",
                color=color,
                extra=extra if extra else None,
            ))

    if cards:
        components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
    return components


# ── Protective Factors ────────────────────────────────────────────────

def render_protective_factors(value: list, site_id: str = "") -> list:
    components = [html.H3("Protective Factors", className="section-heading")]
    if not isinstance(value, list) or not value:
        return components
    cards = []
    for pf in value:
        text = pf if isinstance(pf, str) else pf.get("detail", str(pf))
        cards.append(vibrantsym_card(
            title=pf.get("factor", "") if isinstance(pf, dict) else "",
            body=text,
            icon="bi-shield-check",
            color="#10b981",
        ))
    if cards:
        components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
    return components


# ── Clinical Features ─────────────────────────────────────────────────

def render_clinical_features(value, site_id: str = "") -> list:
    components = [html.H3("Clinical Features", className="section-heading")]
    if not value:
        return components

    if isinstance(value, dict):
        for sub_key, sub_val in value.items():
            label = sub_key.replace("_", " ").title()
            if isinstance(sub_val, list):
                cards = []
                for item in sub_val:
                    if isinstance(item, dict):
                        name = item.get("name", "")
                        detail = item.get("detail", "")
                        freq = item.get("frequency", "")
                        alarm = item.get("alarm", False)
                        color = "#ef4444" if alarm else "#f59e0b"
                        cards.append(vibrantsym_card(
                            title=name, body=detail, icon="bi-exclamation-diamond-fill" if alarm else "bi-clipboard-pulse",
                            color=color,
                            extra=[dmc.Badge(freq, color=color.replace("#", ""), variant="light")] if freq else None,
                        ))
                if cards:
                    components.append(html.H4(label, className="subsection-heading"))
                    components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
            elif isinstance(sub_val, str) and sub_val.strip():
                components.append(dmc.Blockquote(
                    dcc.Markdown(sub_val, className="section-text"),
                    cite=label, className="definition-blockquote",
                ))
    elif isinstance(value, str):
        components.append(dmc.Paper(
            dcc.Markdown(value, className="section-text"),
            shadow="xs", radius="md", p="lg", withBorder=True, className="definition-paper",
        ))
    elif isinstance(value, list):
        cards = []
        for item in value:
            if isinstance(item, dict):
                cards.append(vibrantsym_card(
                    title=item.get("name", ""), body=item.get("detail", ""),
                    icon="bi-clipboard-pulse", color="#f59e0b",
                ))
        if cards:
            components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
    return components


# ── Red Flags ────────────────────────────────────────────────────────

def render_red_flags(value: list, site_id: str = "") -> list:
    components = [html.H3("Red Flags", className="section-heading")]
    if not isinstance(value, list) or not value:
        return components
    alerts = []
    for rf in value:
        text = rf if isinstance(rf, str) else rf.get("detail", str(rf))
        title = "Red Flag" if isinstance(rf, str) else rf.get("name", "Red Flag")
        alerts.append(alert_gradient(title=title, body=text, color="#ef4444",
                                     icon="bi-exclamation-triangle-fill"))
    components.extend(alerts)
    return components


# ── Investigations ────────────────────────────────────────────────────

def render_investigations(value, site_id: str = "") -> list:
    components = [html.H3("Investigations", className="section-heading")]
    if not value:
        return components

    timeline_items = []
    if isinstance(value, dict):
        for key, sub_val in value.items():
            label = key.replace("_", " ").title()
            if isinstance(sub_val, list):
                cards = []
                for item in sub_val:
                    if isinstance(item, dict):
                        text = item.get("rationale", "") or item.get("text", "")
                        cards.append(vibrantsym_card(
                            title=item.get("test", item.get("name", key)),
                            body=text, icon="bi-search", color="#7c3aed",
                        ))
                if cards:
                    components.append(html.H4(label, className="subsection-heading"))
                    components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
            elif isinstance(sub_val, str) and sub_val.strip():
                timeline_items.append({"title": label, "body": sub_val, "icon": "bi-search"})
    elif isinstance(value, list):
        cards = []
        for item in value:
            if isinstance(item, dict):
                cards.append(vibrantsym_card(
                    title=item.get("test", item.get("name", "")),
                    body=item.get("rationale", item.get("detail", "")),
                    icon="bi-search", color="#7c3aed",
                ))
        if cards:
            components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
    elif isinstance(value, str):
        components.append(dmc.Paper(
            dcc.Markdown(value, className="section-text"),
            shadow="xs", radius="md", p="lg", withBorder=True, className="definition-paper",
        ))
    return components


# ── Surgery ───────────────────────────────────────────────────────────

def render_surgery(value: dict, site_id: str = "") -> list:
    components = [html.H3("Surgery", className="section-heading")]
    if not isinstance(value, dict):
        return components

    if isinstance(value.get("role"), str):
        components.append(dmc.Blockquote(
            dcc.Markdown(value["role"], className="section-text"),
            cite="Surgical Role", icon=html.I(className="bi bi-scissors"),
            className="definition-blockquote",
        ))

    if isinstance(value.get("principles"), (str, list)):
        principles = value["principles"]
        if isinstance(principles, str):
            principles = [principles]
        for p in principles:
            if isinstance(p, str) and p.strip():
                components.append(vibrantsym_card(
                    title="", body=p, icon="bi-check-circle", color="#6366f1",
                ))

    if isinstance(value.get("procedures"), list):
        cards = []
        for proc in value["procedures"]:
            if isinstance(proc, dict):
                cards.append(vibrantsym_card(
                    title=proc.get("name", proc.get("procedure", "")),
                    body=proc.get("description", proc.get("detail", proc.get("indications", ""))),
                    icon="bi-scissors", color="#ec4899",
                ))
        if cards:
            components.append(html.H4("Procedures", className="subsection-heading"))
            components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))

    return components


# ── Complications ─────────────────────────────────────────────────────

def render_complications(value: dict, site_id: str = "") -> list:
    components = [html.H3("Complications", className="section-heading")]
    if not isinstance(value, dict):
        return components

    for key, label, color in [
        ("disease_related", "Disease-Related", "#ef4444"),
        ("treatment_related", "Treatment-Related", "#f59e0b"),
    ]:
        items = value.get(key, [])
        if isinstance(items, list) and items:
            components.append(html.H4(label, className="subsection-heading"))
            cards = []
            for item in items:
                if isinstance(item, dict):
                    cards.append(_dict_to_card(item, icon="bi-exclamation-circle", color=color))
                elif isinstance(item, str):
                    cards.append(vibrantsym_card(
                        title="", body=item, icon="bi-exclamation-circle", color=color,
                    ))
            if cards:
                components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))

    return components


# ── Supportive Care ───────────────────────────────────────────────────

def render_supportive_care(value: dict, site_id: str = "") -> list:
    components = [html.H3("Supportive Care", className="section-heading")]
    if not isinstance(value, dict):
        return components

    items = []
    colors = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ef4444", "#14b8a6"]
    for i, (key, sub_val) in enumerate(value.items()):
        if key == "overview" and isinstance(sub_val, str):
            components.append(dmc.Paper(
                dcc.Markdown(sub_val, className="section-text"),
                shadow="xs", radius="md", p="md", withBorder=True, className="definition-paper",
            ))
        elif isinstance(sub_val, str) and sub_val.strip():
            items.append(dmc.AccordionItem(
                value=key, children=[
                    dmc.AccordionControl(key.replace("_", " ").title()),
                    dmc.AccordionPanel(dcc.Markdown(sub_val, className="section-text")),
                ],
            ))
        elif isinstance(sub_val, dict):
            body_parts = []
            for sk, sv in sub_val.items():
                if isinstance(sv, str) and sv.strip():
                    body_parts.append(f"**{sk.replace('_', ' ').title()}**: {sv}")
            if body_parts:
                items.append(dmc.AccordionItem(
                    value=key, children=[
                        dmc.AccordionControl(key.replace("_", " ").title()),
                        dmc.AccordionPanel(dcc.Markdown("\n\n".join(body_parts), className="section-text")),
                    ],
                ))

    if items:
        components.append(dmc.Accordion(chevronPosition="right", variant="contained", radius="md",
                                        children=items, className="mb-4"))
    return components


# ── Follow-Up ─────────────────────────────────────────────────────────

def render_follow_up(value: dict, site_id: str = "") -> list:
    components = [html.H3("Follow-Up", className="section-heading")]
    if not isinstance(value, dict):
        return components
    timeline_items = []
    for key, sub_val in value.items():
        label = key.replace("_", " ").title()
        if isinstance(sub_val, str) and sub_val.strip():
            timeline_items.append({"title": label, "body": sub_val, "icon": "bi-calendar-check"})
        elif isinstance(sub_val, list):
            for item in sub_val:
                if isinstance(item, str):
                    timeline_items.append({"title": label, "body": item, "icon": "bi-calendar2-check"})
    if timeline_items:
        components.append(timeline_component(timeline_items, color="#10b981"))
    return components


# ── Clinical Pearls ───────────────────────────────────────────────────

def render_clinical_pearls(value: list, site_id: str = "") -> list:
    components = [html.H3("Clinical Pearls", className="section-heading")]
    if not isinstance(value, list) or not value:
        return components
    cards = []
    for i, pearl in enumerate(value):
        text = pearl if isinstance(pearl, str) else pearl.get("text", str(pearl))
        cards.append(vibrantsym_card(
            title=f"Pearl {i + 1}", body=text,
            icon="bi-lightbulb", color="#f59e0b",
        ))
    if cards:
        components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
    return components


# ── Special Situations ────────────────────────────────────────────────

def render_special_situations(value: list, site_id: str = "") -> list:
    components = [html.H3("Special Situations", className="section-heading")]
    if not isinstance(value, list) or not value:
        return components
    cards = []
    for item in value:
        if isinstance(item, dict):
            cards.append(_dict_to_card(item, icon="bi-exclamation-diamond", color="#ec4899"))
        elif isinstance(item, str):
            cards.append(vibrantsym_card(
                title="", body=item, icon="bi-exclamation-diamond", color="#ec4899",
            ))
    if cards:
        components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
    return components


# ── Guidelines & Resources ────────────────────────────────────────────

def render_guidelines_resources(value: list, site_id: str = "") -> list:
    components = [html.H3("Guidelines & Resources", className="section-heading")]
    if not isinstance(value, list) or not value:
        return components
    cards = []
    for item in value:
        if isinstance(item, dict):
            org = item.get("organisation", item.get("org", ""))
            extra = [dmc.Badge(org, color="indigo", variant="light")] if org else None
            cards.append(_dict_to_card(item, icon="bi-journal-check", color="#6366f1",
                                       extra_badges=extra))
    if cards:
        components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))
    return components


# ── Management Principles ─────────────────────────────────────────────

def render_management_principles(value: dict, site_id: str = "") -> list:
    components = [html.H3("Management Principles", className="section-heading")]
    if not isinstance(value, dict):
        return components

    if isinstance(value.get("overview"), str):
        components.append(dmc.Paper(
            dcc.Markdown(value["overview"], className="section-text"),
            shadow="xs", radius="md", p="md", withBorder=True, className="definition-paper",
        ))

    if isinstance(value.get("by_intent"), list):
        cards = []
        for item in value["by_intent"]:
            text = item if isinstance(item, str) else item.get("detail", str(item))
            intent = "Curative" if isinstance(item, str) and "curative" in item.lower() else \
                     "Palliative" if isinstance(item, str) and "palliative" in item.lower() else \
                     item.get("intent", "Management") if isinstance(item, dict) else "Management"
            color = "#10b981" if "curative" in intent.lower() else "#f59e0b" if "palliative" in intent.lower() else "#6366f1"
            cards.append(vibrantsym_card(title=intent.title(), body=text, icon="bi-bullseye", color=color))
        if cards:
            components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))

    for key in value:
        if key in ("overview", "by_intent"):
            continue
        sub = value[key]
        if isinstance(sub, str) and sub.strip():
            components.append(dmc.Blockquote(
                dcc.Markdown(sub, className="section-text"),
                cite=key.replace("_", " ").title(),
                className="definition-blockquote",
            ))

    return components


# ── Treatment Response Assessment ─────────────────────────────────────

def render_treatment_response(value: dict, site_id: str = "") -> list:
    components = [html.H3("Treatment Response Assessment", className="section-heading")]
    if not isinstance(value, dict):
        return components

    for key, sub_val in value.items():
        label = key.replace("_", " ").title()
        if isinstance(sub_val, str) and sub_val.strip():
            components.append(dmc.Paper([
                dmc.Text(label, size="sm", fw=600, c="#1a5276", mb=4),
                dcc.Markdown(sub_val, className="section-text"),
            ], shadow="xs", radius="md", p="md", withBorder=True, className="definition-paper"))
        elif isinstance(sub_val, list):
            text = "\n\n".join(f"- {item}" for item in sub_val if isinstance(item, str))
            if text:
                components.append(dmc.Paper([
                    dmc.Text(label, size="sm", fw=600, c="#1a5276", mb=4),
                    dcc.Markdown(text, className="section-text"),
                ], shadow="xs", radius="md", p="md", withBorder=True, className="definition-paper"))
    return components


# ── Surveillance ──────────────────────────────────────────────────────

def render_surveillance(value: dict, site_id: str = "") -> list:
    components = [html.H3("Surveillance", className="section-heading")]
    if not isinstance(value, dict):
        return components

    timeline_items = []
    for key, sub_val in value.items():
        label = key.replace("_", " ").title()
        if isinstance(sub_val, str) and sub_val.strip():
            timeline_items.append({"title": label, "body": sub_val, "icon": "bi-binoculars"})
        elif isinstance(sub_val, list):
            for item in sub_val:
                if isinstance(item, str):
                    timeline_items.append({"title": label, "body": item, "icon": "bi-binoculars"})
    if timeline_items:
        components.append(timeline_component(timeline_items, color="#3b82f6"))
    return components


# ── Prognosis ─────────────────────────────────────────────────────────

def render_enhanced_prognosis(value: dict, site_id: str = "") -> list:
    components = [html.H3("Prognosis", className="section-heading")]
    if not isinstance(value, dict):
        return components

    if isinstance(value.get("overall"), str):
        components.append(dmc.Blockquote(
            dcc.Markdown(value["overall"], className="section-text"),
            cite="Overall Prognosis", icon=html.I(className="bi bi-graph-up"),
            className="definition-blockquote",
        ))

    # Try enriched cache first for survival chart
    chart_stages = []; chart_os = []
    if site_id:
        enriched = _load_enriched(site_id, "prognosis")
        if enriched:
            ec = enriched.get("chart", {})
            if ec.get("stages") and ec.get("os"):
                chart_stages = ec["stages"]
                chart_os = ec["os"]

    # Fallback: parse from raw by_stage data
    if not chart_stages and isinstance(value.get("by_stage"), list):
        for item in value["by_stage"]:
            if isinstance(item, dict):
                chart_stages.append(item.get("stage", ""))
                try:
                    surv_str = str(item.get("os_5yr", item.get("survival", "")))
                    if surv_str.strip():
                        chart_os.append(float(surv_str.replace("%", "").split("-")[-1].strip()))
                    else:
                        chart_os.append(0)
                except (ValueError, AttributeError):
                    chart_os.append(0)

    # Only show chart if >=2 valid non-zero values
    if chart_stages and any(v > 0 for v in chart_os) and sum(1 for v in chart_os if v > 0) >= 2:
        try:
            fig = prognosis_bars({"stages": chart_stages, "os_5yr": chart_os})
            if fig:
                components.append(dcc.Graph(figure=fig, config={"displayModeBar": False}, className="mb-4"))
        except Exception:
            pass

    # Prognostic factors cards
    factors = []
    if site_id:
        enriched = _load_enriched(site_id, "prognosis")
        if enriched and enriched.get("factors"):
            factors = enriched["factors"]
    if not factors and isinstance(value.get("prognostic_factors"), list):
        factors = value["prognostic_factors"]

    if factors:
        cards = []
        for pf in factors:
            if isinstance(pf, str):
                cards.append(vibrantsym_card(title="", body=pf, icon="bi-clipboard-data", color="#6366f1"))
            elif isinstance(pf, dict):
                impact = str(pf.get("impact", ""))
                color = "#10b981" if "favorable" in impact.lower() else "#ef4444"
                cards.append(vibrantsym_card(
                    title=pf.get("factor", ""), body=pf.get("detail", ""),
                    icon="bi-clipboard-data", color=color,
                    extra=[dmc.Badge(impact, color=color.replace("#", ""), variant="light")] if impact else None,
                ))
        if cards:
            components.append(html.H4("Prognostic Factors", className="subsection-heading"))
            components.append(dmc.SimpleGrid(cols={"base": 1, "sm": 2}, spacing="md", children=cards))

    return components

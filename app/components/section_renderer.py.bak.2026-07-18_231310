import json
from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.callouts import (
    alarm_indicator,
    frequency_badge,
    investigation_card,
    pearl_card,
    risk_factor_card,
    section_icon,
    stat_card,
    subtype_card,
    symptom_card,
    timeline_card,
)
from app.components.tables import create_table
import dash_mantine_components as dmc


def _render_definition(value) -> list:
    if isinstance(value, dict) and value.get("sections"):
        sections = value["sections"]
        components: list = [
            html.H3("Definition", className="section-heading"),
        ]
        for sec in sections:
            components.append(
                dmc.Blockquote(
                    dcc.Markdown(sec["content"], className="section-text definition-markdown"),
                    cite=sec["heading"],
                    icon=html.I(className="bi bi-bookmark-check"),
                    className="definition-blockquote",
                )
            )
        return components

    if isinstance(value, str) and value.strip():
        return [
            html.H3("Definition", className="section-heading"),
            dmc.Paper(
                dcc.Markdown(value, className="section-text definition-markdown"),
                shadow="xs",
                radius="md",
                p="lg",
                withBorder=True,
                className="definition-paper",
            ),
        ]

    return []


def _is_simple_val(v: Any) -> bool:
    return v is None or isinstance(v, (str, int, float, bool))


def _is_table_candidate(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    if not value:
        return False
    if not all(isinstance(item, dict) for item in value):
        return False
    first = value[0]
    return all(_is_simple_val(v) for v in first.values())


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_symptom_list(value: Any) -> bool:
    if not _is_table_candidate(value):
        return False
    keys = set(value[0].keys())
    return {"name", "detail"}.issubset(keys) and "frequency" in keys


def _is_risk_factor_list(value: Any) -> bool:
    if not _is_table_candidate(value):
        return False
    keys = set(value[0].keys())
    return {"factor", "type", "detail"}.issubset(keys)


def _is_investigation_list(value: Any) -> bool:
    if not _is_table_candidate(value):
        return False
    keys = set(value[0].keys())
    return {"test", "rationale"}.issubset(keys)


def _is_subtype_list(value: Any) -> bool:
    if not _is_table_candidate(value):
        return False
    keys = set(value[0].keys())
    return {"name", "description"}.issubset(keys) and "frequency" in keys


def _is_epidemiology_dict(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    epi_keys = {"incidence", "mortality", "trends", "demographics"}
    return bool(epi_keys & set(k.lower() for k in value.keys()))


def _label_from_key(key: str) -> str:
    return key.replace("_", " ").title()


def _render_heading(key: str, depth: int = 0) -> html.H1 | html.H2 | html.H3 | html.H4 | html.H5:
    tag = "h3" if depth == 0 else "h4" if depth <= 1 else "h5"
    icon = section_icon(key)
    label = _label_from_key(key)
    display = f"{icon}  {label}" if icon else label
    return getattr(html, tag.title())(display, className="section-heading" if depth == 0 else "subsection-heading")


def _render_epidemiology(value: dict) -> list:
    cards = []
    items = [
        ("Incidence", value.get("incidence", ""), "📈", "#1a5276"),
        ("Mortality", value.get("mortality", ""), "✝", "#c0392b"),
        ("Demographics", value.get("demographics", ""), "👥", "#2c7ba0"),
        ("Trends", value.get("trends", ""), "📊", "#27ae60"),
    ]
    for label, val, icon, color in items:
        if val:
            cards.append(dbc.Col(stat_card(label, val, icon, color), xs=12, sm=6, md=3))
    return [dbc.Row(cards, className="g-3 stat-grid")] if cards else []


def _render_symptoms(value: list, is_alarm_section: bool = False) -> list:
    return [symptom_card(s, i) for i, s in enumerate(value)]


def _render_risk_factors(value: list) -> list:
    return [risk_factor_card(rf, i) for i, rf in enumerate(value)]


def _render_investigations(value: list) -> list:
    return [investigation_card(inv) for inv in value]


def _render_subtypes(value: list) -> list:
    return [subtype_card(s) for s in value]


def _render_pearls(value: list) -> list:
    return [pearl_card(p, i) for i, p in enumerate(value)]


def _render_surveillance(value: Any) -> list:
    cards = []
    if isinstance(value, dict):
        for sub_key, sub_val in value.items():
            if isinstance(sub_val, list):
                for item in sub_val:
                    if isinstance(item, str):
                        cards.append(timeline_card(item, "📅"))
            elif isinstance(sub_val, str):
                cards.append(timeline_card(sub_val, "📅"))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                cards.append(timeline_card(item, "📅"))
    if not cards:
        cards = [timeline_card(str(value), "📅")]
    return cards


def render_section(key: str, value: Any, depth: int = 0) -> list:
    components: list = []

    if value is None or (isinstance(value, (list, dict)) and not value):
        return components

    if isinstance(value, str):
        if depth == 0 and len(key) > 2:
            components.append(_render_heading(key, depth))
            components.append(dcc.Markdown(value, className="section-text"))
        else:
            components.append(html.Div([
                html.Strong(_label_from_key(key) + ": "),
                html.Span(value),
            ], className="kv-pair"))

    elif isinstance(value, (int, float)):
        components.append(html.Div([
            html.Strong(_label_from_key(key) + ": "),
            html.Span(str(value)),
        ], className="kv-pair"))

    elif isinstance(value, bool):
        if key in ("alarm", "alert"):
            components.append(html.Div([
                html.Strong(_label_from_key(key) + ": "),
                alarm_indicator(value),
            ], className="kv-pair"))
        elif key == "mandatory":
            components.append(html.Div([
                html.Strong(_label_from_key(key) + ": "),
                dbc.Badge("Required", color="success", className="rounded-pill") if value else dbc.Badge("Optional", color="secondary", className="rounded-pill"),
            ], className="kv-pair"))
        else:
            components.append(html.Div([
                html.Strong(_label_from_key(key) + ": "),
                dbc.Badge("Yes", color="primary", className="rounded-pill") if value else dbc.Badge("No", color="secondary", className="rounded-pill"),
            ], className="kv-pair"))

    elif _is_symptom_list(value):
        components.append(_render_heading(key, depth))
        is_alarm = "alarm" in key or "red_flag" in key
        components.extend(_render_symptoms(value, is_alarm))

    elif _is_risk_factor_list(value):
        components.append(_render_heading(key, depth))
        components.extend(_render_risk_factors(value))

    elif _is_investigation_list(value):
        components.append(_render_heading(key, depth))
        components.extend(_render_investigations(value))

    elif _is_subtype_list(value):
        components.append(_render_heading(key, depth))
        components.extend(_render_subtypes(value))

    elif _is_table_candidate(value):
        components.append(_render_heading(key, depth))
        components.append(create_table(
            data=value,
            page_size=min(len(value), 20),
            filter_action="native" if len(value) > 10 else "none",
        ))

    elif _is_string_list(value):
        is_pearl = "pearl" in key or "red_flag" in key
        components.append(_render_heading(key, depth))
        if is_pearl:
            components.extend(_render_pearls(value))
        elif "surveillance" in key or "follow" in key or "imaging" in key:
            components.extend(_render_surveillance(value))
        else:
            items = [html.Li(item) for item in value]
            components.append(html.Ul(items, className="styled-list"))

    elif isinstance(value, dict):
        if _is_epidemiology_dict(value):
            components.append(_render_heading(key, depth))
            components.extend(_render_epidemiology(value))
            for sub_key, sub_val in value.items():
                if sub_val and sub_key not in ("incidence", "mortality", "trends", "demographics"):
                    components.extend(render_section(sub_key, sub_val, depth + 1))
            return components

        if "surveillance" in key or "follow_up" in key:
            components.append(_render_heading(key, depth))
            components.extend(_render_surveillance(value))
            return components

        if "complication" in key:
            components.append(_render_heading(key, depth))
            for sub_key, sub_val in value.items():
                if sub_val:
                    components.append(html.H6(_label_from_key(sub_key), className="complication-group"))
                    if isinstance(sub_val, list):
                        for item in sub_val:
                            if isinstance(item, str):
                                components.append(dbc.Card(
                                    dbc.CardBody(html.P(item, className="mb-0")),
                                    className="complication-card mb-2",
                                    color="danger" if "disease" in sub_key else "warning",
                                    inverse=False if "disease" not in sub_key else True,
                                ))
                            elif isinstance(item, dict):
                                components.append(dbc.Card(
                                    dbc.CardBody([
                                        html.Strong(item.get("complication", item.get("name", ""))),
                                        html.P(item.get("management", item.get("detail", "")), className="small mb-0"),
                                    ]),
                                    className="complication-card mb-2",
                                ))
                    elif isinstance(sub_val, str):
                        components.append(dcc.Markdown(sub_val, className="section-text"))
            return components

        if "supportive" in key or "care" in key:
            components.append(_render_heading(key, depth))
            for sub_key, sub_val in value.items():
                if sub_val:
                    components.append(html.H6(_label_from_key(sub_key), className="supportive-sub"))
                    if isinstance(sub_val, str):
                        components.append(dcc.Markdown(sub_val, className="section-text"))
                    elif isinstance(sub_val, list):
                        components.append(html.Ul([html.Li(str(v)) for v in sub_val if v], className="styled-list"))
            return components

        if "investigation" in key:
            components.append(_render_heading(key, depth))
            for sub_key, sub_val in value.items():
                if sub_val and isinstance(sub_val, list):
                    components.append(html.H6(_label_from_key(sub_key), className="investigation-group"))
                    for item in sub_val:
                        if isinstance(item, dict) and item.get("test"):
                            components.append(investigation_card(item))
                        elif isinstance(item, str):
                            components.append(html.Li(item, className="ms-3"))
            return components

        components.append(_render_heading(key, depth))

        is_flat = all(isinstance(v, (str, int, float, bool, type(None))) for v in value.values())
        if is_flat and len(value) <= 6:
            items = []
            for sub_key, sub_val in value.items():
                if sub_val is None:
                    continue
                if isinstance(sub_val, bool):
                    if sub_key in ("alarm", "alert"):
                        items.append(html.Div([
                            html.Strong(_label_from_key(sub_key) + ": "),
                            alarm_indicator(sub_val),
                        ], className="kv-pair"))
                    elif sub_key == "mandatory":
                        items.append(html.Div([
                            html.Strong(_label_from_key(sub_key) + ": "),
                            dbc.Badge("Required", color="success", className="rounded-pill") if sub_val else dbc.Badge("Optional", color="secondary", className="rounded-pill"),
                        ], className="kv-pair"))
                    else:
                        items.append(html.Div([
                            html.Strong(_label_from_key(sub_key) + ": "),
                            dbc.Badge("Yes", color="primary", className="rounded-pill") if sub_val else dbc.Badge("No", color="secondary", className="rounded-pill"),
                        ], className="kv-pair"))
                else:
                    items.append(html.Div([
                        html.Strong(_label_from_key(sub_key) + ": "),
                        html.Span(str(sub_val)),
                    ], className="kv-pair"))
            components.extend(items)
        else:
            for sub_key, sub_val in value.items():
                if sub_val is None or not sub_val:
                    continue
                if "clinical_feature" in sub_key or "red_flag" in sub_key:
                    if isinstance(sub_val, dict):
                        symptoms = sub_val.get("symptoms", [])
                        signs = sub_val.get("signs", [])
                        if symptoms:
                            components.append(html.H6("Symptoms", className="subsection-heading"))
                            components.extend(_render_symptoms(symptoms))
                        if signs:
                            components.append(html.H6("Signs", className="subsection-heading"))
                            components.extend(_render_symptoms(signs))
                        for sk, sv in sub_val.items():
                            if sk not in ("symptoms", "signs") and sv:
                                components.extend(render_section(sk, sv, depth + 1))
                    else:
                        components.extend(render_section(sub_key, sub_val, depth + 1))
                elif "investigation" in sub_key:
                    if isinstance(sub_val, dict):
                        for inv_key, inv_val in sub_val.items():
                            if isinstance(inv_val, list):
                                components.append(html.H6(_label_from_key(inv_key), className="subsection-heading"))
                                for item in inv_val:
                                    if isinstance(item, dict) and item.get("test"):
                                        components.append(investigation_card(item))
                                    elif isinstance(item, str):
                                        components.append(html.Li(item, className="ms-3"))
                            elif inv_val:
                                components.extend(render_section(inv_key, inv_val, depth + 1))
                    else:
                        components.extend(render_section(sub_key, sub_val, depth + 1))
                else:
                    components.extend(render_section(sub_key, sub_val, depth + 1))

    elif isinstance(value, list):
        components.append(_render_heading(key, depth))
        for idx, item in enumerate(value):
            if isinstance(item, str):
                components.append(html.Li(item, className="ms-3"))
            elif isinstance(item, dict):
                components.append(html.Div(
                    json.dumps(item, indent=2),
                    className="ms-3 mb-2 p-2 bg-light rounded",
                    style={"fontSize": "0.85rem", "whiteSpace": "pre-wrap", "fontFamily": "monospace"},
                ))
            else:
                components.append(html.Li(str(item), className="ms-3"))

    return components


def _render_management_pathways(value: list) -> list:
    if not value:
        return []
    components = []
    for pw in value:
        if not isinstance(pw, dict):
            continue
        title = pw.get("title", pw.get("pathway_id", "Pathway"))
        branching = pw.get("branching_basis", [])
        nodes = pw.get("nodes", [])

        node_items = []
        for node in nodes:
            criteria = node.get("criteria", "")
            options = node.get("options", [])
            opt_text = "; ".join(
                f"{o.get('label', o.get('type', ''))} ({o.get('preference', o.get('recommendation', ''))})"
                for o in options if isinstance(o, dict)
            )
            adj = node.get("adjuvant_logic", {})
            adj_text = ""
            if isinstance(adj, dict):
                adj_text = adj.get("summary", str(adj)) if not adj.get("applies") is False else ""

            node_items.append(dbc.Card(
                dbc.CardBody([
                    html.Strong(criteria) if criteria else None,
                    html.P(opt_text, className="small text-muted mb-1") if opt_text else None,
                    html.P(adj_text, className="small text-info mb-0") if adj_text else None,
                ]),
                className="pathway-node-card mb-2",
            ))

        components.append(dbc.Card([
            dbc.CardHeader(html.Strong(title)),
            dbc.CardBody([
                html.P(", ".join(branching), className="small text-muted") if branching else None,
                *node_items,
            ]),
        ], className="pathway-card mb-3"))

    return components


def _render_pretreatment_evaluation(value: list) -> list:
    if not value:
        return []
    components = []
    for cat in value:
        if not isinstance(cat, dict):
            continue
        category = cat.get("category", "")
        items = cat.get("items", [])
        item_cards = []
        for it in items:
            if not isinstance(it, dict):
                continue
            item_cards.append(dbc.Card(
                dbc.CardBody([
                    html.Strong(it.get("text", "")),
                    html.P(it.get("recommendation", ""), className="small text-muted mb-0") if it.get("recommendation") else None,
                ]),
                className="pre-eval-card mb-2",
            ))
        if item_cards:
            components.append(html.Div([
                html.H6(category, className="pre-eval-category"),
                *item_cards,
            ], className="mb-3"))

    return components


def _render_systemic_therapy(value: dict) -> list:
    if not value:
        return []
    components = []
    overview = value.get("overview", "")
    if overview:
        components.append(dcc.Markdown(overview, className="section-text"))

    by_stage = value.get("by_stage_and_setting", [])
    if isinstance(by_stage, list):
        for item in by_stage:
            if not isinstance(item, dict):
                continue
            components.append(dbc.Card(
                dbc.CardBody([
                    html.Strong(item.get("setting", "")),
                    html.P(item.get("rationale", ""), className="small text-muted mb-1") if item.get("rationale") else None,
                    html.P("Preferred: " + str(item.get("preferred_regimen", "")), className="small mb-0") if item.get("preferred_regimen") else None,
                ]),
                className="systemic-card mb-2",
            ))

    key_regimens = value.get("key_regimens", [])
    if isinstance(key_regimens, list) and key_regimens:
        components.append(html.H5("Key Regimens", className="mt-3 mb-2"))
        for kr in key_regimens:
            if not isinstance(kr, dict):
                continue
            drugs = kr.get("drugs", [])
            drug_strs = []
            for d in (drugs if isinstance(drugs, list) else []):
                if not isinstance(d, dict):
                    continue
                day_or_schedule = d.get("day") or d.get("schedule", "")
                drug_strs.append(f"{d.get('name', '')} {d.get('dose', '')} {d.get('route', '')} {day_or_schedule}".strip())
            components.append(dbc.Card(
                dbc.CardBody([
                    html.Strong(kr.get("name", kr.get("setting", ""))),
                    html.P(" + ".join(drug_strs), className="small text-muted mb-1") if drug_strs else None,
                    html.P(str(kr.get("cycle_days", "")), className="small mb-0") if kr.get("cycle_days") else None,
                ]),
                className="systemic-card mb-2",
            ))

    return components


_handbook_render_cache: dict[int, list] = {}


def render_handbook(handbook: dict[str, Any]) -> list:
    if not handbook:
        return [html.P("No handbook data available for this site.", className="text-muted")]

    cache_key = id(handbook)
    if cache_key in _handbook_render_cache:
        return _handbook_render_cache[cache_key]

    from app.components.staging_viewer import (
        render_prognosis,
        render_radiation_therapy,
        render_staging,
        render_trials,
    )

    priority_keys = [
        "definition", "epidemiology", "subtypes", "molecular_pathogenesis",
        "risk_factors", "protective_factors",
        "clinical_features", "red_flags",
        "investigations", "staging",
        "management_principles", "management_pathways",
        "pretreatment_evaluation", "surgery", "radiation_therapy",
        "systemic_therapy", "treatment_response_assessment",
        "surveillance", "complications", "supportive_care",
        "prognosis", "follow_up", "key_trials", "clinical_pearls",
        "special_situations", "guidelines_resources", "drug_information",
    ]

    custom_renderers = {
        "definition": _render_definition,
        "staging": render_staging,
        "radiation_therapy": render_radiation_therapy,
        "key_trials": render_trials,
        "prognosis": render_prognosis,
        "management_pathways": _render_management_pathways,
        "pretreatment_evaluation": _render_pretreatment_evaluation,
        "systemic_therapy": _render_systemic_therapy,
    }

    all_components: list = []
    seen: set[str] = set()

    for key in priority_keys:
        if key not in handbook or key in seen:
            continue
        seen.add(key)
        value = handbook[key]
        if not value:
            continue

        sub_site_keys = [k for k in handbook if k != key and k not in seen and key.split("_")[0] in k]
        for sk in sub_site_keys:
            seen.add(sk)

        renderer = custom_renderers.get(key)
        if renderer:
            all_components.append(html.Div(id=key, children=renderer(value)))
        else:
            all_components.append(html.Div(id=key, children=render_section(key, value)))

    for key, value in handbook.items():
        if key in seen:
            continue
        seen.add(key)
        if not value:
            continue
        all_components.append(html.Div(id=key, children=render_section(key, value)))

    _handbook_render_cache[cache_key] = all_components
    return all_components

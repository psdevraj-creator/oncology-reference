import json
from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.tables import create_table

SPECIAL_SECTIONS = {
    "staging",
    "radiation_therapy",
    "key_trials",
    "prognosis",
    "systemic_therapy",
    "management_pathways",
    "dose_frameworks",
    "surveillance",
    "complications",
    "supportive_care",
}


def _is_table_candidate(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    if not value:
        return False
    return all(isinstance(item, dict) for item in value)


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _label_from_key(key: str) -> str:
    return key.replace("_", " ").title()


def render_section(key: str, value: Any, depth: int = 0) -> list:
    components: list = []

    if value is None or (isinstance(value, (list, dict)) and not value):
        return components

    if isinstance(value, str):
        heading_tag = "h4" if depth == 0 else "h5" if depth <= 1 else "h6"
        components.append(getattr(html, heading_tag.title())(
            _label_from_key(key), className="section-heading" if depth == 0 else "subsection-heading"
        ))
        components.append(dcc.Markdown(
            value,
            className="section-text",
            style={"fontSize": "0.95rem", "lineHeight": "1.6"},
        ))

    elif isinstance(value, (int, float)):
        row = dbc.Row([
            dbc.Col(html.Strong(_label_from_key(key) + ": "), width="auto"),
            dbc.Col(html.Span(str(value))),
        ], className="mb-1")
        components.append(row)

    elif isinstance(value, bool):
        badge = dbc.Badge("Yes" if value else "No", color="primary" if value else "secondary")
        components.append(html.Span([html.Strong(_label_from_key(key) + ": "), badge]))

    elif _is_table_candidate(value):
        heading_tag = "h4" if depth == 0 else "h5" if depth <= 1 else "h6"
        components.append(getattr(html, heading_tag.title())(
            _label_from_key(key), className="section-heading" if depth == 0 else "subsection-heading"
        ))
        components.append(create_table(
            data=value,
            page_size=min(len(value), 20),
            filter_action="native" if len(value) > 10 else "none",
        ))

    elif _is_string_list(value):
        heading_tag = "h4" if depth == 0 else "h5" if depth <= 1 else "h6"
        components.append(getattr(html, heading_tag.title())(
            _label_from_key(key), className="section-heading" if depth == 0 else "subsection-heading"
        ))
        components.append(html.Ul([html.Li(item) for item in value], className="mb-3"))

    elif isinstance(value, dict):
        heading_tag = "h4" if depth == 0 else "h5" if depth <= 1 else "h6"
        is_flat = all(
            isinstance(v, (str, int, float, bool, type(None)))
            for v in value.values()
        )
        if is_flat and len(value) <= 6:
            components.append(getattr(html, heading_tag.title())(
                _label_from_key(key), className="section-heading" if depth == 0 else "subsection-heading"
            ))
            for sub_key, sub_val in value.items():
                if sub_val is None:
                    continue
                components.append(html.Div([
                    html.Strong(_label_from_key(sub_key) + ": "),
                    html.Span(str(sub_val)),
                ], className="mb-1 ms-3"))
        else:
            components.append(getattr(html, heading_tag.title())(
                _label_from_key(key), className="section-heading" if depth == 0 else "subsection-heading"
            ))
            for sub_key, sub_val in value.items():
                components.extend(render_section(sub_key, sub_val, depth + 1))

    elif isinstance(value, list):
        heading_tag = "h4" if depth == 0 else "h5" if depth <= 1 else "h6"
        components.append(getattr(html, heading_tag.title())(
            _label_from_key(key), className="section-heading" if depth == 0 else "subsection-heading"
        ))
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


def render_handbook(handbook: dict[str, Any]) -> list:
    if not handbook:
        return [html.P("No handbook data available for this site.", className="text-muted")]

    from app.components.staging_viewer import (
        render_prognosis,
        render_radiation_therapy,
        render_staging,
        render_trials,
    )

    priority_keys = [
        "definition", "epidemiology", "subtypes", "molecular_pathogenesis",
        "clinical_features", "investigations", "staging",
        "management_principles", "management_pathways",
        "pretreatment_evaluation", "surgery", "radiation_therapy",
        "systemic_therapy", "treatment_response_assessment",
        "surveillance", "complications", "supportive_care",
        "prognosis", "follow_up", "key_trials", "clinical_pearls",
        "special_situations", "guidelines_resources", "drug_information",
    ]

    custom_renderers = {
        "staging": render_staging,
        "radiation_therapy": render_radiation_therapy,
        "key_trials": render_trials,
        "prognosis": render_prognosis,
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

        renderer = custom_renderers.get(key)
        if renderer:
            all_components.extend(renderer(value))
        else:
            all_components.extend(render_section(key, value))

    for key, value in handbook.items():
        if key in seen:
            continue
        seen.add(key)
        if not value:
            continue
        all_components.extend(render_section(key, value))

    return all_components

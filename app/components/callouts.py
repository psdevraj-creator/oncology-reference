import dash_bootstrap_components as dbc
from dash import html


def warning_box(message: str, title: str = "Clinical Warning") -> dbc.Alert:
    return dbc.Alert([
        html.H5(title, className="alert-heading"),
        html.P(message),
    ], color="warning", className="callout-warning")


def pearl_box(message: str, title: str = "FRCR Pearl") -> dbc.Alert:
    return dbc.Alert([
        html.H5(title, className="alert-heading"),
        html.P(message),
    ], color="info", className="callout-pearl")


def success_box(message: str, title: str = "Key Point") -> dbc.Alert:
    return dbc.Alert([
        html.H5(title, className="alert-heading"),
        html.P(message),
    ], color="success", className="callout-success")


def danger_box(message: str, title: str = "Red Flag") -> dbc.Alert:
    return dbc.Alert([
        html.H5(title, className="alert-heading"),
        html.P(message),
    ], color="danger", className="callout-danger")


def info_panel(items: list[str], title: str = "Clinical Notes") -> dbc.Card:
    if not items:
        return dbc.Card()
    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="card-subtitle mb-2"),
            html.Ul([html.Li(item, className="mb-1") for item in items]),
        ]),
        className="mb-3 shadow-sm",
    )


def alarm_indicator(alarm: bool) -> html.Span:
    if alarm:
        return html.Span(" RED FLAG", className="alarm-on")
    return html.Span("", className="alarm-off")


def frequency_badge(freq: str) -> dbc.Badge | None:
    if not freq:
        return None
    freq_lower = freq.lower().strip()
    if "common" in freq_lower:
        color = "primary"
    elif "occasional" in freq_lower or "rare" in freq_lower:
        color = "secondary"
    else:
        color = "light"
    return dbc.Badge(freq, color=color, className="frequency-badge rounded-pill")


def symptom_card(symptom: dict, index: int = 0) -> dbc.Card:
    alarm = symptom.get("alarm", False)
    name = symptom.get("name", "")
    detail = symptom.get("detail", "")
    freq = symptom.get("frequency", "")

    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.Span(alarm_indicator(alarm), className="me-2" if alarm else ""),
                html.Strong(name),
                frequency_badge(freq) if freq else None,
            ], className="symptom-header"),
            html.P(detail, className="symptom-detail") if detail else None,
        ]),
        className=f"symptom-card mb-2 {'symptom-alarm' if alarm else ''}",
    )


def risk_factor_card(rf: dict, index: int = 0) -> dbc.Card:
    factor = rf.get("factor", "")
    rf_type = rf.get("type", "")
    detail = rf.get("detail", "")
    strength = rf.get("strength", "")

    strength_colors = {
        "strong": "danger",
        "well-established": "warning",
        "moderate": "info",
        "weak": "secondary",
    }
    s_lower = strength.lower().strip()
    strength_color = "secondary"
    for k, v in strength_colors.items():
        if k in s_lower:
            strength_color = v
            break

    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.Strong(factor),
                dbc.Badge(strength, color=strength_color, className="strength-badge ms-2 rounded-pill") if strength else None,
                dbc.Badge(rf_type, color="light", className="ms-1 rounded-pill") if rf_type else None,
            ], className="rf-header"),
            html.P(detail, className="rf-detail") if detail else None,
        ]),
        className="risk-factor-card mb-2",
    )


def stat_card(label: str, value: str, icon: str = "", color: str = "#2c7ba0") -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.Div(icon, className="stat-card-icon") if icon else None,
            html.Div(str(value), className="stat-card-value", style={"color": color}),
            html.Div(label, className="stat-card-label"),
        ]),
        className="mini-stat-card shadow-sm text-center h-100",
    )


def pearl_card(pearl: str, index: int = 0) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.Div(f"{index + 1}.", className="pearl-number"),
            html.P(pearl, className="pearl-text"),
        ]),
        className="pearl-card mb-2",
    )


def investigation_card(test: dict) -> dbc.Card:
    name = test.get("test", test.get("name", ""))
    rationale = test.get("rationale", "")
    findings = test.get("key_findings", "") or test.get("indication", "")

    return dbc.Card(
        dbc.CardBody([
            html.Strong(name, className="inv-name"),
            html.P(rationale, className="inv-rationale small text-muted") if rationale else None,
            html.P(findings, className="inv-findings small") if findings else None,
        ]),
        className="investigation-card mb-2",
    )


def timeline_card(text: str, icon: str = "") -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.Span(icon, className="timeline-icon") if icon else None,
                html.Span(text, className="timeline-text"),
            ], className="timeline-item"),
        ]),
        className="timeline-card mb-2",
    )


def subtype_card(sub: dict) -> dbc.Card:
    name = sub.get("name", "")
    desc = sub.get("description", "")
    freq = sub.get("frequency", "")
    associations = sub.get("key_associations", [])

    items = [
        html.Div([
            html.Strong(name),
            dbc.Badge(freq, color="info", className="ms-2 rounded-pill") if freq else None,
        ], className="subtype-header"),
        html.P(desc, className="subtype-desc") if desc else None,
    ]
    if associations:
        items.append(html.Div([
            html.Small("Associated: ", className="text-muted"),
            html.Small(", ".join(associations), className="text-muted"),
        ]))
    return dbc.Card(
        dbc.CardBody(items),
        className="subtype-card mb-2",
    )


def section_icon(key: str) -> str:
    icons = {
        "definition": "📖",
        "epidemiology": "📊",
        "subtypes": "🧬",
        "molecular_pathogenesis": "🔬",
        "risk_factors": "⚠",
        "protective_factors": "🛡",
        "clinical_features": "🩺",
        "red_flags": "🚩",
        "investigations": "🔍",
        "staging": "📋",
        "management_principles": "📐",
        "management_pathways": "🗺",
        "pretreatment_evaluation": "✅",
        "surgery": "🔪",
        "radiation_therapy": "☢",
        "systemic_therapy": "💊",
        "treatment_response_assessment": "📈",
        "surveillance": "📅",
        "complications": "⚡",
        "supportive_care": "🤝",
        "prognosis": "🔮",
        "follow_up": "📆",
        "key_trials": "📜",
        "clinical_pearls": "💡",
        "special_situations": "🔀",
        "guidelines_resources": "📚",
        "drug_information": "💉",
    }
    for k, icon in icons.items():
        if k in key:
            return icon
    return ""

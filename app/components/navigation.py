import dash_bootstrap_components as dbc
from dash import html


def breadcrumb(items: list[tuple[str, str]]) -> dbc.Breadcrumb:
    bc_items = []
    for label, href in items:
        if href:
            bc_items.append({"label": label, "href": href})
        else:
            bc_items.append({"label": label, "active": True})
    return dbc.Breadcrumb(items=bc_items, className="breadcrumb-nav")


def sidebar_nav(sections: list[dict], active_section: str = "") -> dbc.Nav:
    nav_items = []
    for sec in sections:
        is_active = sec.get("id") == active_section
        nav_items.append(
            dbc.NavItem(
                html.A(
                    sec.get("label", sec.get("id", "")),
                    href=f"#{sec.get('id', '')}",
                    className=f"sidebar-link nav-link {'active' if is_active else ''}",
                )
            )
        )
    return dbc.Nav(nav_items, vertical=True, pills=True, className="sidebar-nav flex-column")


def generate_toc(handbook: dict) -> list[dict]:
    sections: list[dict] = []
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
    seen: set[str] = set()
    for key in priority_keys:
        if key in handbook and key not in seen:
            sections.append({"id": key, "label": key.replace("_", " ").title()})
            seen.add(key)
    for key in handbook:
        if key not in seen:
            sections.append({"id": key, "label": key.replace("_", " ").title()})
            seen.add(key)
    return sections

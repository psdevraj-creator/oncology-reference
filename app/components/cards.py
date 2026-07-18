import dash_bootstrap_components as dbc
from dash import html

from app.data.category_map import SYSTEMS, get_system_for_site


def disease_card(site: dict, system_color: str | None = None) -> dbc.Col:
    site_id = site["id"]
    color = system_color or site.get("color_accent", "#2563eb")
    desc = site.get("description", "")
    regimens = site.get("regimen_count", 0)
    sys_info = get_system_for_site(site_id)
    system_label = sys_info["name"] if sys_info else None

    return dbc.Col(
        html.A(
            dbc.Card([
                dbc.CardBody([
                    html.Div(site.get("emoji", "\U0001f9ec"), className="card-emoji"),
                    html.H5(site["display_name"], className="card-site-name"),
                    html.P(
                        desc if desc else f"{regimens} regimens",
                        className="card-description",
                    ),
                    html.Div([
                        dbc.Badge(f"{regimens} regimens", className="card-badge rounded-pill"),
                        *(
                            [dbc.Badge(system_label, className="card-badge card-system-badge rounded-pill")]
                            if system_label else []
                        ),
                    ], className="card-badges"),
                ]),
            ],
                className="disease-card shadow-sm h-100",
                style={"borderLeft": f"3px solid {color}"},
            ),
            href=f"/disease/{site_id}",
            className="text-decoration-none",
        ),
        xs=12, sm=6, md=4, lg=3,
        className="mb-3",
    )


def disease_grid(sites: list[dict]) -> dbc.Row:
    return dbc.Row(
        [disease_card(site) for site in sites],
        className="g-3 disease-grid",
    )


def category_section(system_key: str, sites: list[dict]) -> html.Div:
    sys_info = SYSTEMS[system_key]
    color = sys_info["color"]
    return html.Div([
        html.Div([
            html.I(className=f"bi {sys_info['icon']} cat-header-icon"),
            html.Span(sys_info["name"], className="cat-header-name"),
        ], className="category-header", style={"borderColor": color}),
        disease_grid(sites),
    ],
        id=f"system-{system_key}",
        className="category-section",
    )


def category_sections(grouped: dict[str, list[dict]]) -> list:
    sections = []
    for i, (key, sites) in enumerate(grouped.items()):
        cls = "category-section" if i % 2 == 0 else "category-section category-section-alt"
        sys_info = SYSTEMS[key]
        color = sys_info["color"]
        sections.append(html.Div([
            html.Div([
                html.I(className=f"bi {sys_info['icon']} cat-header-icon"),
                html.Span(sys_info["name"], className="cat-header-name"),
                dbc.Badge(f"{len(sites)} sites", className="cat-header-count rounded-pill"),
            ], className="category-header", style={"borderColor": color}),
            disease_grid(sites),
        ],
            id=f"system-{key}",
            className=cls,
        ))
    return sections

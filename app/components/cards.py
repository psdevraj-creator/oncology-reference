import dash_bootstrap_components as dbc
from dash import html


def disease_card(site: dict) -> dbc.Col:
    site_id = site["id"]
    accent = site.get("color_accent", "#2563eb")
    desc = site.get("description", "")
    regimens = site.get("regimen_count", 0)

    return dbc.Col(
        html.A(
            dbc.Card([
                html.Div(
                    className="card-accent-bar",
                    style={"backgroundColor": accent},
                ),
                dbc.CardBody([
                    html.Div([
                        html.Span(site.get("emoji", ""), className="card-emoji"),
                        html.Span(site["display_name"], className="card-site-name"),
                    ], className="card-site-header"),
                    html.P(
                        desc if desc else f"Clinical reference with {regimens} regimens",
                        className="card-description",
                    ),
                    html.Div([
                        dbc.Badge(f"{regimens} regimens", color="primary", className="card-badge"),
                        dbc.Badge(
                            f"Type {site.get('archetype', '?')}",
                            color="secondary",
                            className="card-badge",
                        ),
                    ], className="card-badges"),
                ]),
            ],
                className="disease-card shadow-sm h-100",
                style={"borderTop": f"3px solid {accent}"},
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

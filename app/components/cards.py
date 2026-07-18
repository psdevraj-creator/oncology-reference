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
                html.Div(className="card-accent-bar", style={"backgroundColor": accent}),
                dbc.CardBody([
                    html.Div(site.get("emoji", ""), className="card-emoji"),
                    html.H5(site["display_name"], className="card-site-name"),
                    html.P(
                        desc if desc else f"{regimens} regimens — clinical reference",
                        className="card-description",
                    ),
                    html.Div([
                        dbc.Badge(f"{regimens} regimens", color="primary", className="card-badge rounded-pill"),
                        dbc.Badge(
                            f"Type {site.get('archetype', '?')}",
                            color="secondary",
                            className="card-badge rounded-pill",
                        ),
                    ], className="card-badges"),
                ]),
            ],
                className="disease-card shadow-sm h-100",
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

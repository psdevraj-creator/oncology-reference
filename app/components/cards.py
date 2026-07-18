import dash_bootstrap_components as dbc
from dash import html


def disease_card(site: dict) -> dbc.Col:
    site_id = site["id"]
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.Div(site.get("emoji", ""), className="card-emoji"),
                html.H5(site["display_name"], className="card-title"),
                html.P(
                    f"{site.get('regimen_count', 0)} regimens",
                    className="card-text text-muted",
                ),
                dbc.Badge(
                    f"Archetype {site.get('archetype', '?')}",
                    color="secondary",
                    className="me-1",
                ),
            ]),
            id=f"card-{site_id}",
            className="disease-card h-100 shadow-sm",
            style={"borderLeft": f"4px solid {site.get('color_accent', '#2563eb')}"},
        ),
        xs=12, sm=6, md=4, lg=3, xxl=2,
        className="mb-3",
    )


def disease_grid(sites: list[dict]) -> dbc.Row:
    return dbc.Row(
        [disease_card(site) for site in sites],
        className="g-3 disease-grid",
    )

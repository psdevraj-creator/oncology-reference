from dash import dcc, html

import dash_bootstrap_components as dbc


def create_layout() -> html.Div:
    return html.Div([
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="user-filters", storage_type="session"),

        dbc.Navbar(
            dbc.Container([
                dbc.NavbarBrand(
                    [html.I(className="bi bi-journal-medical me-2"), "Oncology Interactive Handbook"],
                    href="/",
                    className="navbar-brand-text",
                ),
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Home", href="/", className="nav-link-text")),
                ], className="ms-auto", navbar=True),
            ], fluid=True),
            color="primary",
            dark=True,
            className="app-navbar shadow-sm",
        ),

        dbc.Container(
            id="page-content",
            fluid=True,
            className="app-content px-3 py-3",
        ),

        html.Footer(
            dbc.Container([
                html.Hr(),
                html.P(
                    "Oncology Interactive Handbook — Clinical reference for educational purposes. "
                    "Not a substitute for clinical judgment.",
                    className="text-muted text-center small",
                ),
            ], fluid=True),
            className="app-footer",
        ),
    ])

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

import dash_bootstrap_components as dbc
from dash import dcc, html


def search_bar(placeholder="Search disease sites...", search_id="search-input"):
    return dbc.InputGroup([
        dbc.InputGroupText(html.I(className="bi bi-search")),
        dbc.Input(
            id=search_id,
            type="text",
            placeholder=placeholder,
            className="form-control",
            debounce=True,
        ),
    ], className="mb-4 search-bar")


def setting_filter(dropdown_id="setting-filter", settings=None):
    if settings is None:
        settings = []
    return html.Div([
        html.Label("Clinical Setting", className="filter-label"),
        dcc.Dropdown(
            id=dropdown_id,
            options=[{"label": s, "value": s} for s in settings],
            multi=True,
            placeholder="All settings",
            clearable=True,
            className="filter-dropdown mb-2",
        ),
    ])


def modality_filter(dropdown_id="modality-filter", modalities=None):
    if modalities is None:
        modalities = []
    return html.Div([
        html.Label("Treatment Modality", className="filter-label"),
        dcc.Dropdown(
            id=dropdown_id,
            options=[{"label": m.title(), "value": m} for m in modalities],
            multi=True,
            placeholder="All modalities",
            clearable=True,
            className="filter-dropdown",
        ),
    ])


def biomarker_filter(dropdown_id="biomarker-filter", biomarkers=None):
    if biomarkers is None:
        biomarkers = []
    return html.Div([
        html.Label("Biomarker", className="filter-label"),
        dcc.Dropdown(
            id=dropdown_id,
            options=[{"label": b, "value": b} for b in biomarkers],
            multi=True,
            placeholder="Any biomarker",
            clearable=True,
            className="filter-dropdown",
        ),
    ])


def filter_bar(settings=None, modalities=None, biomarkers=None):
    return dbc.Row([
        dbc.Col(setting_filter(settings=settings), xs=12, md=4),
        dbc.Col(modality_filter(modalities=modalities), xs=12, md=4),
        dbc.Col(biomarker_filter(biomarkers=biomarkers), xs=12, md=4),
    ], className="filter-bar mb-3 p-3 bg-light rounded")

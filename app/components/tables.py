from dash import dash_table


TABLE_STYLE_DATA = {
    "backgroundColor": "#ffffff",
    "color": "#212529",
    "fontSize": "0.875rem",
    "fontFamily": "'Segoe UI', system-ui, -apple-system, sans-serif",
    "whiteSpace": "normal",
    "height": "auto",
    "lineHeight": "1.4",
}

TABLE_STYLE_HEADER = {
    "backgroundColor": "#f1f3f5",
    "color": "#212529",
    "fontWeight": "600",
    "fontSize": "0.8rem",
    "textTransform": "uppercase",
    "letterSpacing": "0.5px",
    "borderBottom": "2px solid #dee2e6",
}

TABLE_STYLE_CELL = {
    "minWidth": "80px",
    "maxWidth": "300px",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
    "padding": "8px 12px",
}

TABLE_STYLE_FILTER = {
    "backgroundColor": "#f8f9fa",
}

TABLE_CSS = [
    {"selector": ".dash-spreadsheet", "rule": "font-family: 'Segoe UI', system-ui, sans-serif;"},
    {"selector": ".dash-filter input", "rule": "border: 1px solid #ced4da; border-radius: 4px; padding: 4px 8px;"},
    {"selector": ".dash-table-container .row", "rule": "margin: 0;"},
]


def create_table(
    data,
    columns=None,
    id=None,
    filter_action="native",
    sort_action="native",
    page_size=20,
    row_selectable=None,
    style_cell_conditional=None,
    hidden_columns=None,
    tooltip_data=None,
    tooltip_duration=None,
    active_cell=None,
    **kwargs,
):
    if columns is None and data:
        if isinstance(data, list) and data:
            columns = [{"name": c.replace("_", " ").title(), "id": c} for c in data[0].keys()]
        else:
            columns = []

    if hidden_columns is None:
        hidden_columns = ["_site_id", "_archetype"]

    table_kwargs = {
        "data": data,
        "columns": columns,
        "filter_action": filter_action,
        "sort_action": sort_action,
        "page_size": page_size,
        "row_selectable": row_selectable,
        "column_selectable": False,
        "style_data": TABLE_STYLE_DATA,
        "style_header": TABLE_STYLE_HEADER,
        "style_cell": TABLE_STYLE_CELL,
        "style_filter": TABLE_STYLE_FILTER,
        "style_data_conditional": style_cell_conditional or [],
        "css": TABLE_CSS,
        "hidden_columns": hidden_columns,
        "tooltip_data": tooltip_data,
        "tooltip_duration": tooltip_duration,
        "active_cell": active_cell,
        **kwargs,
    }
    if id is not None:
        table_kwargs["id"] = id

    return dash_table.DataTable(**table_kwargs)

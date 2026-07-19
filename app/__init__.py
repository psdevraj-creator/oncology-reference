import dash


def create_app() -> dash.Dash:
    app = dash.Dash(
        __name__,
        external_stylesheets=["/assets/bootstrap.min.css", "/assets/bootstrap-icons.css"],
        suppress_callback_exceptions=True,
        title="Oncology Interactive Handbook",
        update_title=None,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        ],
    )

    # Register service worker for offline/cached repeat visits
    app.index_string = app.index_string.replace(
        "</head>",
        """<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/assets/service-worker.js');
  });
}
</script>
</head>""",
    )

    return app

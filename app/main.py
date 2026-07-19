from app import create_app
from app.callbacks import register_callbacks
from app.data import loader

app = create_app()

from app.layout import create_layout

app.layout = create_layout()
register_callbacks(app)

server = app.server

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)

import logging
import os
from pathlib import Path

from flask import Flask

from app.config import PROJECT_ROOT, DATA_DIR, DESKTOP_MODE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "app" / "templates"),
        static_folder=str(PROJECT_ROOT / "app" / "assets"),
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "oncology-handbook-dev")

    # Preload all data at startup
    logger.info("Preloading data...")
    from app.data.loader import load_all
    load_all()
    from app.data.loader import get_sites, get_regimens_df
    sites = get_sites()
    regimens_df = get_regimens_df()
    total_regimens = len(regimens_df)
    app.config["SITES"] = sites
    app.config["REGIMENS_DF"] = regimens_df
    app.config["TOTAL_REGIMENS"] = total_regimens
    app.config["SITES_BY_ID"] = {s["id"]: s for s in sites}
    logger.info("Loaded %d sites, %d regimens", len(sites), total_regimens)

    # Register routes
    from app.routes.home import home_bp
    from app.routes.disease import disease_bp
    from app.routes.regimens import regimens_bp
    app.register_blueprint(home_bp)
    app.register_blueprint(disease_bp)
    app.register_blueprint(regimens_bp)

    # Desktop shutdown route
    if DESKTOP_MODE:
        @app.route("/shutdown", methods=["POST"])
        def shutdown_server():
            func = app.config.get("SHUTDOWN_FUNC")
            if func:
                func()
            else:
                os._exit(0)
            return "OK"

    # Health check for Cloud Run
    @app.route("/healthz")
    def healthz():
        return "OK", 200

    @app.errorhandler(404)
    def not_found(_e):
        from flask import render_template
        return render_template("base.html", content="<h2>Page not found</h2><p><a href='/'>Back to home</a></p>"), 404

    @app.errorhandler(500)
    def server_error(_e):
        from flask import render_template
        return render_template("base.html", content="<h2>Server error</h2><p><a href='/'>Back to home</a></p>"), 500

    return app

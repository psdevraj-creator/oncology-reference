from flask import Blueprint, current_app, render_template
from app.data.loader import get_handbook, get_site, get_regimens_for_site, site_exists
from app.components.section_html import render_handbook, get_section_toc
from app.data.loader import load_all

disease_bp = Blueprint("disease", __name__)


@disease_bp.route("/disease/<site_id>")
def disease_page(site_id):
    if not site_exists(site_id):
        return render_template("base.html", content=f"<h2>Site not found</h2><p><a href='/'>Back to home</a></p>"), 404

    site = get_site(site_id)
    handbook = get_handbook(site_id)

    # Inject rewritten definition
    _inject_rewritten_definition(handbook, site_id)

    try:
        handbook_html = render_handbook(handbook, site_id)
    except Exception as e:
        current_app.logger.error("Failed to render handbook for %s: %s", site_id, e)
        handbook_html = f'<div class="alert alert-danger">Error rendering handbook: {e}</div>'

    toc = get_section_toc(handbook)
    regimen_count = len(get_regimens_for_site(site_id))

    return render_template(
        "disease.html",
        site=site,
        handbook_html=handbook_html,
        toc=toc,
        regimen_count=regimen_count,
    )


_REWRITTEN_DIR = None


def _inject_rewritten_definition(handbook: dict, site_id: str) -> None:
    global _REWRITTEN_DIR
    if _REWRITTEN_DIR is None:
        from pathlib import Path
        _REWRITTEN_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "rewritten"
    cache_path = _REWRITTEN_DIR / f"{site_id}_definition.json"
    if not cache_path.exists():
        return
    try:
        import json
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        if data.get("sections"):
            handbook["definition"] = data
    except (json.JSONDecodeError, OSError):
        pass

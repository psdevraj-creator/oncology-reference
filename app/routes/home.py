from flask import Blueprint, current_app, render_template, request
from app.data.category_map import SYSTEMS, group_sites_by_system, SITE_SYSTEM, get_system_for_site

home_bp = Blueprint("home", __name__)


def _search_sites(sites, query: str):
    if not query or not query.strip():
        return sites
    term = query.lower().strip()
    return [
        s for s in sites
        if term in s.get("display_name", "").lower()
        or term in s.get("description", "").lower()
        or term in s.get("id", "").lower()
        or term in (s.get("archetype", "") or "").lower()
    ]


def _build_stats():
    sites = current_app.config["SITES"]
    total_regimens = current_app.config.get("TOTAL_REGIMENS", sum(s.get("regimen_count", 0) for s in sites))
    return {
        "sites": len(sites),
        "regimens": total_regimens,
        "systems": len(SYSTEMS),
    }


@home_bp.route("/")
def index():
    sites = current_app.config["SITES"]
    grouped = group_sites_by_system(sites)
    stats = _build_stats()

    sorted_systems = sorted(SYSTEMS.items(), key=lambda x: x[1]["order"])

    category_sections = []
    for system_key, system_sites in grouped.items():
        sys_info = SYSTEMS.get(system_key, {})
        category_sections.append({
            "key": system_key,
            "name": sys_info.get("name", system_key),
            "icon": sys_info.get("icon", "bi-circle"),
            "color": sys_info.get("color", "#2563eb"),
            "sites": system_sites,
        })

    return render_template(
        "home.html",
        stats=stats,
        systems=sorted_systems,
        category_sections=category_sections,
        query="",
        active_system="all",
    )


@home_bp.route("/search")
def search():
    sites = current_app.config["SITES"]
    query = request.args.get("q", "").strip()
    active_system = request.args.get("system", "all")

    sites = _search_sites(sites, query)
    grouped = group_sites_by_system(sites)

    if active_system and active_system != "all":
        grouped = {k: v for k, v in grouped.items() if k == active_system}

    category_sections = []
    for system_key, system_sites in grouped.items():
        sys_info = SYSTEMS.get(system_key, {})
        category_sections.append({
            "key": system_key,
            "name": sys_info.get("name", system_key),
            "icon": sys_info.get("icon", "bi-circle"),
            "color": sys_info.get("color", "#2563eb"),
            "sites": system_sites,
        })

    resp = render_template(
        "partials/disease_cards.html",
        category_sections=category_sections,
        query=query,
    )
    resp = current_app.make_response(resp)
    resp.headers["HX-Push-Url"] = f"/search?q={query}&system={active_system}"
    return resp


"""Export Flask app as static HTML files for Hostinger deployment.

Output structure:
  Oncology topics page/deployment/
    Oncology.html              ← home page (Alpine search, no HTMX)
    Oncology/
      search-index.json        ← pre-built search data
      assets/styles.css        ← app styles
      disease/{site}/index.html   (41 sites)
      regimens/index.html         (master)
      regimens/{site}/index.html  (41 sites)
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

# Ensure we can import from the app
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from flask import Response as FlaskResponse

from app.server import create_app
from app.data.loader import get_sites, get_all_regimens
from app.config import SITES_REGISTRY_PATH

# ── Paths ─────────────────────────────────────────────────────────────
OUTPUT = Path(r"C:\Users\dpsri\OneDrive\Desktop\Educational webpage project\Oncology topics page\deployment")
ONC = OUTPUT / "Oncology"
ASSETS = ONC / "assets"
DISEASE = ONC / "disease"
REGIMENS = ONC / "regimens"

# ── Path rewriting ────────────────────────────────────────────────────
# Internal links in the app are absolute:  /regimens  /disease/breast
# In the static export they must be:       /Oncology/regimens/  /Oncology/disease/breast/
# The home page is at root as Oncology.html, not index.html.

_REWRITES = [
    (r'href="/regimens',  'href="/Oncology/regimens'),
    (r'href="/disease',   'href="/Oncology/disease'),
    (r'href="/static/',   'href="/Oncology/assets/'),
    (r'src="/static/',    'src="/Oncology/assets/'),
    (r'href="/"',         'href="/Oncology.html"'),
    # Regimen template's Alpine link to disease page uses string concat
    (r"'/disease/'",      "'/Oncology/disease/'"),
]


def rewrite_paths(html: str) -> str:
    for pattern, replacement in _REWRITES:
        html = re.sub(pattern, replacement, html)
    # Remove unused HTMX script tag (saves ~14 KB per page)
    html = re.sub(r'<script[^>]*unpkg\.com/htmx[^>]*></script>', '', html)
    return html


# ── Home page: replace HTMX search with Alpine + search-index ─────────
_HOME_SCRIPT = """<script>
document.addEventListener("DOMContentLoaded", function() {
  var SITES = %s;
  var searchInput = document.getElementById("home-search");
  var gridContainer = document.getElementById("disease-grid-container");
  var filterStrip = document.getElementById("filter-strip");
  var activeSystem = "all";
  var searchQ = "";

  function filter() {
    var q = searchQ.toLowerCase().trim();
    // Show/hide category sections and individual cards
    var sections = document.querySelectorAll(".category-section");
    sections.forEach(function(sec) {
      var sys = sec.getAttribute("data-system") || "";
      if (activeSystem !== "all" && sys !== activeSystem) {
        sec.style.display = "none";
        return;
      }
      var cards = sec.querySelectorAll(".disease-card");
      var visibleCount = 0;
      cards.forEach(function(card) {
        var kw = (card.getAttribute("data-keywords") || "").toLowerCase();
        var dn = (card.getAttribute("data-name") || "").toLowerCase();
        var match = !q || kw.indexOf(q) !== -1 || dn.indexOf(q) !== -1;
        card.style.display = match ? "" : "none";
        if (match) visibleCount++;
      });
      sec.style.display = visibleCount > 0 ? "" : "none";
    });
  }

  // Search input
  if (searchInput) {
    searchInput.addEventListener("input", function() {
      searchQ = this.value;
      filter();
    });
  }

  // Filter pills
  if (filterStrip) {
    filterStrip.addEventListener("click", function(e) {
      var pill = e.target.closest(".filter-pill");
      if (!pill) return;
      var val = pill.getAttribute("data-value") || "all";
      activeSystem = val === "all" ? "all" : val;
      filterStrip.querySelectorAll(".filter-pill").forEach(function(p) {
        p.classList.toggle("active", p === pill || (val === "all" && p.classList.contains("all-pill")));
      });
    });
  }
});
</script>"""


def _build_search_index():
    sites = get_sites()
    from app.data.category_map import get_system_for_site
    return [
        {
            "id": s["id"],
            "display_name": s["display_name"],
            "description": s.get("description", ""),
            "archetype": s.get("archetype", ""),
            "system": get_system_for_site(s["id"]),
        }
        for s in sites
    ]


def _add_cloudrun_placeholder(html: str) -> str:
    placeholder = """<div class="text-center py-4 mt-4 border-top">
  <p class="text-muted small mb-2">Need interactive features? Try the full version &mdash; filter regimens by drug/dose/line, collapse &amp; search handbook sections, and more.</p>
  <a href="https://CLOUD_RUN_URL" class="btn btn-primary btn-lg">
    <i class="bi bi-cloud-arrow-up"></i> Launch Interactive Version
  </a>
</div>"""
    # Insert before closing </main>
    html = html.replace("</main>", placeholder + "\n</main>")
    return html


def _transform_home_page(html: str, search_index: list) -> str:
    # 1. Remove HTMX attributes from search input
    html = re.sub(r'\s*hx-[a-z-]+="[^"]*"', "", html)

    # 2. Remove hx-indicator spinner (HTMX specific)
    html = re.sub(r'<div id="search-spinner"[^>]*>.*?</div>', "", html)

    # 3. Inject Alpine search script with search index data
    script = _HOME_SCRIPT % json.dumps(search_index, indent=1)
    html = html.replace("</body>", script + "\n</body>")

    # 4. Add Cloud Run placeholder
    html = _add_cloudrun_placeholder(html)

    return html


# ── Main export ──────────────────────────────────────────────────────
def export():
    app = create_app()
    sites = get_sites()

    # Create output directories
    ASSETS.mkdir(parents=True, exist_ok=True)
    DISEASE.mkdir(parents=True, exist_ok=True)
    REGIMENS.mkdir(parents=True, exist_ok=True)

    with app.test_client() as client:
        existing = set(s["id"] for s in sites)

        # ── Copy static assets ──
        src_css = Path(r"C:\Users\dpsri\OneDrive\Desktop\Educational webpage project\interactive-oncology-app\app\assets\styles.css")
        if src_css.exists():
            shutil.copy2(str(src_css), str(ASSETS / "styles.css"))
            print("  assets/styles.css ✓")

        # ── Write search-index.json ──
        search_index = _build_search_index()
        (ONC / "search-index.json").write_text(
            json.dumps(search_index, indent=1), encoding="utf-8"
        )
        print("  search-index.json ✓")

        # ── Home page ──
        resp = client.get("/")
        html = resp.data.decode("utf-8")
        html = rewrite_paths(html)
        html = _transform_home_page(html, search_index)
        (OUTPUT / "Oncology.html").write_text(html, encoding="utf-8")
        print("  Oncology.html ✓")

        # ── Disease pages ──
        for s in sites:
            sid = s["id"]
            resp = client.get(f"/disease/{sid}")
            if resp.status_code != 200:
                print(f"  disease/{sid} -> {resp.status_code} SKIP")
                continue
            html = resp.data.decode("utf-8")
            html = rewrite_paths(html)
            out_dir = DISEASE / sid
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "index.html").write_text(html, encoding="utf-8")
            print(f"  disease/{sid}/index.html ✓")

        # ── Master regimens page ──
        resp = client.get("/regimens")
        if resp.status_code == 200:
            html = resp.data.decode("utf-8")
            html = rewrite_paths(html)
            (REGIMENS / "index.html").write_text(html, encoding="utf-8")
            print("  regimens/index.html ✓")
        else:
            print(f"  regimens/ -> {resp.status_code} SKIP")

        # ── Per-site regimen pages ──
        for s in sites:
            sid = s["id"]
            resp = client.get(f"/regimens/{sid}")
            if resp.status_code != 200:
                print(f"  regimens/{sid} -> {resp.status_code} SKIP")
                continue
            html = resp.data.decode("utf-8")
            html = rewrite_paths(html)
            out_dir = REGIMENS / sid
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "index.html").write_text(html, encoding="utf-8")
            print(f"  regimens/{sid}/index.html ✓")

    # ── Summary ──
    total_size = sum(f.stat().st_size for f in OUTPUT.rglob("*") if f.is_file())
    print(f"\nDone. {total_size / 1024 / 1024:.1f} MB written to {OUTPUT}")
    print(f"  Oncology.html — root landing page (replaces old)")
    print(f"  Oncology/ — {len(sites)} disease pages, 2 regimen pages, assets, search-index")


if __name__ == "__main__":
    export()

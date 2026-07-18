#!/usr/bin/env python3
"""
Enrich HTML — Inject PubMed data into source project's per-site HTML pages.

Reads the PubMed cache (data/pubmed/*.json), matches trial names against
regimens in {site}_data.json, enriches both the JSON and the inline JS
in each {site}.html to render PubMed badges, citations, and abstracts.

Usage:
    python enrich_html.py                          # Process all 41 sites
    python enrich_html.py --site biliary           # Single site
    python enrich_html.py --dry-run                # Preview only
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
PUBMED_DIR = SCRIPT_DIR / "data" / "pubmed"
SOURCE_DIR = Path(r"C:\Users\dpsri\OneDrive\Desktop\Educational webpage project\Oncology topics page\deployment\Oncology")


def load_pubmed_cache() -> dict[str, dict]:
    cache = {}
    if not PUBMED_DIR.exists():
        print(f"PubMed dir not found: {PUBMED_DIR}")
        return cache
    for f in PUBMED_DIR.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            name = (data.get("trial_name", "") or "").strip()
            if name:
                key = _normalize(name)
                cache[key] = data
        except Exception:
            pass
    return cache


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())


def _fuzzy_match(trial_name: str, cache: dict[str, dict]) -> Optional[dict]:
    if not trial_name:
        return None
    name = trial_name.strip()
    keys_to_try = [_normalize(name)]

    paren = name.find("(")
    if paren > 0:
        keys_to_try.append(_normalize(name[:paren].strip()))

    words = name.split()
    for n in range(min(3, len(words)), 0, -1):
        short = " ".join(words[:n]).strip().rstrip(",").rstrip(".")
        if len(short) >= 3:
            keys_to_try.append(_normalize(short))

    seen = set()
    for k in keys_to_try:
        if k in seen:
            continue
        seen.add(k)
        if k in cache:
            return cache[k]

    parts = re.split(r"[\s\-_/]+", name.lower())
    if len(parts) > 1 and len(parts[0]) >= 3:
        for k, v in cache.items():
            if parts[0] in k:
                return v

    return None


def enrich_data_json(site_path: Path, cache: dict[str, dict], dry_run: bool = False) -> int:
    data_path = site_path / "data" / f"{site_path.name}_data.json"
    if not data_path.exists():
        print(f"  [SKIP] No data file: {data_path}")
        return 0

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    matched = 0
    regimens = data.get("regimens", [])
    for r in regimens:
        td = r.get("trial_data")
        if not isinstance(td, dict):
            continue
        trial_name = (td.get("trial_name") or "").strip()
        if not trial_name:
            continue

        pubmed = _fuzzy_match(trial_name, cache)
        if not pubmed:
            continue

        td["pmid"] = pubmed.get("pmid", "")

        title = pubmed.get("title", "")
        journal = pubmed.get("journal", "")
        year = pubmed.get("year", "")
        doi = pubmed.get("doi", "")
        authors_list = pubmed.get("authors", [])
        authors = ", ".join(authors_list[:3])
        if len(authors_list) > 3:
            authors += " et al."

        citation_parts = [authors, f'"{title}"', f"{journal} ({year})"]
        td["pubmed_citation"] = ". ".join(p for p in citation_parts if p)

        abstract = pubmed.get("abstract", "")
        if abstract:
            td["pubmed_abstract"] = abstract

        if doi:
            td["pubmed_doi"] = doi

        matched += 1

    if matched > 0:
        new_refs = dict(data.get("references", {}))
        for r in regimens:
            td = r.get("trial_data")
            if not isinstance(td, dict):
                continue
            if td.get("pmid") and td.get("pubmed_citation"):
                citation_key = f"pubmed_{td['pmid']}"
                if citation_key not in new_refs:
                    new_refs[citation_key] = td["pubmed_citation"]
        data["references"] = new_refs

    if not dry_run and matched > 0:
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return matched


APA_CSS = """
.pubmed-inline { margin: 6px 0 0; padding: 8px 10px; background: #f0f7fa; border-radius: 8px; font-size: 0.82rem; line-height: 1.45; }
.pubmed-inline a { color: #1a5276; font-weight: 600; text-decoration: none; }
.pubmed-inline a:hover { text-decoration: underline; }
.pubmed-cite { display: block; color: #666; font-size: 0.78rem; margin-top: 3px; }
.pubmed-abstract { margin: 6px 0 0; }
.pubmed-abstract summary { cursor: pointer; color: #2c7ba0; font-weight: 600; font-size: 0.82rem; }
.pubmed-abstract p { margin: 5px 0 0; font-size: 0.8rem; line-height: 1.5; color: #555; }
"""

PUBMED_JS_CALL = (
    'pubmedHtml'
)


def _inject_pubmed_js(html: str) -> str:
    js_already_injected = "pubmedHtml" in html

    if not js_already_injected:
        old_pattern = "toxHtml + relevanceHtml +\n        '</div>';"
        if old_pattern in html:
            injection = (
                "toxHtml + relevanceHtml +\n"
                "        pubmedHtml +\n"
                "        '</div>';"
            )
            html = html.replace(old_pattern, injection)
        else:
            return html

    def_var = "var toxHtml = '';"
    if def_var in html and "var pubmedHtml" not in html:
        pubmed_func = (
            def_var + "\n"
            "      var pubmedHtml = (tD && tD.pmid) ?\n"
            "        '<div class=\"pubmed-inline\"><a href=\"https://pubmed.ncbi.nlm.nih.gov/' + tD.pmid + '/\" target=\"_blank\" rel=\"noopener\">PubMed: ' + tD.pmid + '</a>' +\n"
            "        (tD.pubmed_citation ? '<span class=\"pubmed-cite\">' + tD.pubmed_citation + '</span>' : '') +\n"
            "        (tD.pubmed_abstract ? '<details class=\"pubmed-abstract\"><summary>Abstract</summary><p>' + tD.pubmed_abstract.substring(0,600) + (tD.pubmed_abstract.length > 600 ? \"...\" : \"\") + '</p></details>' : '') +\n"
            "        '</div>' : '';\n"
        )
        html = html.replace(def_var, pubmed_func, 1)

    if APA_CSS not in html:
        style_close = html.find("</style>")
        if style_close > 0:
            html = html[:style_close] + APA_CSS + "\n" + html[style_close:]

    return html


def enrich_html_file(site_path: Path, cache: dict[str, dict], dry_run: bool = False) -> bool:
    html_path = site_path / f"{site_path.name}.html"
    if not html_path.exists():
        print(f"  [SKIP] No HTML file: {html_path}")
        return False

    with open(html_path, encoding="utf-8", errors="replace") as f:
        html = f.read()

    if "pubmedHtml" in html and "pubmed-inline" in html:
        return False

    updated = _inject_pubmed_js(html)

    if updated == html:
        print(f"  [WARN] Could not inject PubMed JS into {html_path.name}")
        return False

    if not dry_run:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(updated)

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Inject PubMed data into source HTML regimen pages")
    parser.add_argument("--site", type=str, default=None, help="Process single site (e.g. biliary)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    if not SOURCE_DIR.exists():
        print(f"ERROR: Source dir not found: {SOURCE_DIR}")
        sys.exit(1)

    print("Loading PubMed cache...")
    cache = load_pubmed_cache()
    print(f"  {len(cache)} cached PubMed entries loaded")

    site_dirs = [args.site] if args.site else sorted(d.name for d in SOURCE_DIR.iterdir()
                                                      if d.is_dir() and (d / "data").exists()
                                                      and not d.name.startswith(".") and d.name != "css" and d.name != "js")

    total_json = 0
    total_html = 0
    total_matched = 0

    for site_id in site_dirs:
        site_path = SOURCE_DIR / site_id
        tag = "[DRY-RUN] " if args.dry_run else ""
        matched = enrich_data_json(site_path, cache, args.dry_run)
        html_updated = enrich_html_file(site_path, cache, args.dry_run)

        if matched > 0 or html_updated:
            print(f"  {tag}{site_id}: {matched} regimen matches, HTML {'updated' if html_updated else 'unchanged'}")
        total_matched += matched
        if matched > 0:
            total_json += 1
        if html_updated:
            total_html += 1

    print()
    print(f"{'[DRY-RUN] ' if args.dry_run else ''}Done. {total_matched} regimen-trial matches across {total_json} sites.")
    print(f"  JSON enriched: {total_json} sites")
    print(f"  HTML patched:  {total_html} sites")

    if total_html > 0 and not args.dry_run:
        print()
        print("To see changes: open any deployment/Oncology/{site}/{site}.html in a browser.")
        print("Regimen trial cards will now show PubMed badges, citations, and collapsible abstracts.")


if __name__ == "__main__":
    main()

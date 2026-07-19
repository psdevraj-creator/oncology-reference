"""
Clinical Overview HTML Generator
Reads enriched section JSONs (from section_rewriter.py) for a site and
generates a complete, styled HTML block for the Clinical Overview tab.
Self-contained: inline CSS, no SVG, no external deps.

Usage:
    python -m app.data.overview_generator --site hepatobiliary  # print HTML
    python -m app.data.overview_generator --site hepatobiliary --out overview.html
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

SOURCE_PROJECT = Path(__file__).resolve().parent.parent.parent.parent / "Oncology topics page"
load_dotenv(dotenv_path=str(SOURCE_PROJECT / ".env"), override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SECTIONS_DIR = PROJECT_ROOT / "data" / "rewritten" / "sections"

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL") or os.environ.get("LLM_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")

_SKIP_KEYS = {"_section", "_site_id", "_model", "_original_chars", "_chars_in"}

OVERVIEW_CACHE_DIR = SECTIONS_DIR / "__overview_cache__"

SECTION_LABELS = {
    "clinical_features": "Clinical Features",
    "clinical_pearls": "Clinical Pearls",
    "complications": "Complications & Toxicities",
    "epidemiology": "Epidemiology",
    "follow_up": "Follow-Up & Surveillance",
    "management_pathways": "Management Pathways",
    "management_principles": "Management Principles",
    "molecular_pathogenesis": "Molecular Pathogenesis",
    "prognosis": "Prognosis",
    "radiation_therapy": "Radiation Therapy",
    "risk_factors": "Risk Factors",
    "staging": "Staging & TNM Classification",
    "surgery": "Surgery",
    "surveillance": "Surveillance",
    "systemic_therapy": "Systemic Therapy",
    "definition": "Definition & Classification",
    "pathology": "Pathology",
    "diagnosis": "Diagnosis & Workup",
    "treatment_guidelines": "Treatment Guidelines",
    "special_situations": "Special Situations",
    "supportive_care": "Supportive Care",
    "protective_factors": "Protective Factors",
    "pretreatment_evaluation": "Pretreatment Evaluation",
    "investigations": "Investigations",
    "red_flags": "Red Flags",
    "subtypes": "Subtypes",
    "guidelines_resources": "Guidelines & Resources",
    "treatment_response_assessment": "Treatment Response Assessment",
    "clinical_overview": "Clinical Overview",
}

SECTION_ORDER = [
    "definition", "clinical_overview", "clinical_features",
    "epidemiology", "risk_factors", "protective_factors", "molecular_pathogenesis", "subtypes", "pathology",
    "staging", "diagnosis", "investigations", "red_flags",
    "management_principles", "treatment_guidelines", "management_pathways",
    "pretreatment_evaluation", "systemic_therapy", "radiation_therapy", "surgery",
    "treatment_response_assessment", "surveillance", "follow_up", "prognosis",
    "complications", "supportive_care", "clinical_pearls", "special_situations",
    "guidelines_resources",
]


def _unwrap_stringified_json(obj):
    """Recursively find and unwrap stringified JSON in sections[].content fields.
    The section_rewriter occasionally double-encodes dicts as JSON strings."""
    if isinstance(obj, dict):
        if "content" in obj and isinstance(obj["content"], str) and obj["content"].strip().startswith("{"):
            try:
                parsed = json.loads(obj["content"])
                if isinstance(parsed, dict):
                    obj["_parsed_content"] = parsed
                    obj["content"] = parsed.get("role") or parsed.get("overview") or parsed.get("description") or obj["content"]
            except (json.JSONDecodeError, ValueError):
                pass
        for key, val in obj.items():
            _unwrap_stringified_json(val)
    elif isinstance(obj, list):
        for item in obj:
            _unwrap_stringified_json(item)


_LAZY_PATTERNS = [
    "the source text does not", "the provided source text does not contain",
    "not specified in the source text", "not provided in the source text",
    "not detailed in the source text", "does not detail",
    "does not provide", "does not contain specific",
    "no specific data was provided", "no specific information",
]


def _filter_lazy_content(obj):
    """Recursively replace lazy/empty LLM content with empty string."""
    if isinstance(obj, dict):
        for key in ("content", "body", "detail", "description"):
            if key in obj and isinstance(obj[key], str):
                text_lower = obj[key].lower()
                if any(p in text_lower for p in _LAZY_PATTERNS):
                    obj[key] = ""
                elif len(obj[key].strip()) < 80 and key in ("body", "description"):
                    obj[key] = ""
        for key, val in obj.items():
            _filter_lazy_content(val)
    elif isinstance(obj, list):
        for item in obj:
            _filter_lazy_content(item)


def load_site_data(site_id: str) -> dict:
    """Load all enriched section JSONs for a site, stripped of metadata keys."""
    site_dir = SECTIONS_DIR / site_id
    if not site_dir.is_dir():
        return {}
    result = {}
    for jf in sorted(site_dir.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for k in _SKIP_KEYS:
            data.pop(k, None)
        _unwrap_stringified_json(data)
        _filter_lazy_content(data)
        section_name = jf.stem
        result[section_name] = data
    return result


def _build_prompt(site_id: str, data: dict) -> str:
    """Build the system prompt for the LLM."""
    section_list = []
    for key in SECTION_ORDER:
        if key in data:
            section_list.append(key)
    for key in data:
        if key not in section_list:
            section_list.append(key)

    sections_prompt = ""
    for sk in section_list:
        label = SECTION_LABELS.get(sk, sk.replace("_", " ").title())
        sections_prompt += f"\n\n=== {label} (key: {sk}) ===\n"
        sections_prompt += json.dumps(data[sk], ensure_ascii=False, indent=2)

    return f"""You are generating the Clinical Overview HTML for {site_id} cancer page. You have structured data for each section below.

Generate a complete, styled HTML block for the clinical overview content. Rules:

1. **No <html>, <head>, or <body> tags** — just the content block.
2. **Inline CSS only** in a single <style> tag at the top. Use a dark blue accent (#1e3a5f) with light backgrounds.
3. **No SVG, no canvas, no Chart.js** — use pure CSS/HTML for all visualizations:
   - For chart-like data (epidemiology chart_data, prognosis chart, complications chart_data, waterfall data): use CSS bar charts — <div> elements with width percentages and background colors.
   - For network data: render as a two-column HTML table (Gene/Pathway | Type).
   - For flowcharts: render as a step-by-step decision tree using nested <details>/<summary> elements or an indented list with decision → treatment flow.
   - For timelines: render as an HTML table with columns: Step, Details, Notes.
   - For cards: render as a CSS grid of styled cards.
   - For all other structured data: HTML tables.
4. **Preserve EVERY word** from `sections[].content` verbatim in prose paragraphs. Do not summarize, truncate, or rewrite.
5. **Handle `_parsed_content`**: Some sections have a `_parsed_content` object (from preprocessing). If present, use its keys to render richer content — render `.role` as prose, `.principles` as a bullet list, `.dose_frameworks` as a table, `.approaches` as cards. Ignore the raw JSON string in `content` if `_parsed_content` exists.
6. **Handle missing/empty data gracefully**: If a section has empty or very short content, show only a subtle italic note: "Detailed information not available in source." at the top of the section, and do NOT render empty prose divs, empty card grids, or empty tables. If `sections` array items have empty `content`, skip rendering the prose entirely for that item.
6. **Section structure**: Each section must be wrapped in `<section id="ov-{key}" class="ov-section">` with an `<h2 class="ov-heading">` for the section title.
7. **Consistent pattern per section type**:
   - `sections[].content` → rendered as `.ov-prose` paragraphs (verbatim)
   - `chart_data` with labels/values → CSS bar chart
   - `waterfall` with labels/values/types → CSS horizontal bar chart grouped by type
   - `network` with nodes/edges/summaries → HTML table (Gene | Type | Pathway | Targetable)
   - `flowchart` or `flowcharts` → nested <details> decision tree
   - `timeline` items → HTML table with Title, Body/Details, Icon columns
   - `cards` or `symptom_cards` or `complication_cards` or `protocol_cards` → CSS grid of .ov-cards
   - `factors` → HTML table (Factor | Impact | Detail)
   - `t_stages` / `n_stages` / `m_stages` / `stage_groups` → HTML staging tables
   - `table_data` with columns/rows → HTML table
   - `alerts` with title/body → styled alert cards
   - `stat_cards` with label/value → stat card grid
   - `gauges` with label/value/unit → simple property list
   - `groups` with category/items → grouped cards
   - `dose_timeline` → HTML table
   - `late_effects` → card grid
   - `schedule_table` → HTML table
8. **Output ONLY the HTML**. No markdown fences, no code block markers, no explanations.

Data for {site_id}:
{sections_prompt}"""


def _call_llm(prompt: str, site_id: str) -> str | None:
    if not DEEPSEEK_KEY:
        print(f"  [overview] SKIP {site_id}: No API key")
        return None
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url=DEEPSEEK_BASE)
    for attempt in range(1, 4):
        print(f"  Calling DeepSeek for overview ({site_id}) attempt {attempt}/3...")
        try:
            resp = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "You are a clinical oncology HTML generator. Output only valid HTML."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=16384,
                temperature=0.1,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else parts[-1]
                if raw.startswith("html"):
                    raw = raw[4:]
                raw = raw.strip()
            return raw
        except Exception as e:
            print(f"  [ERR] {site_id}: {e}")
            if attempt < 3:
                import time
                time.sleep(5)
    return None


def _generate_fallback_html(data: dict) -> str:
    """Generate a simple HTML overview without LLM (fallback if API fails)."""
    html = '<style>.ov-fallback { font-family: Inter, sans-serif; color: #1e3a5f; } .ov-fallback .ov-section { margin-bottom: 1.5rem; } .ov-fallback .ov-heading { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; } .ov-fallback .ov-prose { line-height: 1.6; color: #374151; } .ov-fallback table { width: 100%; border-collapse: collapse; margin: 0.5rem 0; } .ov-fallback th, .ov-fallback td { border: 1px solid #d1d5db; padding: 0.4rem 0.6rem; text-align: left; font-size: 0.85rem; } .ov-fallback th { background: #1e3a5f; color: white; } .ov-fallback .ov-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; } .ov-fallback .ov-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 0.75rem; } .ov-fallback .ov-card-title { font-weight: 600; font-size: 0.9rem; color: #1e3a5f; } .ov-fallback .ov-card-detail { font-size: 0.85rem; color: #374151; margin-top: 0.3rem; }</style><div class="ov-fallback">'
    for key in SECTION_ORDER:
        if key not in data:
            continue
        label = SECTION_LABELS.get(key, key.replace("_", " ").title())
        sec = data[key]
        html += f'<section class="ov-section" id="ov-{key}"><h2 class="ov-heading">{label}</h2>'

        if "sections" in sec and isinstance(sec["sections"], list):
            for s in sec["sections"]:
                if s.get("heading"):
                    html += f'<h3 class="ov-subheading">{s["heading"]}</h3>'
                content = s.get("content", "")
                if content and len(content) > 50 and "not detail" not in content.lower() and "not contain" not in content.lower() and "not specified" not in content.lower():
                    html += f'<div class="ov-prose">{content}</div>'
                elif content:
                    html += '<div class="ov-prose"><em>Detailed information not available in source.</em></div>'

        if "cards" in sec and isinstance(sec["cards"], list) and sec["cards"]:
            html += '<div class="ov-cards">'
            for c in sec["cards"]:
                title = c.get("name") or c.get("factor") or c.get("title") or ""
                detail = c.get("detail") or c.get("description") or ""
                html += f'<div class="ov-card"><div class="ov-card-title">{title}</div>'
                if detail:
                    html += f'<div class="ov-card-detail">{detail}</div>'
                html += '</div>'
            html += '</div>'

        if "timeline" in sec and isinstance(sec["timeline"], list) and sec["timeline"]:
            html += '<table><thead><tr><th>Step</th><th>Details</th></tr></thead><tbody>'
            for t in sec["timeline"]:
                html += f'<tr><td>{t.get("title", "")}</td><td>{t.get("body", t.get("detail", ""))}</td></tr>'
            html += '</tbody></table>'

        if "factors" in sec and isinstance(sec["factors"], list) and sec["factors"]:
            html += '<table><thead><tr><th>Factor</th><th>Impact</th><th>Detail</th></tr></thead><tbody>'
            for f in sec["factors"]:
                html += f'<tr><td>{f.get("factor", "")}</td><td>{f.get("impact", "")}</td><td>{f.get("detail", "")}</td></tr>'
            html += '</tbody></table>'

        html += '</section>'
    html += '</div>'
    return html


def _cache_path(site_id: str) -> Path:
    return OVERVIEW_CACHE_DIR / f"{site_id}.html"


def _cache_valid(site_id: str) -> bool:
    """Check if cached overview is newer than all source JSON files."""
    cache = _cache_path(site_id)
    if not cache.exists():
        return False
    cache_mtime = cache.stat().st_mtime
    site_dir = SECTIONS_DIR / site_id
    if not site_dir.is_dir():
        return False
    for jf in site_dir.glob("*.json"):
        if jf.stat().st_mtime > cache_mtime:
            return False
    return True


def generate_overview_html(site_id: str, force: bool = False) -> str:
    """Main entry: load enriched data, call LLM, return HTML block.
    Caches result to avoid repeated API calls.
    Falls back to basic rendering if LLM call fails."""
    # Check cache first
    if not force and _cache_valid(site_id):
        try:
            return _cache_path(site_id).read_text(encoding="utf-8")
        except OSError:
            pass

    data = load_site_data(site_id)
    if not data:
        return '<div class="overview-empty"><p>No clinical overview data available for this site.</p></div>'

    prompt = _build_prompt(site_id, data)
    html = _call_llm(prompt, site_id)
    if not html:
        print(f"  [overview] LLM call failed, using fallback for {site_id}")
        html = _generate_fallback_html(data)

    # Write cache
    try:
        OVERVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(site_id).write_text(html, encoding="utf-8")
    except OSError as _e:
        pass

    return html


def invalidate_cache(site_id: str | None = None):
    """Remove cached overview HTML for a site (or all sites)."""
    if site_id:
        p = _cache_path(site_id)
        if p.exists():
            p.unlink()
    else:
        import shutil as _sh
        if OVERVIEW_CACHE_DIR.is_dir():
            _sh.rmtree(OVERVIEW_CACHE_DIR)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate clinical overview HTML for a site")
    parser.add_argument("--site", required=True, help="Site ID (e.g. hepatobiliary)")
    parser.add_argument("--out", help="Output file path (optional; prints to stdout if omitted)")
    parser.add_argument("--force", action="store_true", help="Ignore cache, regenerate")
    parser.add_argument("--invalidate-cache", action="store_true", help="Delete cache for this site")
    args = parser.parse_args()

    if args.invalidate_cache:
        invalidate_cache(args.site)
        print(f"Cache invalidated for {args.site}")
        return

    html = generate_overview_html(args.site, force=args.force)
    if args.out:
        Path(args.out).write_text(html, encoding="utf-8")
        print(f"Written: {args.out}")
    else:
        print(html)


if __name__ == "__main__":
    main()

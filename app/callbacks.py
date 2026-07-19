from __future__ import annotations

import os as _os

import pandas as pd
from dash import ClientsideFunction, Input, Output, State, html

from app.components.cards import category_sections
from app.data.category_map import group_sites_by_system
from app.data.loader import (
    get_regimens_for_site,
    get_sites,
    site_exists,
)
from app.data.transforms import extract_trial_outcomes
from app.pages import disease, home, regimens, trials


def register_callbacks(app) -> None:

    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
    )
    def render_page(pathname: str | None):
        if not pathname or pathname == "/":
            return home.layout()

        if pathname.startswith("/disease/"):
            site_id = pathname.split("/disease/", 1)[-1].rstrip("/")
            if site_id:
                return disease.layout(site_id)

        if pathname.startswith("/regimens/"):
            site_id = pathname.split("/regimens/", 1)[-1].rstrip("/")
            if site_id:
                return regimens.layout(site_id)
            return regimens.layout()

        if pathname.startswith("/trials/"):
            site_id = pathname.split("/trials/", 1)[-1].rstrip("/")
            if site_id:
                return trials.layout(site_id)
            return trials.layout()

        return home.layout()

    @app.callback(
        Output("disease-grid-container", "children"),
        Input("home-search", "value"),
        Input("quick-jump", "value"),
    )
    def filter_cards(search_term: str | None, active_system: str):
        sites = get_sites()
        if search_term and search_term.strip():
            term = search_term.lower().strip()
            sites = [
                s for s in sites
                if term in s["display_name"].lower()
                or term in s.get("description", "").lower()
                or term in s["id"].lower()
                or term in (s.get("archetype") or "").lower()
            ]
        grouped = group_sites_by_system(sites)
        if active_system and active_system != "all":
            grouped = {k: v for k, v in grouped.items() if k == active_system}
        return category_sections(grouped)

    # ── Clientside: filter regimens in browser from dcc.Store ───
    app.clientside_callback(
        ClientsideFunction(namespace="regimen", function_name="filter"),
        Output("regimen-table", "data"),
        Input("regimen-store", "data"),
        Input("setting-filter", "value"),
        Input("modality-filter", "value"),
        Input("biomarker-filter", "value"),
        Input("regimen-search", "value"),
    )

    @app.callback(
        Output("regimen-detail", "children"),
        Input("regimen-table", "selected_rows"),
        Input("regimen-table", "data"),
        State("url", "pathname"),
    )
    def show_regimen_detail(selected_rows, table_data, pathname):
        if not selected_rows or not table_data:
            return html.P("Select a regimen row to see details.", className="text-muted")

        row_idx = selected_rows[0]
        if row_idx >= len(table_data):
            return ""

        row = table_data[row_idx]
        regimen_name = row.get("regimen_name", "")

        site_id = None
        if pathname and pathname.startswith("/regimens/"):
            parts = pathname.split("/regimens/", 1)
            if len(parts) > 1 and parts[1]:
                site_id = parts[1].rstrip("/")

        if site_id and site_exists(site_id):
            df = get_regimens_for_site(site_id)
        else:
            df = get_regimens_df()

        match = df[df["regimen_name"] == regimen_name]
        if match.empty:
            return ""
        regimen = match.iloc[0]

        import dash_bootstrap_components as dbc
        from dash import dcc
        from app.components.trial_viz import render_trial_outcomes_comparison
        from app.data.loader import get_pubmed_data

        components = [
            html.H4(regimen_name),
            html.Hr(),
        ]

        setting = regimen.get("setting")
        if setting and pd.notna(setting):
            components.append(html.P([html.Strong("Setting: "), str(setting)]))

        modality = regimen.get("treatment_modality")
        if isinstance(modality, list) and modality:
            components.append(html.P([html.Strong("Modality: "), ", ".join(modality)]))

        guideline = regimen.get("guideline_category")
        if guideline and pd.notna(guideline):
            components.append(dbc.Badge(str(guideline), color="info", className="me-2"))

        evidence = regimen.get("evidence_level")
        if evidence and pd.notna(evidence):
            components.append(dbc.Badge(str(evidence), color="secondary", className="me-2"))

        drugs = regimen.get("drugs")
        if isinstance(drugs, list) and drugs:
            components.append(html.H6("Drug Regimen", className="mt-3"))
            drug_rows = []
            for d in drugs:
                if not isinstance(d, dict):
                    continue
                drug_rows.append(html.Tr([
                    html.Td(html.Strong(d.get("name", ""))),
                    html.Td(d.get("dose", "")),
                    html.Td(d.get("route", "")),
                    html.Td(d.get("schedule", "")),
                ]))
            components.append(dbc.Table(
                [html.Thead(html.Tr([html.Th("Drug"), html.Th("Dose"), html.Th("Route"), html.Th("Schedule")]))]
                + [html.Tbody(drug_rows)],
                bordered=True, hover=True, size="sm",
            ))

        biomarkers = regimen.get("biomarkers")
        if isinstance(biomarkers, list) and biomarkers:
            components.append(html.H6("Biomarkers", className="mt-3"))
            bio_items = []
            for b in biomarkers:
                if not isinstance(b, dict):
                    continue
                req_text = f": {b.get('requirement', '')}" if b.get("requirement") else ""
                mandatory = " (mandatory)" if b.get("mandatory") else ""
                bio_items.append(html.Li([
                    html.Strong(b.get("marker", "")),
                    html.Span(req_text + mandatory),
                ]))
            components.append(html.Ul(bio_items))

        trial_data = regimen.get("trial_data")
        if isinstance(trial_data, dict) and trial_data.get("trial_name"):
            components.append(html.H6("Pivotal Trial Evidence", className="mt-3"))

            pubmed = get_pubmed_data(str(trial_data.get("trial_name", "")))
            if pubmed and pubmed.get("pmid"):
                components.append(html.A(
                    dbc.Badge(f"PubMed: {pubmed.get('pmid')}", color="success"),
                    href=f"https://pubmed.ncbi.nlm.nih.gov/{pubmed['pmid']}",
                    target="_blank",
                    className="text-decoration-none mb-2 d-inline-block",
                ))

            comparison = render_trial_outcomes_comparison(trial_data)
            if comparison.children:
                components.append(comparison)
            else:
                components.append(html.P([
                    html.Strong(str(trial_data.get("trial_name", ""))),
                    f" — Phase {trial_data.get('phase', '?')}, N={trial_data.get('n_patients', '?')}"
                    if trial_data.get("phase") else "",
                ]))

        notes = regimen.get("notes")
        if notes and pd.notna(notes):
            components.append(html.H6("Clinical Notes", className="mt-3"))
            components.append(dcc.Markdown(str(notes)))

        return html.Div(components, className="regimen-detail-panel p-3 bg-light rounded")

    @app.callback(
        Output("pubmed-search-results", "children"),
        Output("pubmed-search-status", "children"),
        Input("pubmed-search-btn", "n_clicks"),
        State("pubmed-search-input", "value"),
        prevent_initial_call=True,
    )
    def search_pubmed_live(n_clicks, query):
        if not query or not query.strip():
            return [], ""

        import json as _json
        import re as _re

        try:
            import requests
        except ImportError:
            return [], html.P("requests not available.", className="text-danger small")

        api_key = _os.environ.get("NCBI_API_KEY", "")
        term = query.strip()
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": f"({term}) AND (cancer OR carcinoma OR tumor OR neoplasm OR chemotherapy OR radiotherapy OR trial)",
            "retmax": "10",
            "retmode": "json",
            "sort": "relevance",
        }
        if api_key:
            params["api_key"] = api_key

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            ids = data.get("esearchresult", {}).get("idlist", [])
        except Exception:
            return [], html.P("PubMed search failed. Try again.", className="text-danger small")

        if not ids:
            return [], html.P(f"No PubMed results for '{term}'.", className="text-muted small")

        import concurrent.futures

        def _fetch_pmid(pmid: str) -> dbc.Card | None:
            efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            efetch_params = {"db": "pubmed", "id": pmid, "rettype": "xml", "retmode": "xml"}
            if api_key:
                efetch_params["api_key"] = api_key
            try:
                r2 = requests.get(efetch_url, params=efetch_params, timeout=5)
                r2.raise_for_status()
                text = r2.text

                title = ""
                m = _re.search(r"<ArticleTitle>(.+?)</ArticleTitle>", text, _re.DOTALL)
                if m:
                    title = _re.sub(r"<[^>]+>", "", m.group(1)).strip()

                abstract = ""
                m = _re.search(r"<AbstractText[^>]*>(.+?)</AbstractText>", text, _re.DOTALL)
                if not m:
                    m = _re.search(r"<Abstract>(.+?)</Abstract>", text, _re.DOTALL)
                if m:
                    abstract = _re.sub(r"<[^>]+>", " ", m.group(1)).strip()
                    abstract = _re.sub(r"\s+", " ", abstract)[:500]

                journal = ""
                year = ""
                m_year = _re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", text, _re.DOTALL)
                if m_year:
                    year = m_year.group(1)
                m_j = _re.search(r"<ISOAbbreviation>(.+?)</ISOAbbreviation>", text)
                if m_j:
                    journal = m_j.group(1).strip()

                import dash_bootstrap_components as dbc
                return dbc.Card(
                    dbc.CardBody([
                        html.A(
                            title or f"PMID: {pmid}",
                            href=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
                            target="_blank",
                            className="fw-bold text-decoration-none d-block mb-1",
                        ),
                        html.P(f"{journal} ({year})" if journal else "", className="text-muted small mb-1"),
                        html.P(abstract[:400] + ("..." if len(abstract) > 400 else "") if abstract else "No abstract available.",
                               className="small text-muted mb-0"),
                    ]),
                    className="mb-2 shadow-sm",
                )
            except Exception:
                return None

        max_workers = min(4, len(ids))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_fetch_pmid, str(pmid)) for pmid in ids[:8]]
            results_set = [f.result() for f in concurrent.futures.as_completed(futures)]
        results = [r for r in results_set if r is not None]

        if not results:
            return [], html.P("Could not fetch abstract details.", className="text-danger small")

        return results, html.P(f"Found {len(ids)} results for '{term}'.", className="text-muted small mt-2")

    # ── Desktop shutdown ───────────────────────────────────────────
    from app.config import DESKTOP_MODE

    if DESKTOP_MODE:
        @app.server.route("/shutdown", methods=["POST"])
        def shutdown_server():
            _os._exit(0)
            return "OK"

        @app.callback(
            Output("stop-server-btn", "children"),
            Input("stop-server-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def stop_server(n_clicks):
            import requests
            try:
                requests.post(f"http://127.0.0.1:{_os.environ.get('PORT', 8080)}/shutdown", timeout=1)
            except Exception:
                pass
            _os._exit(0)
            return "Stopping..."

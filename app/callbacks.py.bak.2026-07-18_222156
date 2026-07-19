from __future__ import annotations

import pandas as pd
from dash import Input, Output, State, html

from app.components.cards import disease_grid
from app.components.tables import create_table
from app.data.loader import (
    get_all_settings,
    get_all_modalities,
    get_all_biomarkers,
    get_regimens_df,
    get_regimens_for_site,
    get_sites,
    site_exists,
)
from app.data.transforms import flatten_regimens_for_table, extract_trial_outcomes
from app.pages import disease, home, regimens, trials


REGIMEN_DISPLAY_COLS = [
    {"name": "Regimen", "id": "regimen_name"},
    {"name": "Setting", "id": "setting"},
    {"name": "Modality", "id": "Modality"},
    {"name": "Drugs", "id": "Drugs"},
    {"name": "Biomarkers", "id": "Biomarkers"},
    {"name": "Evidence", "id": "evidence_level"},
    {"name": "Category", "id": "guideline_category"},
]


def _search_regimens(df: pd.DataFrame, term: str) -> pd.DataFrame:
    mask = pd.Series(False, index=df.index)

    for col in ["regimen_name", "setting", "notes", "evidence_level", "guideline_category"]:
        if col in df.columns:
            mask |= df[col].astype(str).str.lower().str.contains(term, na=False)

    if "drugs" in df.columns:
        mask |= df["drugs"].apply(
            lambda x: any(
                term in str(d.get("name", "")).lower()
                or term in str(d.get("dose", "")).lower()
                or term in str(d.get("schedule", "")).lower()
                for d in x if isinstance(d, dict)
            )
            if isinstance(x, list) else False
        )

    if "biomarkers" in df.columns:
        mask |= df["biomarkers"].apply(
            lambda x: any(
                term in str(b.get("marker", "")).lower()
                or term in str(b.get("requirement", "")).lower()
                for b in x if isinstance(b, dict)
            )
            if isinstance(x, list) else False
        )

    if "treatment_modality" in df.columns:
        mask |= df["treatment_modality"].apply(
            lambda x: any(term in str(m).lower() for m in x)
            if isinstance(x, list) else False
        )

    flat = flatten_regimens_for_table(df)
    for col in ["Drugs", "Biomarkers", "Modality"]:
        if col in flat.columns:
            mask |= flat[col].astype(str).str.lower().str.contains(term, na=False)

    return df[mask]


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
    )
    def filter_cards(search_term: str | None):
        sites = get_sites()
        if not search_term or not search_term.strip():
            return disease_grid(sites)
        term = search_term.lower().strip()
        filtered = [
            s for s in sites
            if term in s["display_name"].lower()
            or term in s.get("description", "").lower()
            or term in s["id"].lower()
            or term in (s.get("archetype") or "").lower()
        ]
        return disease_grid(filtered)

    @app.callback(
        Output("regimen-table-container", "children"),
        Input("setting-filter", "value"),
        Input("modality-filter", "value"),
        Input("biomarker-filter", "value"),
        Input("regimen-search", "value"),
        State("url", "pathname"),
    )
    def filter_regimens(settings, modalities, biomarkers, search_term, pathname):
        site_id = None
        if pathname and pathname.startswith("/regimens/"):
            parts = pathname.split("/regimens/", 1)
            if len(parts) > 1 and parts[1]:
                site_id = parts[1].rstrip("/")

        if site_id and site_exists(site_id):
            df = get_regimens_for_site(site_id)
        else:
            df = get_regimens_df()

        if df.empty:
            return [html.P("No regimens available.", className="text-muted")]

        if settings:
            df = df[df["setting"].isin(settings)]
        if modalities:
            df = df[df["treatment_modality"].apply(
                lambda x: any(m in modalities for m in x)
                if isinstance(x, list) else False
            )]
        if biomarkers:
            def _has_biomarker(row_bios, target):
                if not isinstance(row_bios, list):
                    return False
                for b in row_bios:
                    if isinstance(b, dict) and b.get("marker", "") in target:
                        return True
                return False
            df = df[df["biomarkers"].apply(lambda x: _has_biomarker(x, biomarkers))]
        if search_term:
            term = search_term.lower().strip()
            if term:
                df = _search_regimens(df, term)

        df_flat = flatten_regimens_for_table(df)
        table_cols = [c for c in REGIMEN_DISPLAY_COLS if c["id"] in df_flat.columns]

        return [
            create_table(
                data=df_flat.to_dict("records"),
                columns=table_cols,
                id="regimen-table",
                row_selectable="single",
                selected_rows=[],
                page_size=20,
            ),
        ]

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
        import os as _os
        import time as _time
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

        results = []
        for pmid in ids[:8]:
            efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            efetch_params = {"db": "pubmed", "id": pmid, "rettype": "xml", "retmode": "xml"}
            if api_key:
                efetch_params["api_key"] = api_key
            try:
                r2 = requests.get(efetch_url, params=efetch_params, timeout=10)
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
                results.append(dbc.Card(
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
                ))

            except Exception:
                continue

            _time.sleep(0.15)

        if not results:
            return [], html.P("Could not fetch abstract details.", className="text-danger small")

        return results, html.P(f"Found {len(ids)} results for '{term}'.", className="text-muted small mt-2")

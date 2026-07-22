# Oncology Interactive Handbook

Interactive clinical oncology reference app built with **Flask + HTMX + Alpine.js**, deployable on **Google Cloud Run** with auto-deployment from GitHub via Cloud Build.

**Live repo:** [github.com/psdevraj-creator/oncology-reference](https://github.com/psdevraj-creator/oncology-reference)

## Overview

- **41 disease sites** — structured handbook (staging, RT doses, systemic therapy, key trials, follow-up, complications, clinical pearls)
- **1,935 regimens** — drugs, doses, biomarkers, trial evidence (OS, PFS, DFS, ORR)
- Interactive regimen explorer — filter by disease, setting, site, intent, line, text search
- Disease pages — section TOC sidebar, collapsible sections, in-page search with term highlighting
- Professional clinical design, zero framework dependencies

## Quick Start (Local)

```bash
pip install -r requirements.txt
python -m app.main
# → http://localhost:8080
```

## Deploy to Cloud Run

Push to `main` auto-deploys via Cloud Build:
```bash
git push origin main
```

Or manually:
```bash
gcloud builds submit --config cloudbuild.yaml .
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Flask 3 |
| UI | Bootstrap 5 (CDN) + Alpine.js 3 + HTMX 2 |
| Icons | Bootstrap Icons (CDN) |
| Data | Pandas, orjson |
| WSGI | Gunicorn (--preload) |
| Container | Docker (Python 3.11-slim) |
| CI/CD | Cloud Build (`cloudbuild.yaml`) |
| Hosting | Cloud Run (serverless, auto-scale) |

### Pages

| Route | Description |
|-------|-------------|
| `/` | Home — search bar + 41 disease site cards (client-side filter by Alpine.js) |
| `/disease/{site_id}` | Disease handbook — 25+ sections, collapsible, in-page search |
| `/regimens` | All 1,935 regimens across all sites — filter by site/subsite/intent/line |
| `/regimens/{site_id}` | Per-site regimens — filterable table + detail panel |

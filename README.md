# Oncology Interactive Handbook

Interactive clinical oncology reference app built with Dash, deployable on Google Cloud Run.

## Overview

- **41 disease sites** with structured handbook content (staging, RT doses, systemic therapy, key trials, follow-up, complications, clinical pearls)
- **1,935+ regimens** with drugs, doses, biomarkers, trial evidence (OS, PFS, DFS, ORR)
- Interactive regimen explorer with filters by disease, setting, modality, biomarker
- Disease overview pages with staging tables, RT dose tables, trial summaries
- FRCR pearls, clinical warnings, red flags

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m app.main
# → http://localhost:8080
```

## Data

The `data/` directory contains:
- `sites_registry.json` — Site index (41 active sites)
- `merged/` — Deduplicated regimen data per site
- `intermediate/` — Structured handbook content (staging, RT, trials, etc.)

Generated from the oncology handbook pipeline (NCCN guideline extraction + LLM synthesis).

## Deployment

### Google Cloud Run (Automatic)

1. **Push to GitHub** — Cloud Build triggers automatically via `cloudbuild.yaml`
2. **Manual deploy**:

```bash
gcloud builds submit --config deployment/cloudbuild.yaml .
```

### Docker (Manual)

```bash
cd deployment
docker build -t oncology-handbook ..
docker run -p 8080:8080 oncology-handbook
```

### One-time Cloud Run setup

```bash
# Enable services
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# Grant Cloud Build access to Cloud Run
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member=serviceAccount:$(gcloud projects describe PROJECT_ID \
    --format='value(projectNumber)')@cloudbuild.gserviceaccount.com \
    --role=roles/run.admin

gcloud iam service-accounts add-iam-policy-binding \
    $(gcloud projects describe PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com \
    --member=serviceAccount:$(gcloud projects describe PROJECT_ID \
    --format='value(projectNumber)')@cloudbuild.gserviceaccount.com \
    --role=roles/iam.serviceAccountUser
```

## Architecture

- **Dash** — Interactive UI framework
- **Flask/Gunicorn** — WSGI production server
- **Pandas** — Structured data handling
- **Pydantic** — Schema validation
- **Bootstrap 5** — UI components (via dash-bootstrap-components)
- **Plotly** — Charts (available for future use)

### User Isolation

All user state lives in the browser (dcc.Store with sessionStorage, URL path, and
dcc.Location). The server holds only read-only shared reference data loaded at
startup. No mutable globals, no server-side sessions, no cross-user leakage.

### Pages

| Route | Description |
|-------|-------------|
| `/` | Home — search + disease site grid |
| `/disease/{site_id}` | Disease overview — handbook sections, staging, RT, trials |
| `/regimens/{site_id}` | Regimen explorer — filterable table + detail panel |
| `/regimens` | All regimens across all sites |

### Project Structure

```
interactive-oncology-app/
├── app/
│   ├── main.py              # App entrypoint / WSGI server
│   ├── layout.py            # App shell (navbar, content area)
│   ├── callbacks.py         # URL routing callbacks
│   ├── config.py            # Paths + env vars
│   ├── pages/               # Page modules
│   │   ├── home.py
│   │   ├── disease.py
│   │   └── regimens.py
│   ├── components/          # Reusable UI components
│   │   ├── cards.py         # Disease cards
│   │   ├── tables.py        # DataTable wrapper
│   │   ├── filters.py       # Filter components
│   │   ├── callouts.py      # Warning/pearl boxes
│   │   ├── navigation.py    # Breadcrumbs + sidebar
│   │   ├── staging_viewer.py  # Staging/RT/Trials renderers
│   │   └── section_renderer.py  # Generic handbook renderer
│   ├── data/                # Data layer
│   │   ├── loader.py        # Load + cache all JSON
│   │   ├── schemas.py       # Pydantic models
│   │   └── transforms.py    # Data transformations
│   └── assets/              # CSS
│       └── styles.css
├── data/                    # Copied from handbook pipeline
│   ├── sites_registry.json
│   ├── merged/
│   └── intermediate/
├── deployment/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── cloudbuild.yaml
├── requirements.txt
└── README.md
```

# Oncology Interactive Handbook

Interactive clinical oncology reference app built with **Dash 4**, deployable on **Google Cloud Run** with auto-deployment from GitHub via Cloud Build.

**Live repo:** [github.com/psdevraj-creator/oncology-reference](https://github.com/psdevraj-creator/oncology-reference)

## Overview

- **41 disease sites** — structured handbook (staging, RT doses, systemic therapy, key trials, follow-up, complications, clinical pearls)
- **1,935 regimens** — drugs, doses, biomarkers, trial evidence (OS, PFS, DFS, ORR)
- Interactive regimen explorer — filter by disease, setting, modality, biomarker, text search
- Disease pages — staging T/N/M tables, RT dose tables, trial summaries, FRCR pearls, red flags
- Professional clinical design, zero framework dependencies, offline-usable

## Quick Start (Local)

```bash
pip install -r requirements.txt
python -m app.main
# → http://localhost:8080
```

## Data Pipeline

The `data/` directory is populated from the source pipeline (`Oncology topics page/`):

| Directory | Source | Contains |
|-----------|--------|----------|
| `data/sites_registry.json` | `Oncology topics page/sites_registry.json` | Site index (41 active sites) |
| `data/merged/` | `Oncology topics page/deployment/Oncology/{site}/data/{site}_data.json` | Deduplicated regimens |
| `data/intermediate/` | `Oncology topics page/intermediate_json/{site}/` | Structured handbook content |

### Sync & Deploy Script

The `sync_and_deploy.py` script scans the source project for updated data files, copies them, and pushes to GitHub (which triggers Cloud Run deployment):

```bash
# Full sync + push to GitHub (data updates → Cloud Run auto-deploy)
python sync_and_deploy.py

# Preview what would change (no copying)
python sync_and_deploy.py --dry-run

# Sync data only, no git operations
python sync_and_deploy.py --data-only

# Push only (no data scan)
python sync_and_deploy.py --push-only

# Custom source path
python sync_and_deploy.py --source "D:\path\to\Oncology topics page"
```

When you run the source pipeline (`manage.py process` → `merge` → `regen-index`) and new data is generated, run `python sync_and_deploy.py` to update the live app.

## Google Cloud Run Deployment

### Project Info
- **GCP Project:** `oncology-reference`
- **Console:** https://console.cloud.google.com/run/overview?hl=en&project=oncology-reference
- **GitHub:** https://github.com/psdevraj-creator/oncology-reference

---

### STEP 1: One-Time GCP Setup

Open **Google Cloud Shell** (https://shell.cloud.google.com) or your local terminal with `gcloud` installed:

```bash
# Set the project
gcloud config set project oncology-reference

# Enable required services
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# Grant Cloud Build permission to deploy to Cloud Run
PROJECT_NUMBER=$(gcloud projects describe oncology-reference --format="value(projectNumber)")
gcloud projects add-iam-policy-binding oncology-reference \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/run.admin"
gcloud iam service-accounts add-iam-policy-binding \
    ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"
```

---

### STEP 2: Connect GitHub to Cloud Build

1. Go to **Cloud Build → Triggers** in GCP Console
   https://console.cloud.google.com/cloud-build/triggers?project=oncology-reference

2. Click **Create Trigger** with these settings:
   - **Name:** `oncology-handbook-deploy`
   - **Event:** Push to a branch
   - **Repository:** Connect to `psdevraj-creator/oncology-reference` (authenticate with GitHub)
   - **Branch:** `^main$`
   - **Configuration:** Cloud Build configuration file (yaml/json)
   - **Location:** `deployment/cloudbuild.yaml`
   - Click **Create**

3. Now any push to `main` will auto-deploy to Cloud Run.

---

### STEP 3: First Deploy (Manual)

After setting up the trigger, push the code to trigger the first build:

```bash
git push origin main
```

Or deploy manually from local:

```bash
gcloud builds submit --config deployment/cloudbuild.yaml .
```

---

### STEP 4: Verify

After deployment completes (~5-8 minutes first time):

```bash
gcloud run services describe oncology-handbook --region=us-central1 --format="value(status.url)"
```

This returns the live URL (e.g., `https://oncology-handbook-xxxxx-uc.a.run.app`).

Visit the URL to confirm the app is running.

---

## Architecture

```
GitHub (main branch)
  ├── Push → Cloud Build Trigger
  │           ├── docker build -t gcr.io/$PROJECT_ID/oncology-handbook
  │           ├── docker push
  │           └── gcloud run deploy
  │
  └── Cloud Run (us-central1)
       ├── Container: oncology-handbook
       ├── Gunicorn: app.main:server (2 workers, 4 threads)
       ├── PORT: auto-assigned by Cloud Run (usually 8080)
       └── URL: https://oncology-handbook-xxxxx-uc.a.run.app
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Dash 4 + Flask |
| UI | dash-bootstrap-components (Bootstrap 5) |
| Tables | Dash DataTable |
| Data | Pandas, Pydantic |
| Charts | Plotly (available) |
| WSGI | Gunicorn |
| Container | Docker (Python 3.11-slim) |
| CI/CD | Cloud Build (`cloudbuild.yaml`) |
| Hosting | Cloud Run (serverless, auto-scale) |

### User Isolation

All user state lives entirely in the browser:
- **`dcc.Location`** — current URL determines which page to render
- **`dcc.Store(type='session')`** — filter selections stored in `sessionStorage`
- **No server-side sessions, no `flask.g`, no mutable globals**

The server holds only **read-only** shared reference data (loaded once at startup). Every user gets fresh, isolated browser state. Safe for concurrent users.

### Pages

| Route | Description |
|-------|-------------|
| `/` | Home — search bar + 41 disease site cards (filterable by name/archetype) |
| `/disease/{site_id}` | Disease overview — handbook sections, staging T/N/M tables, RT doses, key trials, FRCR pearls, follow-up |
| `/regimens/{site_id}` | Regimen explorer — filterable DataTable + click-to-expand detail panel (drugs, biomarkers, trial outcomes) |
| `/regimens` | All 1,935 regimens across all sites |

### Project Structure

```
interactive-oncology-app/
├── app/
│   ├── main.py              # App entrypoint / WSGI server
│   ├── layout.py            # App shell (navbar, content area, footer)
│   ├── callbacks.py         # All callbacks (URL routing, search, regimen filters, detail panel)
│   ├── config.py            # Paths + env vars
│   ├── pages/
│   │   ├── home.py          # Search + disease grid
│   │   ├── disease.py       # Disease overview (sidebar + handbook sections)
│   │   └── regimens.py      # Regimen explorer layout
│   ├── components/
│   │   ├── cards.py         # Disease cards
│   │   ├── tables.py        # DataTable factory
│   │   ├── filters.py       # Filter dropdowns
│   │   ├── callouts.py      # Warning/pearl boxes
│   │   ├── navigation.py    # Breadcrumbs + sidebar TOC
│   │   ├── staging_viewer.py  # Staging/RT/Trials custom renderers
│   │   └── section_renderer.py  # Generic recursive handbook renderer
│   ├── data/
│   │   ├── loader.py        # Load + cache all JSON at startup
│   │   ├── schemas.py       # Pydantic validation models
│   │   └── transforms.py    # DataFrame transforms
│   └── assets/
│       └── styles.css       # Clinical theme
├── data/                    # Copied from source pipeline by sync_and_deploy.py
│   ├── sites_registry.json
│   ├── merged/              # 41 regimen JSONs
│   └── intermediate/        # 41 structured handbook JSONs
├── deployment/
│   ├── Dockerfile           # Gunicorn on Python 3.11-slim
│   ├── cloudbuild.yaml      # Cloud Run auto-deploy config
├── sync_and_deploy.py       # Data sync + git push script
├── requirements.txt
└── README.md
```

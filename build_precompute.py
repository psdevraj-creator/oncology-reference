"""
Pre-build data indexes for faster startup.
Run: python build_precompute.py
Produces: data/prebuilt/regimens.feather, nct_index.json, pubmed_index.json
"""

import json
import logging
from pathlib import Path

import pandas as pd

try:
    import orjson

    def _load(path: Path):
        return orjson.loads(path.read_bytes())
except ImportError:
    def _load(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
PREBUILT_DIR = DATA_DIR / "prebuilt"
MERGED_DIR = DATA_DIR / "merged"
NCT_DIR = DATA_DIR / "nct"
PUBMED_DIR = DATA_DIR / "pubmed"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def build_regimens_feather():
    site_registry_path = DATA_DIR / "sites_registry.json"
    if not site_registry_path.exists():
        log.warning("sites_registry.json not found, skipping regimens feather")
        return

    registry = _load(site_registry_path)
    sites = [s for s in registry.get("sites", []) if s.get("status") == "active"]

    all_rows: list[dict] = []
    for site in sites:
        site_id = site["id"]
        merged_path = MERGED_DIR / f"{site_id}.json"
        if not merged_path.exists():
            continue
        try:
            merged = _load(merged_path)
        except Exception:
            log.warning("Failed to load %s", merged_path)
            continue
        for r in merged.get("regimens", []):
            r["_site_id"] = site_id
            r["_site_display"] = site["display_name"]
            r["_archetype"] = site.get("archetype", "")
            # Pre-flatten columns
            if "drugs" in r and isinstance(r["drugs"], list):
                r["Drugs"] = " + ".join(
                    d.get("name", "?") for d in r["drugs"] if isinstance(d, dict)
                )
            if "biomarkers" in r and isinstance(r["biomarkers"], list):
                r["Biomarkers"] = "; ".join(
                    f"{b.get('marker', '')}" + (f": {b.get('requirement', '')}" if b.get("requirement") else "")
                    for b in r["biomarkers"] if isinstance(b, dict)
                )
            if "treatment_modality" in r and isinstance(r["treatment_modality"], list):
                r["Modality"] = ", ".join(str(m) for m in r["treatment_modality"])
            all_rows.append(r)

    if not all_rows:
        log.warning("No regimens found, skipping")
        return

    df = pd.DataFrame(all_rows)
    PREBUILT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_feather(PREBUILT_DIR / "regimens.feather")
    log.info("Wrote %d regimens to data/prebuilt/regimens.feather (%d rows)", len(df), len(df.columns))


def build_nct_index():
    if not NCT_DIR.exists():
        log.warning("NCT directory not found, skipping")
        return

    index: dict[str, dict] = {}
    by_nct: dict[str, dict] = {}

    for f in sorted(NCT_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            log.warning("Failed to load %s", f)
            continue
        trial_name = data.get("trial_name", "")
        nct_id = data.get("nct_id", "")
        if trial_name:
            index[trial_name.lower()] = data
        if nct_id:
            by_nct[nct_id] = data

    PREBUILT_DIR.mkdir(parents=True, exist_ok=True)
    output = {"index": index, "by_nct": by_nct}
    (PREBUILT_DIR / "nct_index.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    log.info("Wrote nct_index.json (%d index, %d by_nct)", len(index), len(by_nct))


def build_pubmed_index():
    if not PUBMED_DIR.exists():
        log.warning("PubMed directory not found, skipping")
        return

    index: dict[str, dict] = {}
    for f in sorted(PUBMED_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            log.warning("Failed to load %s", f)
            continue
        name = data.get("trial_name", f.stem)
        import re
        key = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())[:80]
        if key:
            index[key] = data

    PREBUILT_DIR.mkdir(parents=True, exist_ok=True)
    (PREBUILT_DIR / "pubmed_index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )
    log.info("Wrote pubmed_index.json (%d entries)", len(index))


if __name__ == "__main__":
    log.info("Building pre-computed indexes...")
    build_regimens_feather()
    build_nct_index()
    build_pubmed_index()
    log.info("Done. Pre-built files in %s", PREBUILT_DIR)

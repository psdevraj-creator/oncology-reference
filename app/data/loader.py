import json
import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from app.config import SITES_REGISTRY_PATH, MERGED_DATA_DIR, INTERMEDIATE_DATA_DIR

logger = logging.getLogger(__name__)

_sites: list[dict[str, Any]] = []
_sites_by_id: dict[str, dict[str, Any]] = {}
_handbooks: dict[str, dict[str, Any]] = {}
_regimens_df: pd.DataFrame = pd.DataFrame()
_all_regimens: list[dict[str, Any]] = []
_references: dict[str, dict[str, Any]] = {}

_loaded = False


def load_all() -> None:
    global _sites, _sites_by_id, _handbooks, _regimens_df, _all_regimens, _references, _loaded

    if _loaded:
        return

    logger.info("Loading site registry from %s", SITES_REGISTRY_PATH)
    with open(SITES_REGISTRY_PATH, encoding="utf-8") as fh:
        registry = json.load(fh)

    _sites = [s for s in registry.get("sites", []) if s.get("status") == "active"]
    _sites_by_id = {s["id"]: s for s in _sites}
    logger.info("Loaded %d active sites", len(_sites))

    all_regimens: list[dict[str, Any]] = []
    for site in _sites:
        site_id: str = site["id"]
        merged_path = MERGED_DATA_DIR / f"{site_id}.json"

        if merged_path.exists():
            try:
                with open(merged_path, encoding="utf-8") as fh:
                    merged = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Skipping merged JSON for %s: %s", site_id, exc)
                continue

            for r in merged.get("regimens", []):
                r["_site_id"] = site_id
                r["_site_display"] = site["display_name"]
                r["_archetype"] = site.get("archetype", "")
                all_regimens.append(r)

            _references[site_id] = merged.get("references", {})

        inter_dir = INTERMEDIATE_DATA_DIR / site_id
        if inter_dir.exists():
            json_files = sorted(inter_dir.glob("*.json"))
            if json_files:
                try:
                    with open(json_files[0], encoding="utf-8") as fh:
                        inter = json.load(fh)
                    _handbooks[site_id] = inter.get("tier_2_handbook", {})
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Skipping intermediate JSON for %s: %s", site_id, exc)

    _all_regimens = all_regimens
    _regimens_df = pd.DataFrame(all_regimens) if all_regimens else pd.DataFrame()
    _loaded = True
    logger.info("Loaded %d regimens, %d handbooks", len(all_regimens), len(_handbooks))


def _ensure_loaded() -> None:
    if not _loaded:
        load_all()


def get_sites() -> list[dict[str, Any]]:
    _ensure_loaded()
    return _sites


def get_site(site_id: str) -> Optional[dict[str, Any]]:
    _ensure_loaded()
    return _sites_by_id.get(site_id)


def get_handbook(site_id: str) -> dict[str, Any]:
    _ensure_loaded()
    return _handbooks.get(site_id, {})


def get_regimens_df() -> pd.DataFrame:
    _ensure_loaded()
    return _regimens_df


def get_regimens_for_site(site_id: str) -> pd.DataFrame:
    df = get_regimens_df()
    if df.empty:
        return df
    return df[df["_site_id"] == site_id].copy()


def get_all_regimens() -> list[dict[str, Any]]:
    _ensure_loaded()
    return _all_regimens


def get_references(site_id: str) -> dict[str, Any]:
    _ensure_loaded()
    return _references.get(site_id, {})


def site_exists(site_id: str) -> bool:
    _ensure_loaded()
    return site_id in _sites_by_id


def get_all_settings() -> list[str]:
    _ensure_loaded()
    if _regimens_df.empty:
        return []
    settings = _regimens_df["setting"].dropna().unique().tolist()
    return sorted(settings)


def get_all_modalities() -> list[str]:
    _ensure_loaded()
    modalities: set[str] = set()
    for row in _all_regimens:
        mods = row.get("treatment_modality")
        if not mods or not isinstance(mods, list):
            continue
        for m in mods:
            modalities.add(m)
    return sorted(modalities)


def get_all_biomarkers() -> list[str]:
    _ensure_loaded()
    markers: set[str] = set()
    for r in _all_regimens:
        biomarkers = r.get("biomarkers")
        if not biomarkers or not isinstance(biomarkers, list):
            continue
        for b in biomarkers:
            if isinstance(b, dict):
                markers.add(b.get("marker", ""))
    return sorted(m for m in markers if m)

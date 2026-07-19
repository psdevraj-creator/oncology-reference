import json as _stdlib_json
import logging
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

try:
    import orjson

    def _json_loads(data: bytes | str) -> Any:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return orjson.loads(data)

    def _json_load(path: Path) -> Any:
        return orjson.loads(path.read_bytes())
except ImportError:
    def _json_loads(data: bytes | str) -> Any:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return _stdlib_json.loads(data)

    def _json_load(path: Path) -> Any:
        with open(path, encoding="utf-8") as fh:
            return _stdlib_json.load(fh)

from app.config import SITES_REGISTRY_PATH, MERGED_DATA_DIR, INTERMEDIATE_DATA_DIR, DATA_DIR

logger = logging.getLogger(__name__)

_sites: list[dict[str, Any]] = []
_sites_by_id: dict[str, dict[str, Any]] = {}
_handbooks: dict[str, dict[str, Any]] = {}
_regimens_df: pd.DataFrame = pd.DataFrame()
_references: dict[str, dict[str, Any]] = {}
_pubmed_cache: dict[str, dict[str, Any]] = {}

_loaded = False
_pubmed_loaded = False

_cached_settings: dict[str | None, list[str]] = {}
_cached_modalities: dict[str | None, list[str]] = {}
_cached_biomarkers: dict[str | None, list[str]] = {}


def load_all() -> None:
    global _sites, _sites_by_id, _regimens_df, _references, _loaded, \
        _cached_settings, _cached_modalities, _cached_biomarkers

    if _loaded:
        return

    logger.info("Loading site registry from %s", SITES_REGISTRY_PATH)
    registry = _json_load(SITES_REGISTRY_PATH)

    _sites = [s for s in registry.get("sites", []) if s.get("status") == "active"]
    _sites_by_id = {s["id"]: s for s in _sites}
    logger.info("Loaded %d active sites", len(_sites))

    # Try pre-built feather first
    prebuilt_dir = DATA_DIR / "prebuilt"
    feather_path = prebuilt_dir / "regimens.feather"
    if feather_path.exists():
        try:
            _regimens_df = pd.read_feather(feather_path)
            # Convert numpy array columns back to lists for compatibility
            for col in ["drugs", "biomarkers", "treatment_modality"]:
                if col in _regimens_df.columns:
                    _regimens_df[col] = _regimens_df[col].apply(
                        lambda x: x.tolist() if hasattr(x, 'tolist') else (x if isinstance(x, list) else [])
                    )
            _loaded = True
            logger.info("Loaded %d regimens from pre-built feather", len(_regimens_df))
            return
        except Exception as exc:
            logger.warning("Failed to read pre-built feather: %s", exc)

    all_regimens: list[dict[str, Any]] = []
    for site in _sites:
        site_id: str = site["id"]
        merged_path = MERGED_DATA_DIR / f"{site_id}.json"

        if merged_path.exists():
            try:
                merged = _json_load(merged_path)
            except Exception as exc:
                logger.warning("Skipping merged JSON for %s: %s", site_id, exc)
                continue

            for r in merged.get("regimens", []):
                r["_site_id"] = site_id
                r["_site_display"] = site["display_name"]
                r["_archetype"] = site.get("archetype", "")
                all_regimens.append(r)

            _references[site_id] = merged.get("references", {})

    _regimens_df = pd.DataFrame(all_regimens) if all_regimens else pd.DataFrame()
    _loaded = True

    # Pre-flatten columns for table display
    if not _regimens_df.empty:
        _regimens_df = _pre_flatten_regimens(_regimens_df)

    # Pre-compute filter dropdown values
    if not _regimens_df.empty:
        _cached_settings[None] = sorted(_regimens_df["setting"].dropna().unique().tolist())
        _cached_modalities[None] = sorted(
            m for m in _regimens_df["treatment_modality"].explode().dropna().unique() if m
        )
        all_markers: set[str] = set()
        for bios in _regimens_df["biomarkers"].dropna():
            if isinstance(bios, list):
                for b in bios:
                    if isinstance(b, dict):
                        all_markers.add(b.get("marker", ""))
        _cached_biomarkers[None] = sorted(m for m in all_markers if m)

    logger.info("Loaded %d regimens", len(all_regimens))


def _pre_flatten_regimens(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-flatten Drugs, Biomarkers, Modality columns at load time."""
    out = df.copy()
    if "drugs" in out.columns:
        out["Drugs"] = out["drugs"].apply(
            lambda drugs: " + ".join(d.get("name", "?") for d in drugs if isinstance(d, dict))
            if isinstance(drugs, list) else ""
        )
    if "biomarkers" in out.columns:
        out["Biomarkers"] = out["biomarkers"].apply(
            lambda bios: "; ".join(
                f"{b.get('marker', '')}" + (f": {b.get('requirement', '')}" if b.get("requirement") else "")
                for b in bios if isinstance(b, dict)
            ) if isinstance(bios, list) else ""
        )
    if "treatment_modality" in out.columns:
        out["Modality"] = out["treatment_modality"].apply(
            lambda x: ", ".join(str(m) for m in x) if isinstance(x, list) else ""
        )
    return out


def _load_single_handbook(site_id: str) -> dict[str, Any]:
    inter_dir = INTERMEDIATE_DATA_DIR / site_id
    if not inter_dir.exists():
        return {}
    json_files = sorted(inter_dir.glob("*.json"))
    if not json_files:
        return {}
    try:
        inter = _json_load(json_files[0])
        return inter.get("tier_2_handbook", {})
    except Exception:
        return {}


def _load_pubmed_cache() -> None:
    global _pubmed_cache, _pubmed_loaded
    if _pubmed_loaded:
        return
    pubmed_dir = DATA_DIR / "pubmed"
    if not pubmed_dir.exists():
        _pubmed_loaded = True
        return

    # Try pre-built index first
    prebuilt_index = DATA_DIR / "prebuilt" / "pubmed_index.json"
    if prebuilt_index.exists():
        try:
            _pubmed_cache = _json_load(prebuilt_index)
            _pubmed_loaded = True
            logger.info("Loaded %d pubmed entries from pre-built index", len(_pubmed_cache))
            return
        except Exception:
            pass

    for pf in pubmed_dir.glob("*.json"):
        try:
            data = _json_load(pf)
            name = data.get("trial_name", pf.stem)
            _pubmed_cache[_normalize_key(name)] = data
        except Exception:
            pass
    _pubmed_loaded = True


def _normalize_key(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())[:80]


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
    if site_id in _handbooks:
        return _handbooks[site_id]
    data = _load_single_handbook(site_id)
    if data:
        _handbooks[site_id] = data
    return data


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
    if _regimens_df.empty:
        return []
    return _regimens_df.to_dict("records")


def get_references(site_id: str) -> dict[str, Any]:
    _ensure_loaded()
    return _references.get(site_id, {})


def site_exists(site_id: str) -> bool:
    _ensure_loaded()
    return site_id in _sites_by_id


def get_all_settings(site_id: Optional[str] = None) -> list[str]:
    _ensure_loaded()
    sid: str | None = site_id
    if sid is not None and sid in _cached_settings:
        return _cached_settings[sid]
    if sid is None and None in _cached_settings:
        return _cached_settings[None]
    if sid:
        df = get_regimens_for_site(sid)
        if df.empty:
            return []
        vals = sorted(df["setting"].dropna().unique().tolist())
        _cached_settings[sid] = vals
        return vals
    if _regimens_df.empty:
        return []
    vals = sorted(_regimens_df["setting"].dropna().unique().tolist())
    _cached_settings[None] = vals
    return vals


def get_all_modalities(site_id: Optional[str] = None) -> list[str]:
    _ensure_loaded()
    sid: str | None = site_id
    if sid is not None and sid in _cached_modalities:
        return _cached_modalities[sid]
    if sid is None and None in _cached_modalities:
        return _cached_modalities[None]
    if sid:
        df = get_regimens_for_site(sid)
        if df.empty:
            return []
        vals = sorted(m for m in df["treatment_modality"].explode().dropna().unique() if m)
        _cached_modalities[sid] = vals
        return vals
    if _regimens_df.empty:
        return []
    vals = sorted(m for m in _regimens_df["treatment_modality"].explode().dropna().unique() if m)
    _cached_modalities[None] = vals
    return vals


def get_all_biomarkers(site_id: Optional[str] = None) -> list[str]:
    _ensure_loaded()
    sid: str | None = site_id
    if sid is not None and sid in _cached_biomarkers:
        return _cached_biomarkers[sid]
    if sid is None and None in _cached_biomarkers:
        return _cached_biomarkers[None]
    markers: set[str] = set()
    source_df = get_regimens_for_site(sid) if sid else _regimens_df
    if source_df.empty:
        return []
    for bios in source_df["biomarkers"].dropna():
        if isinstance(bios, list):
            for b in bios:
                if isinstance(b, dict):
                    markers.add(b.get("marker", ""))
    vals = sorted(m for m in markers if m)
    cache_key: str | None = sid if sid else None
    _cached_biomarkers[cache_key] = vals
    return vals


def get_pubmed_data(trial_name: str) -> Optional[dict[str, Any]]:
    _ensure_loaded()
    if not trial_name:
        return None

    # Lazy-load pubmed cache on first lookup
    if not _pubmed_loaded:
        _load_pubmed_cache()

    name = trial_name.strip()

    keys_to_try = [
        _normalize_key(name),
    ]

    paren_idx = name.find("(")
    if paren_idx > 0:
        keys_to_try.append(_normalize_key(name[:paren_idx].strip()))

    words = name.split()
    for n in range(min(4, len(words)), 0, -1):
        short = " ".join(words[:n]).strip().rstrip(",").rstrip(".")
        if short.lower() != name.lower():
            keys_to_try.append(_normalize_key(short))

    seen: set[str] = set()
    for key in keys_to_try:
        if key in seen:
            continue
        seen.add(key)
        if key in _pubmed_cache:
            return _pubmed_cache[key]

    parts = re.split(r"[\s\-_/]+", name.lower())
    if len(parts) > 1:
        for key, data in _pubmed_cache.items():
            if parts[0] in key and len(parts[0]) >= 3:
                return data

    return None


def get_all_pubmed() -> dict[str, dict[str, Any]]:
    _ensure_loaded()
    if not _pubmed_loaded:
        _load_pubmed_cache()
    return _pubmed_cache

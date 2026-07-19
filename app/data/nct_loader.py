"""
NCT Verified Trial Data Loader.
Loads and indexes NCT-verified trial outcomes for the Dash app.
Provides structured enrollment, phase, PMIDs, and outcome data.
"""

import json
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
NCT_DIR = PROJECT_ROOT / "data" / "nct"


class NCTLoader:
    """Load and query NCT-verified trial data."""

    def __init__(self):
        self._index: dict[str, dict] = {}
        self._by_nct: dict[str, dict] = {}
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        if not NCT_DIR.exists():
            return

        # Try pre-built index first
        prebuilt_index = PROJECT_ROOT / "data" / "prebuilt" / "nct_index.json"
        if prebuilt_index.exists():
            try:
                index_data = json.loads(prebuilt_index.read_text(encoding="utf-8"))
                self._index = index_data.get("index", {})
                self._by_nct = index_data.get("by_nct", {})
                if self._index or self._by_nct:
                    self._loaded = True
                    return
            except Exception:
                pass

        for f in NCT_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            trial_name = data.get("trial_name", "")
            nct_id = data.get("nct_id", "")
            if trial_name:
                self._index[trial_name.lower()] = data
            if nct_id:
                self._by_nct[nct_id] = data
        self._loaded = True

    def lookup_by_trial_name(self, trial_name: str) -> Optional[dict]:
        self._load()
        if not trial_name:
            return None
        # Direct lookup
        key = trial_name.strip().lower()
        if key in self._index:
            return self._index[key]
        # Try partial match (acronym within trial name)
        for stored_name, data in self._index.items():
            acronym = data.get("acronym", "").lower()
            if acronym and (acronym in key or key in stored_name):
                return data
        return None

    def lookup_by_nct(self, nct_id: str) -> Optional[dict]:
        self._load()
        return self._by_nct.get(nct_id)

    def get_enrollment(self, trial_name: str) -> Optional[int]:
        data = self.lookup_by_trial_name(trial_name)
        if data:
            return data.get("enrollment")
        return None

    def get_phase(self, trial_name: str) -> list[str]:
        data = self.lookup_by_trial_name(trial_name)
        if data:
            return data.get("phase", [])
        return []

    def get_pmids(self, trial_name: str) -> list[dict]:
        data = self.lookup_by_trial_name(trial_name)
        if data:
            return data.get("pmids", [])
        return []

    def get_outcomes(self, trial_name: str) -> list[dict]:
        data = self.lookup_by_trial_name(trial_name)
        if data:
            return data.get("outcomes", [])
        return []

    def get_verified_nct_id(self, trial_name: str) -> Optional[str]:
        data = self.lookup_by_trial_name(trial_name)
        if data:
            return data.get("nct_id")
        return None

    def has_results(self, trial_name: str) -> bool:
        data = self.lookup_by_trial_name(trial_name)
        if data:
            return data.get("has_results", False)
        return False

    @property
    def total_verified(self) -> int:
        self._load()
        return len(self._index)

    @property
    def total_with_results(self) -> int:
        self._load()
        return sum(1 for d in self._index.values() if d.get("has_results"))

    def summary(self) -> dict:
        return {
            "verified_trials": self.total_verified,
            "with_results": self.total_with_results,
            "cache_dir": str(NCT_DIR),
        }


_nct_loader: Optional[NCTLoader] = None


def get_nct_loader() -> NCTLoader:
    global _nct_loader
    if _nct_loader is None:
        _nct_loader = NCTLoader()
    return _nct_loader

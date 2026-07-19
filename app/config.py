import os
import sys
from pathlib import Path


def _get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _get_project_root()
DATA_DIR = PROJECT_ROOT / "data"
SITES_REGISTRY_PATH = DATA_DIR / "sites_registry.json"
MERGED_DATA_DIR = DATA_DIR / "merged"
INTERMEDIATE_DATA_DIR = DATA_DIR / "intermediate"

PORT = int(os.environ.get("PORT", 8080))
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
DESKTOP_MODE = os.environ.get("DESKTOP_MODE", "") == "1"

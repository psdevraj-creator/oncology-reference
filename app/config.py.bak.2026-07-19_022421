import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SITES_REGISTRY_PATH = DATA_DIR / "sites_registry.json"
MERGED_DATA_DIR = DATA_DIR / "merged"
INTERMEDIATE_DATA_DIR = DATA_DIR / "intermediate"

PORT = int(os.environ.get("PORT", 8080))
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")

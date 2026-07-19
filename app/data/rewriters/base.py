"""
Synchronous base: OpenAI client, retry logic, cache read/write.
Processes sites in batches with concurrent.futures for parallelism.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

SOURCE_PROJECT = Path(__file__).resolve().parent.parent.parent.parent.parent / "Oncology topics page"
load_dotenv(dotenv_path=str(SOURCE_PROJECT / ".env"), override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
INTERMEDIATE_DIR = PROJECT_ROOT / "data" / "intermediate"
CACHE_DIR = PROJECT_ROOT / "data" / "rewritten" / "sections"

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_BASE = "https://api.deepseek.com/v1"

CONCURRENCY = int(os.environ.get("REWRITER_CONCURRENCY", "6"))

_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_KEY, base_url=DEEPSEEK_BASE)
    return _client


def load_handbook(site_id: str) -> tuple[dict | None, str | None]:
    site_dir = INTERMEDIATE_DIR / site_id
    if not site_dir.is_dir():
        return None, None
    files = sorted([f for f in site_dir.iterdir() if f.suffix == ".json"])
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            hb = data.get("tier_2_handbook", {})
            return hb, fp.name
        except Exception:
            continue
    return None, None


def cache_path(site_id: str, section: str) -> Path:
    return CACHE_DIR / site_id / f"{section}.json"


def read_cache(site_id: str, section: str) -> dict | None:
    fp = cache_path(site_id, section)
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def write_cache(site_id: str, section: str, data: dict) -> None:
    fp = cache_path(site_id, section)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def section_value(handbook: dict, section: str) -> str | None:
    value = handbook.get(section)
    if value is None:
        return None
    if isinstance(value, str):
        if len(value.strip()) < 150:
            return None
        return value
    if isinstance(value, (list, dict)):
        s = json.dumps(value, ensure_ascii=False)
        if len(s) < 150:
            return None
        return s
    return None


def call_llm(prompt: str, user_input: str, label: str,
             max_tokens: int = 4096) -> dict | None:
    client = get_client()
    for attempt in range(1, 7):
        try:
            print(f"  {label}...", end=" ", flush=True)
            t0 = time.monotonic()
            resp = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=max_tokens, temperature=0.1,
            )
            raw = resp.choices[0].message.content
            if not raw:
                print(f"EMPTY (finish={resp.choices[0].finish_reason})")
                if attempt < 6:
                    time.sleep(3)
                continue
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else parts[-1]
                raw = raw.removeprefix("json").strip()
            elapsed = time.monotonic() - t0
            print(f"OK ({elapsed:.0f}s, {len(raw)} chars)")
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"JSON FAIL: {e}")
            if attempt < 6:
                time.sleep(2)
        except Exception as e:
            print(f"ERR: {e}")
            if attempt < 6:
                time.sleep(4)
    return None


def process_task(label: str, prompt: str, user_input: str,
                 max_tokens: int, site_id: str, section: str) -> bool:
    result = call_llm(prompt, user_input, label, max_tokens=max_tokens)
    if result is None:
        return False
    result["_section"] = section
    result["_site_id"] = site_id
    result["_chars_in"] = len(user_input)
    write_cache(site_id, section, result)
    return True


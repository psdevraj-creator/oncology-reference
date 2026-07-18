"""
One-time rewrite of handbook definition sections from single-paragraph prose
into structured {heading, content} sub-sections via DeepSeek.

Usage:
    python -m app.data.definition_rewriter          # process all uncached sites
    python -m app.data.definition_rewriter --force  # reprocess all, overwriting cache
    python -m app.data.definition_rewriter --site breast  # single site only
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

SOURCE_PROJECT = Path(__file__).resolve().parent.parent.parent.parent / "Oncology topics page"
_ENV_PATH = SOURCE_PROJECT / ".env"
load_dotenv(dotenv_path=str(_ENV_PATH), override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INTERMEDIATE_DIR = PROJECT_ROOT / "data" / "intermediate"
REWRITTEN_DIR = PROJECT_ROOT / "data" / "rewritten"

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL") or os.environ.get("LLM_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")

MIN_CHARS = 300
MAX_SECTIONS = 8
MIN_SECTIONS = 2

PROMPT = """You are a clinical oncology editor with deep expertise in cancer classification, staging, and diagnostics.

Your task: restructure the following clinical definition paragraph into 3-5 logical sub-sections.

CRITICAL RULES:
1. PRESERVE ALL original text verbatim — do NOT summarize, condense, edit, or rephrase
2. Keep all citations like [ST-1], [BINV-1], [IBC-1] exactly as they appear
3. Keep TNM staging details, anatomical terms, drug names, percentages verbatim
4. Split ONLY at natural topic transitions (classification → staging → diagnosis → variants)
5. Each sub-section heading must be 2-5 words, clinically precise (e.g. "WHO Classification", "TNM Staging", "Diagnostic Criteria")
6. Do NOT invent facts, statistics, or details not present in the original text
7. If a sentence bridges two topics, keep it with whichever topic it predominantly belongs to
8. The combined content of all sections MUST equal the original text with no omissions

Output as raw JSON only:
{
  "sections": [
    {"heading": "Classification", "content": "..."},
    {"heading": "TNM Staging", "content": "..."},
    {"heading": "Diagnostic Criteria", "content": "..."}
  ]
}

No markdown code fences. No additional text. Pure JSON."""


def _get_definition(site_id: str) -> tuple[str | None, str | None]:
    site_dir = INTERMEDIATE_DIR / site_id
    if not site_dir.is_dir():
        return None, None
    files = sorted([f for f in site_dir.iterdir() if f.suffix == ".json"])
    if not files:
        return None, None
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            handbook = data.get("tier_2_handbook", {})
            definition = handbook.get("definition", "")
            if isinstance(definition, str) and len(definition.strip()) >= MIN_CHARS:
                return definition.strip(), fp.name
        except (json.JSONDecodeError, KeyError):
            continue
    return None, None


def _call_deepseek(definition: str, site_id: str) -> dict | None:
    if not DEEPSEEK_KEY:
        print(f"  [SKIP] {site_id}: No DEEPSEEK_API_KEY set")
        return None

    client = OpenAI(api_key=DEEPSEEK_KEY, base_url=DEEPSEEK_BASE)

    for attempt in range(1, 5):
        print(f"  {site_id}: calling DeepSeek (model={DEEPSEEK_MODEL})", end="")
        if attempt > 1:
            print(f" [attempt {attempt}/4]", end="")
        print("...")
        try:
            resp = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": definition},
                ],
                max_tokens=4096,
                temperature=0.1,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            data = json.loads(raw)
            sections = data.get("sections", [])
            if not isinstance(sections, list) or len(sections) < MIN_SECTIONS:
                print(f"  [WARN] {site_id}: only {len(sections)} section(s), expected ≥{MIN_SECTIONS}")
                return None
            if len(sections) > MAX_SECTIONS:
                print(f"  [WARN] {site_id}: {len(sections)} sections, capping to {MAX_SECTIONS}")
                sections = sections[:MAX_SECTIONS]
            for s in sections:
                if "heading" not in s or "content" not in s:
                    print(f"  [WARN] {site_id}: section missing heading/content")
                    return None
            total_chars = sum(len(s.get("content", "")) for s in sections)
            if total_chars < MIN_CHARS:
                print(f"  [WARN] {site_id}: output too short ({total_chars} chars)")
                return None
            print(f"  {site_id}: restructured into {len(sections)} sections ({total_chars} chars)")
            return {"site_id": site_id, "sections": sections}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [ERR] {site_id}: JSON parse error: {e}")
            if attempt < 4:
                time.sleep(3)
        except Exception as e:
            print(f"  [ERR] {site_id}: API error: {e}")
            if attempt < 4:
                time.sleep(5)

    return None


def _cache_path(site_id: str) -> Path:
    return REWRITTEN_DIR / f"{site_id}_definition.json"


def process_site(site_id: str, force: bool = False) -> bool:
    cache = _cache_path(site_id)
    if cache.exists() and not force:
        print(f"  [CACHE] {site_id}: already rewritten, skipping")
        return True

    definition, source_file = _get_definition(site_id)
    if definition is None:
        print(f"  [SKIP] {site_id}: no definition (or too short <{MIN_CHARS} chars)")
        return False

    result = _call_deepseek(definition, site_id)
    if result is None:
        return False

    result["source_file"] = source_file
    result["original_chars"] = len(definition)
    result["model"] = DEEPSEEK_MODEL

    REWRITTEN_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def process_all(force: bool = False, site_filter: str | None = None) -> dict:
    if not INTERMEDIATE_DIR.is_dir():
        print(f"[ERROR] Intermediate data directory not found: {INTERMEDIATE_DIR}")
        return {"total": 0, "ok": 0, "skip": 0, "fail": 0}

    site_dirs = sorted(
        [d for d in INTERMEDIATE_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name.lower(),
    )

    if site_filter:
        site_dirs = [d for d in site_dirs if d.name == site_filter]
        if not site_dirs:
            print(f"[ERROR] Site '{site_filter}' not found in intermediate data")
            return {"total": 0, "ok": 0, "skip": 0, "fail": 0}

    stats = {"total": len(site_dirs), "ok": 0, "skip": 0, "fail": 0}
    print(f"\nRewriting definitions ({'ALL' if not site_filter else site_filter}) "
          f"— {stats['total']} sites, model={DEEPSEEK_MODEL}\n")

    for site_dir in site_dirs:
        site_id = site_dir.name
        if process_site(site_id, force=force):
            stats["ok"] += 1
        else:
            stats["fail"] += 1
        time.sleep(1)  # rate limit

    print(f"\nDone. {stats['ok']} restructured, {stats['fail']} failed/skipped ({stats['total']} total)")
    return stats


if __name__ == "__main__":
    force = "--force" in sys.argv
    site_filter = None
    for arg in sys.argv[1:]:
        if arg.startswith("--site="):
            site_filter = arg.split("=", 1)[1]
        elif arg == "--site":
            idx = sys.argv.index("--site")
            if idx + 1 < len(sys.argv):
                site_filter = sys.argv[idx + 1]

    process_all(force=force, site_filter=site_filter)

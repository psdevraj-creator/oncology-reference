#!/usr/bin/env python3
"""
PubMed Trial Enricher — Oncology Interactive Handbook

Queries PubMed E-utilities API for clinical trial abstracts
and caches the results alongside the handbook data.

First run queries all unique trials (~1,000 = ~2 min with API key).
Subsequent runs only query new/uncached trials (~10 seconds).

Usage:
    python pubmed_enricher.py                          # Use NCBI_API_KEY from .env or env var
    python pubmed_enricher.py --api-key YOUR_KEY       # Provide key directly
    python pubmed_enricher.py --force                  # Re-query all trials (ignore cache)
    python pubmed_enricher.py --dry-run                # Show what would be queried
    python pubmed_enricher.py --max 50                 # Limit to N trials (testing)

Called automatically by sync_and_deploy.py --pubmed
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
MERGED_DIR = DATA_DIR / "merged"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
PUBMED_DIR = DATA_DIR / "pubmed"
CACHE_MAX_AGE_DAYS = 30

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
REQUEST_DELAY = 0.20  # seconds between requests (5/sec safe with API key)

# Patterns for NCCN internal references (not real trial names)
NCCN_REF_PATTERN = re.compile(r"^\d{6,}")
ET_AL_PATTERN = re.compile(r"\((.+?)\s+et\s+al\.?\s+\d{4}\)")


def get_api_key() -> Optional[str]:
    key = os.environ.get("NCBI_API_KEY", "")
    if key:
        return key
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("NCBI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def normalize_trial_name(name: str) -> str:
    name = name.strip()
    # "20020408 (Van Cutsem et al. 2007)" → extract author name
    if NCCN_REF_PATTERN.match(name):
        m = ET_AL_PATTERN.search(name)
        if m:
            return m.group(1).strip()
        return ""

    # Remove extraneous suffixes
    name = re.sub(r"\s*\([^)]*\d{4}[^)]*\)\s*$", "", name)
    name = re.sub(r"\s*trial\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*study\s*$", "", name, flags=re.IGNORECASE)

    return name.strip()


def normalize_filename(name: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
    safe = re.sub(r"_+", "_", safe)
    safe = safe.strip("_")
    if len(safe) > 100:
        safe = safe[:100]
    return safe or hashlib.md5(name.encode()).hexdigest()[:12]


def collect_trial_names() -> set[str]:
    trials: set[str] = set()

    for jf in sorted(MERGED_DIR.glob("*.json")):
        try:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for r in data.get("regimens", []):
            td = r.get("trial_data")
            if isinstance(td, dict) and td.get("trial_name"):
                name = normalize_trial_name(td["trial_name"])
                if name:
                    trials.add(name)

    for site_dir in sorted(INTERMEDIATE_DIR.iterdir()):
        if not site_dir.is_dir():
            continue
        for jf in sorted(site_dir.glob("*.json")):
            try:
                with open(jf, encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            for t in data.get("tier_2_handbook", {}).get("key_trials", []):
                if not isinstance(t, dict):
                    continue
                acronym = (t.get("acronym") or "").strip()
                if acronym:
                    name = normalize_trial_name(acronym)
                    if name:
                        trials.add(name)
                full = (t.get("full_name") or "").strip()
                if full and full != acronym:
                    name = normalize_trial_name(full)
                    if name:
                        trials.add(name)

    return trials


def pubmed_search(query: str, api_key: Optional[str] = None) -> Optional[str]:
    url = f"{EUTILS_BASE}/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmax": "1", "retmode": "json"}
    if api_key:
        params["api_key"] = api_key
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        return ids[0] if ids else None
    except Exception:
        return None


def pubmed_fetch(pmid: str, api_key: Optional[str] = None) -> Optional[dict]:
    url = f"{EUTILS_BASE}/efetch.fcgi"
    params = {"db": "pubmed", "id": pmid, "rettype": "xml", "retmode": "xml"}
    if api_key:
        params["api_key"] = api_key
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        text = resp.text

        abstract = ""
        title = ""
        journal = ""
        year = ""
        authors: list[str] = []
        doi = ""

        m_title = re.search(r"<ArticleTitle>(.+?)</ArticleTitle>", text, re.DOTALL)
        if m_title:
            title = re.sub(r"<[^>]+>", "", m_title.group(1)).strip()

        m_abs = re.search(r"<AbstractText[^>]*>(.+?)</AbstractText>", text, re.DOTALL)
        if not m_abs:
            m_abs = re.search(r"<Abstract>(.+?)</Abstract>", text, re.DOTALL)
        if m_abs:
            abstract = re.sub(r"<[^>]+>", " ", m_abs.group(1)).strip()
            abstract = re.sub(r"\s+", " ", abstract)

        m_journal = re.search(r"<Title>(.+?)</Title>", text[: text.find("<Abstract")] if "<Abstract" in text else text, re.DOTALL)
        if m_journal:
            journal = re.sub(r"<[^>]+>", "", m_journal.group(1)).strip()

        m_year = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", text, re.DOTALL)
        if m_year:
            year = m_year.group(1)

        for m in re.finditer(r"<Author[^>]*>.*?<LastName>(.+?)</LastName>.*?<Initials>(.+?)</Initials>", text, re.DOTALL):
            authors.append(f"{m.group(1)} {m.group(2)}")

        m_doi = re.search(r"<ArticleId IdType=\"doi\">(.+?)</ArticleId>", text)
        if m_doi:
            doi = m_doi.group(1)

        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "year": year,
            "authors": authors[:5],
            "doi": doi,
            "query_date": datetime.now().isoformat(),
        }
    except Exception:
        return None


def build_search_query(trial_name: str) -> str:
    name = trial_name.strip().upper()
    # All-caps acronym? Search as title
    if re.match(r"^[A-Z][A-Z0-9\-_\. ]{2,40}$", name):
        return f'"{name}"[Title]'
    # Multi-word trial name
    if " " in name:
        terms = name.split()
        acronym = "".join(w[0] for w in terms if w[0].isalpha())
        if len(acronym) >= 2:
            return f'("{name}"[Title] OR {acronym}[Title]) AND (cancer OR carcinoma OR tumor OR neoplasm OR chemotherapy OR radiotherapy)'
        return f'"{name}"[Title]'
    # Single word
    return f'{name}[Title] AND (cancer OR carcinoma OR trial)'


def is_already_cached(trial_name: str) -> bool:
    fn = normalize_filename(trial_name)
    cache_path = PUBMED_DIR / f"{fn}.json"
    if not cache_path.exists():
        return False
    try:
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        query_date = data.get("query_date", "")
        if query_date:
            dt = datetime.fromisoformat(query_date)
            if datetime.now() - dt < timedelta(days=CACHE_MAX_AGE_DAYS):
                return True
    except Exception:
        pass
    return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enrich oncology trial data with PubMed abstracts")
    parser.add_argument("--api-key", type=str, default=None, help="NCBI API key")
    parser.add_argument("--force", action="store_true", help="Re-query all trials, ignore cache")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be queried without making requests")
    parser.add_argument("--max", type=int, default=0, help="Limit to N trials (for testing)")
    args = parser.parse_args()

    api_key = args.api_key or get_api_key()
    if not api_key:
        print("[WARN] No NCBI_API_KEY found. Rate limited to 3 requests/second.")
        print("       Get a free key at https://www.ncbi.nlm.nih.gov/account/")
        print("       Set NCBI_API_KEY in .env file or --api-key argument.")
        delay = 1.0
    else:
        delay = REQUEST_DELAY

    PUBMED_DIR.mkdir(parents=True, exist_ok=True)

    print("Collecting trial names from data files...")
    all_trials = collect_trial_names()
    print(f"Found {len(all_trials)} unique trial names across all sites")

    # Filter already-cached trials
    to_query: list[str] = []
    for name in sorted(all_trials):
        if not args.force and is_already_cached(name):
            continue
        to_query.append(name)

    if args.max and args.max < len(to_query):
        to_query = to_query[: args.max]

    print(f"Already cached: {len(all_trials) - len(to_query)}")
    print(f"Need to query:   {len(to_query)}")

    if args.dry_run:
        print("\n[Dry run] Would query these trials:")
        for name in to_query[:30]:
            query = build_search_query(name)
            print(f"  {name}  →  {query}")
        if len(to_query) > 30:
            print(f"  ... and {len(to_query) - 30} more")
        return

    if not to_query:
        print("All trials are cached. Nothing to do.")
        return

    success = 0
    no_match = 0
    errors = 0

    start_time = time.time()
    for i, name in enumerate(to_query, 1):
        query = build_search_query(name)
        print(f"[{i}/{len(to_query)}] {name[:60]:<60} ", end="", flush=True)

        pmid = pubmed_search(query, api_key)
        if not pmid:
            print("NO MATCH")
            no_match += 1
        else:
            data = pubmed_fetch(pmid, api_key)
            if data:
                data["trial_name"] = name
                fn = normalize_filename(name)
                cache_path = PUBMED_DIR / f"{fn}.json"
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"OK (PMID: {pmid})")
                success += 1
            else:
                print("FETCH ERROR")
                errors += 1

        # Rate limit delay
        if i < len(to_query):
            time.sleep(delay)

        # Progress report every 50
        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (len(to_query) - i) / rate if rate > 0 else 0
            print(f"  --- [{i}/{len(to_query)}] {rate:.1f}/sec, ~{remaining:.0f}s remaining ---")

    elapsed = time.time() - start_time
    print()
    print(f"Done in {elapsed:.1f}s")
    print(f"  Success:  {success}")
    print(f"  No match: {no_match}")
    print(f"  Errors:   {errors}")
    print(f"  Total cache files: {len(list(PUBMED_DIR.glob('*.json')))}")


if __name__ == "__main__":
    main()

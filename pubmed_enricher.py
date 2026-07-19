#!/usr/bin/env python3
"""
PubMed Trial Enricher v3 — Simple direct search.
Sends full trial name to PubMed. No parsing, no scoring — PubMed's own
relevance engine handles disambiguation.

Query strategy:
  1. "{trial_name}"[Title] AND (trial[Title/Abstract] OR cancer[Title/Abstract])
     → contextualized phrase search — filters out geographic/animal matches
  2. "{trial_name}"[All Fields]
     → fallback: full phrase anywhere

Usage:
    python pubmed_enricher.py                          # use NCBI_API_KEY from env
    python pubmed_enricher.py --force                  # re-query all trials
    python pubmed_enricher.py --max 10                 # limit for testing

Called automatically by: sync_and_deploy.py --pubmed
"""

import json
import os
import re
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
NCT_OVERRIDES_FILE = PUBMED_DIR / "nct_overrides.json"
CACHE_MAX_AGE_DAYS = 30

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
REQUEST_DELAY = 0.20


# ── Helpers ────────────────────────────────────────────────────

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


def normalize_name(name: str) -> str:
    name = name.strip()
    # Strip trailing noise
    name = re.sub(r"\s*trial\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*study\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*(?:phase\s*[IV1-3]+)\s*$", "", name, flags=re.IGNORECASE)
    return name.strip()


def safe_filename(name: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
    safe = re.sub(r"_+", "_", safe).strip("_")[:80]
    return safe or f"trial_{abs(hash(name)) % 1000000:06d}"


def load_nct_overrides() -> dict:
    if not NCT_OVERRIDES_FILE.exists():
        return {}
    try:
        return json.loads(NCT_OVERRIDES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def score_word_overlap(text_a: str, text_b: str) -> float:
    """Simple word overlap score between two strings. Returns 0-1."""
    wa = set(text_a.lower().split())
    wb = set(text_b.lower().split())
    if not wa or not wb:
        return 0
    return len(wa & wb) / min(len(wa), len(wb))


# ── Trial collection ───────────────────────────────────────────

def collect_trial_names() -> set[str]:
    trials: set[str] = set()

    for jf in sorted(MERGED_DIR.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in data.get("regimens", []):
            td = r.get("trial_data")
            if isinstance(td, dict) and td.get("trial_name"):
                name = normalize_name(td["trial_name"])
                if name and len(name) > 2:
                    trials.add(name)

    for site_dir in sorted(INTERMEDIATE_DIR.iterdir()):
        if not site_dir.is_dir():
            continue
        for jf in sorted(site_dir.glob("*.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            for t in data.get("tier_2_handbook", {}).get("key_trials", []):
                if not isinstance(t, dict):
                    continue
                for k in ("acronym", "full_name"):
                    val = (t.get(k) or "").strip()
                    if val:
                        name = normalize_name(val)
                        if name and len(name) > 2:
                            trials.add(name)

    return trials


# ── PubMed API ─────────────────────────────────────────────────

def pubmed_search(query: str, api_key: Optional[str] = None) -> Optional[str]:
    """Search PubMed, return the best (first) PMID. PubMed ranks by relevance."""
    url = f"{EUTILS_BASE}/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmax": "5", "retmode": "json"}
    if api_key:
        params["api_key"] = api_key
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def pick_best_pmid(pmids: list[str], api_key: Optional[str] = None) -> Optional[str]:
    """Pick the best PMID, skipping corrigenda/errata/secondary analyses."""
    if not pmids:
        return None
    skip_words = ("corrigendum", "erratum", "patient-reported outcomes", "quality of life",
                  "correction to", "correction:")
    for pmid in pmids:
        data = pubmed_fetch(pmid, api_key, fetch_abstract=False)
        if not data:
            continue
        title_lower = data.get("title", "").lower()
        if any(w in title_lower for w in skip_words):
            continue
        return pmid
    # All were corrigenda — return the first one anyway
    return pmids[0]


def pubmed_fetch(pmid: str, api_key: Optional[str] = None, fetch_abstract: bool = True) -> Optional[dict]:
    url = f"{EUTILS_BASE}/efetch.fcgi"
    params = {"db": "pubmed", "id": pmid, "rettype": "xml", "retmode": "xml"}
    if api_key:
        params["api_key"] = api_key
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        text = resp.text
    except Exception:
        return None

    # Title (always needed)
    m_title = re.search(r"<ArticleTitle>(.+?)</ArticleTitle>", text, re.DOTALL)
    title = ""
    if m_title:
        title = re.sub(r"<[^>]+>", "", m_title.group(1)).strip()

    result = {"title": title}

    if not fetch_abstract:
        return result

    # Full fetch
    abstract = ""
    m_abs = re.search(r"<AbstractText[^>]*>(.+?)</AbstractText>", text, re.DOTALL)
    if not m_abs:
        m_abs = re.search(r"<Abstract>(.+?)</Abstract>", text, re.DOTALL)
    if m_abs:
        abstract = re.sub(r"<[^>]+>", " ", m_abs.group(1)).strip()
        abstract = re.sub(r"\s+", " ", abstract)

    journal = ""
    year = ""
    authors: list[str] = []
    doi = ""

    m_journal = re.search(r"<ISOAbbreviation>(.+?)</ISOAbbreviation>", text)
    if not m_journal:
        m_journal = re.search(r"<Title>(.+?)</Title>",
            text[:text.find("<Abstract") if "<Abstract" in text else 2000], re.DOTALL)
    if m_journal:
        journal = re.sub(r"<[^>]+>", "", m_journal.group(1)).strip()

    m_year = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", text, re.DOTALL)
    if m_year:
        year = m_year.group(1)

    for m in re.finditer(r"<Author[^>]*>.*?<LastName>(.+?)</LastName>.*?<Initials>(.+?)</Initials>",
                        text, re.DOTALL):
        authors.append(f"{m.group(1)} {m.group(2)}")

    m_doi = re.search(r'<ArticleId IdType="doi">(.+?)</ArticleId>', text)
    if m_doi:
        doi = m_doi.group(1)

    result.update({
        "pmid": pmid,
        "abstract": abstract,
        "journal": journal,
        "year": year,
        "authors": authors[:5],
        "doi": doi,
        "query_date": datetime.now().isoformat(),
    })
    return result


# ── Caching ────────────────────────────────────────────────────

def is_cached(trial_name: str) -> bool:
    fp = PUBMED_DIR / f"{safe_filename(trial_name)}.json"
    if not fp.exists():
        return False
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        qd = data.get("query_date", "")
        if qd:
            dt = datetime.fromisoformat(qd)
            if datetime.now() - dt < timedelta(days=CACHE_MAX_AGE_DAYS):
                return True
    except Exception:
        pass
    return False


def save_cache(trial_name: str, data: dict):
    data["trial_name"] = trial_name
    fp = PUBMED_DIR / f"{safe_filename(trial_name)}.json"
    PUBMED_DIR.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── PMID cross-verification (NCT vs PubMed) ────────────────────

def verify_pmid(trial_name: str, nct_trial: dict, pubmed_pmid: str,
                api_key: Optional[str] = None) -> Optional[dict]:
    """When NCT provides PMIDs (trial sponsor), trust them and prefer RESULT type.
    Cross-check: fetch the NCT PMID. If it's valid clinical content, use it.
    Only fall back to PubMed search if all NCT PMIDs fail."""
    nct_pmid_list = []
    for p in nct_trial.get("pmids", []):
        if isinstance(p, str):
            nct_pmid_list.append(p)
        elif isinstance(p, dict):
            nct_pmid_list.append(p["pmid"])

    if not nct_pmid_list:
        return pubmed_fetch(pubmed_pmid, api_key)

    # Try NCT PMIDs — prefer RESULT type (actual trial paper)
    # Fall through to DERIVED type (subgroup analyses) if RESULT not available
    for pmid in nct_pmid_list:
        data = pubmed_fetch(pmid, api_key)
        if data and data.get("title"):
            title_lower = data["title"].lower()
            # Skip protocol/design papers if we have other options
            if ("design and rationale" in title_lower or "study protocol" in title_lower):
                continue
            data["_source"] = "nct-verified"
            return data

    # If only protocol papers found, use the first one
    for pmid in nct_pmid_list:
        data = pubmed_fetch(pmid, api_key)
        if data:
            data["_source"] = "nct-verified (protocol)"
            return data

    # NCT PMIDs all failed — fall back to PubMed
    return pubmed_fetch(pubmed_pmid, api_key)


# ── Main ───────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Simple PubMed trial enricher — direct trial name search")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--force", action="store_true", help="Re-query all trials")
    parser.add_argument("--max", type=int, default=0, help="Limit for testing")
    args = parser.parse_args()

    api_key = args.api_key or get_api_key()
    if not api_key:
        print("[WARN] No NCBI_API_KEY found. Rate limited to 3 req/sec.")
        print("       Get free key: https://www.ncbi.nlm.nih.gov/account/")
        delay = 1.0
    else:
        delay = REQUEST_DELAY

    PUBMED_DIR.mkdir(parents=True, exist_ok=True)

    print("Collecting trial names...")
    all_trials = collect_trial_names()
    print(f"Unique trial names: {len(all_trials)}")

    nct_overrides = load_nct_overrides()
    print(f"NCT cross-reference: {len(nct_overrides)} trials available")

    to_query: list[str] = []
    for name in sorted(all_trials):
        if len(name) < 3:
            continue
        if not args.force and is_cached(name):
            continue
        to_query.append(name)

    if args.max and 0 < args.max < len(to_query):
        to_query = to_query[:args.max]

    already = len(all_trials) - len(to_query)
    print(f"Cached: {already}, To query: {len(to_query)}")

    if not to_query:
        print("All trials cached. Done.")
        return

    success = 0
    no_match = 0
    errors = 0
    start_time = time.time()

    for i, name in enumerate(to_query, 1):
        print(f"[{i}/{len(to_query)}] {name[:55]:<55} ", end="", flush=True)

        # Query: try NCT first (trial sponsor verified), fallback to PubMed search
        clean = name.strip().replace('"', '')

        nct_trial = nct_overrides.get(name)
        if nct_trial and nct_trial.get("pmids"):
            data = verify_pmid(name, nct_trial, "", api_key)
            if data:
                save_cache(name, data)
                src = data.pop("_source", "")
                print(f"NCT-OK (PMID:{data['pmid']})")
                success += 1
            else:
                print("NCT-FAIL")
                errors += 1
            continue

        pmids = pubmed_search(f'"{clean}" AND (trial OR cancer OR carcinoma OR chemotherapy)', api_key)
        if not pmids:
            pmids = pubmed_search(f'"{clean}"', api_key)

        pmid = pick_best_pmid(pmids, api_key)

        if not pmid:
            print("NO MATCH")
            no_match += 1
        else:
            data = pubmed_fetch(pmid, api_key)
            if data:
                save_cache(name, data)
                print(f"OK (PMID:{data['pmid']})")
                success += 1
            else:
                print("FETCH ERR")
                errors += 1

        if i < len(to_query):
            time.sleep(delay)

        if i % 100 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (len(to_query) - i) / rate if rate > 0 else 0
            print(f"  --- [{i}/{len(to_query)}] {rate:.1f}/s, ~{remaining:.0f}s left, hit={success}/{i} ---")

    elapsed = time.time() - start_time
    print()
    print(f"Done in {elapsed:.0f}s")
    print(f"  Success:  {success}")
    print(f"  No match: {no_match}")
    print(f"  Errors:   {errors}")
    print(f"  Cache:    {len(list(PUBMED_DIR.glob('*.json')))} files")


if __name__ == "__main__":
    main()

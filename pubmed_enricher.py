#!/usr/bin/env python3
"""
PubMed Trial Enricher v2 — Smart Multi-Strategy Search

Instead of sending raw trial names to PubMed, this extracts:
  • Trial acronyms (CHECKMATE-025, KEYNOTE-522)
  • Drug names (pembrolizumab, cisplatin) via suffix detection
  • Author names (Baratti et al. 2013)
  • NCT / protocol numbers
Then constructs optimal PubMed E-utilities queries with fallback strategies.

Usage:
    python pubmed_enricher.py                          # Use NCBI_API_KEY from env
    python pubmed_enricher.py --api-key YOUR_KEY       # Provide key directly
    python pubmed_enricher.py --force                  # Re-query all trials
    python pubmed_enricher.py --dry-run                # Preview queries
    python pubmed_enricher.py --max 50                 # Limit for testing

Called automatically by: sync_and_deploy.py --pubmed
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
REQUEST_DELAY = 0.20

NCCN_REF_PATTERN = re.compile(r"^\d{6,}")
ET_AL_PATTERN = re.compile(r"\((.+?)\s+et\s+al\.?\s+\d{4}\)")

DRUG_SUFFIXES = re.compile(
    r"\b(\w+(?:mab|nib|mide|mus|stat|parib|sertib|ciclib|dent|cept|ximab|zumab|tinib|lisib|rafenib|zomib|cycline|platin|tecan|inib|mib|parib|aciclib))\b",
    re.IGNORECASE,
)
KNOWN_DRUGS = re.compile(
    r"\b(Pembrolizumab|Nivolumab|Atezolizumab|Avelumab|Durvalumab|Ipilimumab|"
    r"Bevacizumab|Cetuximab|Panitumumab|Trastuzumab|Pertuzumab|Rituximab|"
    r"Cisplatin|Carboplatin|Oxaliplatin|Gemcitabine|Paclitaxel|Docetaxel|"
    r"Doxorubicin|Epirubicin|Irinotecan|Capecitabine|Fluorouracil|Methotrexate|"
    r"Cyclophosphamide|Ifosfamide|Etoposide|Topotecan|Vinorelbine|Vinblastine|"
    r"Vincristine|Dacarbazine|Temozolomide|Lomustine|Procarbazine|"
    r"Imatinib|Dasatinib|Nilotinib|Erlotinib|Gefitinib|Afatinib|Osimertinib|"
    r"Sunitinib|Sorafenib|Pazopanib|Cabozantinib|Axitinib|Lenvatinib|Regorafenib|"
    r"Vemurafenib|Dabrafenib|Trametinib|Cobimetinib|Binimetinib|"
    r"Encorafenib|Larotrectinib|Entrectinib|Crizotinib|Alectinib|Ceritinib|"
    r"Brigatinib|Lorlatinib|Palbociclib|Ribociclib|Abemaciclib|"
    r"Olaparib|Niraparib|Rucaparib|Talazoparib|Veliparib|"
    r"Pomalidomide|Lenalidomide|Thalidomide|Bortezomib|Carfilzomib|Ixazomib|"
    r"Daratumumab|Elotuzumab|Isatuximab|Belantamab|Selinexor|Venetoclax|"
    r"Abiraterone|Enzalutamide|Apalutamide|Darolutamide|Radium|Lutetium|"
    r"Tisotumab|Sacituzumab|Trastuzumab|Enfortumab|Cemiplimab|Dostarlimab|"
    r"Relatlimab|Toripalimab|Tislelizumab|Camrelizumab|Sintilimab|"
    r"Copanlisib|Idelalisib|Duvelisib|Tazemetostat|"
    r"Bispecific|CAR[- ]T|BCMA|CD19|CD20|CD30|CD33|CD38|CDK4\/6|"
    r"BRAF|MEK|EGFR|ALK|ROS1|RET|NTRK|HER2|PD-1|PD-L1|CTLA-4|PARP|mTOR|PI3K|FGFR|"
    r"VEGF|HDAC|BTK|FLT3|IDH|JAK|KRAS|BRCA|MSI|dMMR|TMB)\b",
    re.IGNORECASE,
)

CANCER_TERMS = re.compile(
    r"\b(Cancer|Carcinoma|Sarcoma|Lymphoma|Leukemia|Myeloma|Melanoma|"
    r"Mesothelioma|Glioma|Blastoma|Neoplasm|Tumor|Malignancy|"
    r"Breast|Lung|Colon|Rectal|Gastric|Pancreatic|Ovarian|Cervical|"
    r"Endometrial|Uterine|Prostate|Bladder|Renal|Hepatocellular|HCC|"
    r"Cholangiocarcinoma|Thyroid|Head and Neck|Oesophageal|Esophageal|"
    r"Glioblastoma|Neuroblastoma|Thymic|Thymoma|Mesothelioma|Testicular|"
    r"Penile|Vulvar|Vaginal|Anal|Kaposi|Merkel|Neuroendocrine|GIST|"
    r"Advanced|Metastatic|Recurrent|Refractory|Unresectable|Inoperable)\b",
    re.IGNORECASE,
)

AUTHOR_YEAR = re.compile(r"^([A-Z][a-z]+(?:\s+(?:et|&)\s+al\.?)?)[\s,;]*[\(\[\.]?\s*(\d{4})", re.IGNORECASE)
NCT_PATTERN = re.compile(r"NCT\d{8}", re.IGNORECASE)
BASED_ON_PATTERN = re.compile(r"^based\s+(on|upon)\s", re.IGNORECASE)
DESCRIPTIVE_PREFIX = re.compile(r"^(a|an)\s+(phase|randomi[sz]ed|open[-\s]label|multi[-\s]cohort)", re.IGNORECASE)
COMBINED_TRIAL = re.compile(r"^([A-Z][A-Z0-9\-_\. ]{2,25})(?:\s*;\s*|\s+(?:and|&)\s+)(.+)", re.IGNORECASE)


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
    if NCCN_REF_PATTERN.match(name):
        m = ET_AL_PATTERN.search(name)
        if m:
            return m.group(1).strip()
        return ""
    name = re.sub(r"\s*trial\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*study\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*(?:phase\s*[IV1-3]+)\s*$", "", name, flags=re.IGNORECASE)
    return name.strip()


def normalize_filename(name: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
    safe = re.sub(r"_+", "_", safe)
    safe = safe.strip("_")
    if len(safe) > 100:
        safe = safe[:100]
    return safe or hashlib.md5(name.encode()).hexdigest()[:12]


def extract_key_terms(name: str) -> dict:
    result = {
        "acronyms": [],
        "drugs": [],
        "cancers": [],
        "authors": [],
        "year": "",
        "nct_ids": [],
        "is_based_on": False,
        "is_descriptive": False,
    }

    result["is_based_on"] = bool(BASED_ON_PATTERN.match(name))
    result["is_descriptive"] = bool(DESCRIPTIVE_PREFIX.match(name))

    for m in NCT_PATTERN.finditer(name):
        result["nct_ids"].append(m.group(0))

    for m in KNOWN_DRUGS.finditer(name):
        result["drugs"].append(m.group(0))
    if not result["drugs"]:
        for m in DRUG_SUFFIXES.finditer(name):
            result["drugs"].append(m.group(0))

    for m in CANCER_TERMS.finditer(name):
        result["cancers"].append(m.group(0))

    m = AUTHOR_YEAR.match(name)
    if m:
        result["authors"].append(m.group(1).strip())
        result["year"] = m.group(2)

    m = COMBINED_TRIAL.match(name)
    if m:
        result["acronyms"].append(m.group(1).strip())
        m2 = COMBINED_TRIAL.match(m.group(2).strip())
        if m2:
            result["acronyms"].append(m2.group(1).strip())
    else:
        short = re.match(r"^([A-Z][A-Z0-9\-_\. ]{2,30})$", name)
        if short:
            result["acronyms"].append(name.strip())

    return result


def build_queries(name: str) -> list[str]:
    terms = extract_key_terms(name)

    if terms["is_based_on"] or (not terms["acronyms"] and not terms["drugs"] and not terms["authors"] and not terms["nct_ids"] and len(name) < 5):
        return []

    queries = []

    for nct in terms["nct_ids"]:
        queries.append(f'{nct}[Secondary Source ID]')
        queries.append(f'{nct}[All Fields]')

    for acronym in terms["acronyms"]:
        clean = acronym.strip().strip('."\';:')
        queries.append(f'"{clean}"[Title]')
        queries.append(f'{clean}[Title] AND (cancer OR carcinoma OR tumor OR neoplasm)[Title/Abstract]')

    if terms["authors"] and terms["year"]:
        author = terms["authors"][0]
        queries.append(f'{author}[Author] AND {terms["year"]}[Date - Publication]')
        queries.append(f'{author}[Author] AND ({terms["year"]}[Date - Publication] OR {terms["year"]}[Date - Create])')

    drugs = list(dict.fromkeys(terms["drugs"]))[:3]
    cancers = list(dict.fromkeys(terms["cancers"]))[:2]

    if drugs:
        drug_q = " OR ".join(f'"{d}"[Title/Abstract]' for d in drugs)
        base = f'({drug_q})'
        if cancers:
            cancer_q = " OR ".join(f'"{c}"[Title/Abstract]' for c in cancers)
            base += f' AND ({cancer_q})'
        queries.append(f'{base} AND (trial[Title/Abstract] OR study[Title/Abstract] OR phase[Title])')
        queries.append(f'{base} AND clinical trial[Publication Type]')

    if terms["is_descriptive"] and not terms["acronyms"]:
        short = name[:200]
        queries.append(f'"{short}"[Title]')

    if not queries:
        if len(name) <= 60:
            queries.append(f'"{name}"[Title/Abstract] AND (trial OR study)[Title/Abstract]')
        elif len(name) <= 100:
            short = " ".join(name.split()[:5])
            queries.append(f'"{short}"[Title/Abstract] AND clinical trial[Publication Type]')

    return queries


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

        m_journal = re.search(r"<ISOAbbreviation>(.+?)</ISOAbbreviation>", text)
        if not m_journal:
            m_journal = re.search(r"<Title>(.+?)</Title>", text[: text.find("<Abstract") if "<Abstract" in text else 2000], re.DOTALL)
        if m_journal:
            journal = re.sub(r"<[^>]+>", "", m_journal.group(1)).strip()

        m_year = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", text, re.DOTALL)
        if m_year:
            year = m_year.group(1)

        for m in re.finditer(r"<Author[^>]*>.*?<LastName>(.+?)</LastName>.*?<Initials>(.+?)</Initials>", text, re.DOTALL):
            authors.append(f"{m.group(1)} {m.group(2)}")

        m_doi = re.search(r'<ArticleId IdType="doi">(.+?)</ArticleId>', text)
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

    parser = argparse.ArgumentParser(description="Smart PubMed trial enrichment for oncology handbook")
    parser.add_argument("--api-key", type=str, default=None, help="NCBI API key")
    parser.add_argument("--force", action="store_true", help="Re-query all trials")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--max", type=int, default=0, help="Limit trials (testing)")
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

    to_query: list[str] = []
    skipped = 0
    for name in sorted(all_trials):
        terms = extract_key_terms(name)
        queries = build_queries(name)
        if not queries and terms["is_based_on"]:
            skipped += 1
            continue
        if not queries and not terms["acronyms"] and not terms["drugs"] and not terms["authors"] and not terms["nct_ids"]:
            skipped += 1
            continue
        if not args.force and is_already_cached(name):
            continue
        to_query.append(name)

    if args.max and 0 < args.max < len(to_query):
        to_query = to_query[: args.max]

    already = len(all_trials) - len(to_query) - skipped
    print(f"Cached: {already}, Skipped (non-trial): {skipped}, To query: {len(to_query)}")

    if args.dry_run:
        print("\n[Dry run] Query strategy preview:")
        for name in to_query[:20]:
            queries = build_queries(name)
            print(f"\n  Trial: {name[:80]}")
            for q in queries[:3]:
                print(f"    -> {q[:120]}")
        return

    if not to_query:
        print("All trials cached or skipped. Done.")
        return

    success = 0
    no_match = 0
    errors = 0
    start_time = time.time()

    for i, name in enumerate(to_query, 1):
        queries = build_queries(name)
        if not queries:
            no_match += 1
            continue

        print(f"[{i}/{len(to_query)}] {name[:55]:<55} ", end="", flush=True)

        pmid = None
        for q in queries[:5]:
            pmid = pubmed_search(q, api_key)
            if pmid:
                break
            time.sleep(0.08)

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
                print(f"OK (PMID:{pmid})")
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

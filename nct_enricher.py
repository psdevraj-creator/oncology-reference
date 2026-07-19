#!/usr/bin/env python3
"""
NCT Verification Enricher — Search ClinicalTrials.gov by trial acronym,
verify NCT IDs, fetch structured outcomes (OS/PFS/HR/ORR), and extract
correct PMID references for PubMed enrichment.

Usage:
    python nct_enricher.py                        # process all uncached trials
    python nct_enricher.py --force                # re-process everything
    python nct_enricher.py --dry-run              # preview only
    python nct_enricher.py --max 20               # limit for testing

Output: data/nct/{trial_name}.json — verified NCT data per trial
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
NCT_DIR = DATA_DIR / "nct"
CACHE_MAX_AGE_DAYS = 30

CT_API = "https://clinicaltrials.gov/api/v2/studies"
REQUEST_DELAY = 0.35

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
    r"Daratumumab|Elotuzumab|Isatuximab|Selinexor|Venetoclax|"
    r"Abiraterone|Enzalutamide|Apalutamide|Darolutamide|Radium|Lutetium|"
    r"Tisotumab|Sacituzumab|Enfortumab|Cemiplimab|Dostarlimab|"
    r"Relatlimab|Toripalimab|Tislelizumab|Camrelizumab|Sintilimab|"
    r"T-DM1|T-DXd|Enhertu|Keytruda|Opdivo|Yervoy|Tecentriq|Imfinzi|Bavencio)\b",
    re.IGNORECASE,
)

NCT_PATTERN = re.compile(r"NCT\d{8}", re.IGNORECASE)
ACRONYM_PATTERN = re.compile(r"^([A-Z][A-Z0-9\-_\/]{2,25}(?:\s+[A-Z0-9\-_\/]{1,15})?)$")
AUTHOR_YEAR = re.compile(r"^\s*[A-Z][a-z]+.*\d{4}")

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "was",
    "with", "from", "data", "based", "phase", "trial", "study", "analysis",
    "multiple", "randomised", "randomized", "open", "label", "registry", "cohort",
    "series", "et", "al", "patients", "patient", "single", "arm", "meta",
    "integrated", "subgroup", "multicenter", "retrospective", "prospective",
    "single-arm", "two", "three", "all", "iv", "iii", "ii", "i",
}


def normalize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s*trial\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*study\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*(?:phase\s*[IV1-3]+)\s*$", "", name, flags=re.IGNORECASE)
    return name.strip()


def looks_like_acronym(s: str) -> bool:
    """Check if a string looks like a trial acronym (not plain English)."""
    if not s:
        return False
    words = s.split()
    if len(words) > 5:
        return False
    # Must have at least one uppercase-only or digit-containing token
    has_acro_token = False
    for w in words:
        if re.match(r"^[A-Z0-9\-_\/]+$", w) and len(w) >= 2:
            has_acro_token = True
            break
    if not has_acro_token:
        return False
    # Must not be all stop words
    significant = [w for w in words if w.lower() not in STOP_WORDS]
    if len(significant) < 1:
        return False
    # Must not look like an author citation
    if re.search(r"\bet\s+al\b", s, re.I):
        return False
    return True


def extract_acronym(name: str) -> Optional[str]:
    """Extract the most likely trial acronym from a trial name string."""
    name = normalize_name(name)

    # Already a clean acronym?
    if ACRONYM_PATTERN.match(name) and looks_like_acronym(name):
        return name.strip(' "\';:.')

    # "TRIAL_NAME (NCTxxxxxxxx)" → extract TRIAL_NAME
    m_nct = re.match(r"^([A-Z][A-Za-z0-9\-_ ]{3,40})\s*\(NCT\d{8}\)", name)
    if m_nct:
        candidate = m_nct.group(1).strip()
        if looks_like_acronym(candidate):
            return candidate

    # "ACRONYM (Author et al. Year)" → extract ACRONYM
    m_author = re.match(r"^([A-Z][A-Z0-9\-_\/ ]{3,30})\s+\([A-Z][a-z]+.*\d{4}\)", name)
    if m_author:
        candidate = m_author.group(1).strip()
        if looks_like_acronym(candidate):
            return candidate

    # "ACRONYM; ACRONYM2" → first one
    m_multi = re.match(r"^([A-Z][A-Z0-9\-_\/ ]{3,30})\s*[;,+&]", name)
    if m_multi:
        candidate = m_multi.group(1).strip()
        if looks_like_acronym(candidate):
            return candidate

    # "ACRONYM phase II/III" → extract acronym
    m_phase = re.match(r"^([A-Z][A-Z0-9\-_\/ ]{3,30})\s+phase\s", name, re.I)
    if m_phase:
        candidate = m_phase.group(1).strip()
        if looks_like_acronym(candidate):
            return candidate

    return None


def collect_all_trials() -> list[tuple[str, str]]:
    """Collect trial names with their site_id. Returns [(site_id, trial_name), ...]."""
    trials: list[tuple[str, str]] = []
    seen = set()

    for jf in sorted(MERGED_DIR.glob("*.json")):
        site_id = jf.stem
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in data.get("regimens", []):
            td = r.get("trial_data", {})
            tn = (isinstance(td, dict) and td.get("trial_name", "") or "").strip()
            if tn and tn not in seen:
                seen.add(tn)
                trials.append((site_id, tn))

    also = set()
    for site_dir in sorted(INTERMEDIATE_DIR.iterdir()):
        if not site_dir.is_dir():
            continue
        sid = site_dir.name
        for jf in sorted(site_dir.glob("*.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            for t in data.get("tier_2_handbook", {}).get("key_trials", []):
                if not isinstance(t, dict):
                    continue
                for k in ("acronym", "full_name"):
                    tn = (t.get(k) or "").strip()
                    if tn and tn not in seen:
                        seen.add(tn)
                        also.add(tn)
    for tn in sorted(also):
        trials.append(("", tn))

    return trials


def search_ctgov(acronym: str) -> list[dict]:
    """Search ClinicalTrials.gov by trial acronym. Returns list of study summaries."""
    url = f"{CT_API}?query.term={requests.utils.quote(acronym)}+AND+cancer&pageSize=5&format=json"
    try:
        resp = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        return data.get("studies", [])
    except Exception:
        return []


def fetch_study(nct_id: str) -> Optional[dict]:
    """Fetch full study record from CT.gov."""
    url = f"{CT_API}/{nct_id}?format=json"
    try:
        resp = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def title_similarity(a: str, b: str) -> float:
    """Simple word overlap similarity score between two titles."""
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0
    intersection = wa & wb
    return len(intersection) / min(len(wa), len(wb))


def extract_acronym_features(name: str) -> dict:
    """Extract drug names and cancer terms from trial name for matching."""
    drugs = [m.group(0) for m in KNOWN_DRUGS.finditer(name)]
    return {"drugs": list(dict.fromkeys(drugs)), "parts": [p.strip() for p in name.split() if len(p.strip()) > 2]}


def match_trial(acronym: str, trial_name: str, studies: list[dict]) -> Optional[str]:
    """Find best matching NCT ID from search results. Returns NCT ID or None."""
    if not studies:
        return None

    acro_feat = extract_acronym_features(trial_name)
    best_score = 0
    best_nct = None

    for study in studies:
        prot = study.get("protocolSection", {})
        ident = prot.get("identificationModule", {})
        nct = ident.get("nctId", "")
        brief = ident.get("briefTitle", "")
        official = ident.get("officialTitle", "")

        score = 0
        # Acronym match in brief title
        if acronym.lower() in brief.lower():
            score += 40
        if acronym.lower() in official.lower():
            score += 30

        # Title similarity
        sim_brief = title_similarity(trial_name, brief)
        sim_official = title_similarity(trial_name, official)
        score += max(sim_brief, sim_official) * 30

        # Drug name match
        for drug in acro_feat["drugs"]:
            if drug.lower() in brief.lower():
                score += 10

        # Cancer term check
        conditions = prot.get("conditionsModule", {}).get("conditions", [])
        for cond in conditions:
            if any(t.lower() in cond.lower() for t in ["cancer", "carcinoma", "sarcoma", "melanoma", "lymphoma", "leukemia", "myeloma"]):
                score += 5
                break

        # Phase check — must be an interventional trial
        design = prot.get("designModule", {})
        if design.get("studyType") == "INTERVENTIONAL":
            score += 5

        if score > best_score:
            best_score = score
            best_nct = nct

    # Require minimum score to return
    if best_score < 30:
        return None
    return best_nct


def extract_outcomes(study: dict) -> dict:
    """Extract structured outcomes from a CT.gov study record."""
    identity = study.get("protocolSection", {}).get("identificationModule", {})
    design = study.get("protocolSection", {}).get("designModule", {})
    status = study.get("protocolSection", {}).get("statusModule", {})
    refs = study.get("protocolSection", {}).get("referencesModule", {})

    outcomes = {
        "nct_id": identity.get("nctId", ""),
        "brief_title": identity.get("briefTitle", ""),
        "official_title": identity.get("officialTitle", ""),
        "phase": design.get("phases", []),
        "enrollment": design.get("enrollmentInfo", {}).get("count", None),
        "status": status.get("overallStatus", ""),
        "has_results": study.get("hasResults", False),
        "pmids": [],
        "outcomes": [],
    }

    # Extract PMIDs from references
    for ref in refs.get("references", []):
        pmid = ref.get("pmid", "")
        if pmid:
            outcomes["pmids"].append({
                "pmid": pmid,
                "type": ref.get("type", ""),
                "citation": ref.get("citation", "")
            })

    # Extract outcome measures
    results = study.get("resultsSection", {})
    om_module = results.get("outcomeMeasuresModule", {})
    measures = om_module.get("outcomeMeasures", [])

    for measure in measures:
        out = {
            "type": measure.get("type", ""),
            "title": measure.get("title", ""),
            "description": measure.get("description", "")[:300],
        }

        classes = measure.get("classes", [])
        for cls in classes:
            cat_data = {"class": cls.get("title", ""), "arms": []}
            for cat in cls.get("categories", []):
                arm = {"title": cat.get("title", ""), "measurements": []}
                for m in cat.get("measurements", []):
                    arm["measurements"].append({
                        "title": m.get("title", ""),
                        "value": m.get("value", m.get("paramValue", "")),
                        "unit": m.get("unit", ""),
                        "lower_limit": m.get("lowerLimit", ""),
                        "upper_limit": m.get("upperLimit", ""),
                    })
                cat_data["arms"].append(arm)
            out["data"] = cat_data

        outcomes["outcomes"].append(out)

    return outcomes


def cache_path(trial_name: str) -> Path:
    safe = re.sub(r"[^a-z0-9_]", "_", trial_name.lower().strip())
    safe = re.sub(r"_+", "_", safe).strip("_")[:80]
    NCT_DIR.mkdir(parents=True, exist_ok=True)
    return NCT_DIR / f"{safe}.json"


def is_cached(trial_name: str) -> bool:
    cp = cache_path(trial_name)
    if not cp.exists():
        return False
    try:
        data = json.loads(cp.read_text(encoding="utf-8"))
        qd = data.get("query_date", "")
        if qd:
            dt = datetime.fromisoformat(qd)
            if datetime.now() - dt < timedelta(days=CACHE_MAX_AGE_DAYS):
                return True
    except Exception:
        pass
    return False


def write_cache(trial_name: str, data: dict):
    cp = cache_path(trial_name)
    data["query_date"] = datetime.now().isoformat()
    data["trial_name"] = trial_name
    cp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ClinicalTrials.gov enricher for oncology trials")
    parser.add_argument("--force", action="store_true", help="Re-process all trials")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--max", type=int, default=0, help="Limit trials for testing")
    args = parser.parse_args()

    print("Collecting trial names...")
    all_trials = collect_all_trials()
    print(f"Total trial mentions: {len(all_trials)}")

    # Filter to trials with recognizable acronyms
    to_process = []
    for site_id, name in all_trials:
        acronym = extract_acronym(name)
        if acronym and len(acronym) >= 3:
            if not args.force and is_cached(name):
                continue
            to_process.append((site_id, name, acronym))

    print(f"Trials with recognizable acronyms: {len(to_process)}")
    cached = sum(1 for _, n in all_trials if extract_acronym(n) and is_cached(n))
    print(f"Already cached: {cached}")
    print(f"To process: {len(to_process)}")

    if args.max and 0 < args.max < len(to_process):
        to_process = to_process[:args.max]

    if args.dry_run:
        print("\n[Dry run] Preview:")
        for site_id, name, acronym in to_process[:30]:
            print(f"  [{site_id}] '{name}' → acronym: {acronym}")
        return

    if not to_process:
        print("All trials cached. Done.")
        return

    success = 0
    no_match = 0
    verified_nct = 0
    has_results = 0
    start_time = time.time()

    for i, (site_id, name, acronym) in enumerate(to_process, 1):
        print(f"[{i}/{len(to_process)}] {acronym:<30} ", end="", flush=True)

        # Search CT.gov
        studies = search_ctgov(acronym)
        if not studies:
            print("NO MATCH")
            no_match += 1
            time.sleep(REQUEST_DELAY)
            continue

        nct_id = match_trial(acronym, name, studies)
        if not nct_id:
            print(f"NO NCT (best={len(studies)} results)")
            no_match += 1
            time.sleep(REQUEST_DELAY)
            continue

        # Fetch full study record
        study = fetch_study(nct_id)
        if not study:
            print(f"FETCH FAIL ({nct_id})")
            time.sleep(REQUEST_DELAY)
            continue

        outcomes = extract_outcomes(study)
        outcomes["acronym"] = acronym
        outcomes["site_id"] = site_id
        write_cache(name, outcomes)

        res_tag = "+RESULTS" if outcomes["has_results"] else ""
        pmid_tag = f", {len(outcomes['pmids'])} PMIDs" if outcomes["pmids"] else ""
        print(f"OK → {nct_id} ({outcomes['phase']}, n={outcomes['enrollment']}{res_tag}{pmid_tag})")
        success += 1
        verified_nct += 1
        if outcomes["has_results"]:
            has_results += 1

        if i < len(to_process):
            time.sleep(REQUEST_DELAY)
        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (len(to_process) - i) / rate if rate > 0 else 0
            print(f"  --- [{i}/{len(to_process)}] {rate:.1f}/s, ~{remaining:.0f}s left, hit={success}/{i} ---")

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.0f}s")
    print(f"  Verified NCT IDs: {verified_nct}")
    print(f"  With results data: {has_results}")
    print(f"  No match: {no_match}")
    print(f"  Cache: {len(list(NCT_DIR.glob('*.json')))} files")


if __name__ == "__main__":
    main()

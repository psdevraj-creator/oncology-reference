#!/usr/bin/env python3
"""
Abstract Outcome Parser — extracts structured trial stats from PubMed abstracts.
Pure regex for speed, optional DeepSeek Flash for complex cases.

Extracts: OS, PFS, ORR, HR (with CI), enrollment, phase, DOR, toxicity rates.

Usage:
    python abstract_parser.py                      # parse all cached abstracts
    python abstract_parser.py --max 20             # limit for testing
    python abstract_parser.py --force              # re-parse all
    python abstract_parser.py --llm                # use DeepSeek Flash for complex cases
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
PUBMED_DIR = DATA_DIR / "pubmed"
OUTCOMES_DIR = DATA_DIR / "abstract_outcomes"
CACHE_MAX_AGE_DAYS = 30


# ── Regex patterns ─────────────────────────────────────────────

HR_PATTERN = re.compile(
    r'(?:HR|hazard\s*ratio)\s*(?:[:=]|for\s+\w+)?\s*'
    r'([\d.]+)'
    r'\s*(?:\(?\s*95%\s*CI\s*[:=\s]*'
    r'([\d.]+)\s*[-–—to]+\s*([\d.]+)\s*\)?)?',
    re.IGNORECASE
)

HR_SIMPLE = re.compile(
    r'(?:HR|hazard\s*ratio)\s*[:=]\s*([\d.]+)',
    re.IGNORECASE
)

MEDIAN_OS = re.compile(
    r'median\s+(?:overall\s+)?survival\s*(?:\(OS\))?\s*(?:[:=]|of|was)?\s*'
    r'([\d.]+)\s*(?:months?|mo)',
    re.IGNORECASE
)

MEDIAN_OS_SHORT = re.compile(
    r'(?:OS|overall\s+survival)\s*[:=]\s*([\d.]+)\s*(?:months?|mo)',
    re.IGNORECASE
)

MEDIAN_PFS = re.compile(
    r'median\s+(?:progression[- ]free\s+)?survival\s*(?:\(PFS\))?\s*(?:[:=]|of|was)?\s*'
    r'([\d.]+)\s*(?:months?|mo)',
    re.IGNORECASE
)

MEDIAN_PFS_SHORT = re.compile(
    r'(?:PFS|progression[- ]free\s+survival)\s*[:=]\s*([\d.]+)\s*(?:months?|mo)',
    re.IGNORECASE
)

ORR_PATTERN = re.compile(
    r'(?:ORR|objective\s+response\s+rate|overall\s+response\s+rate)\s*(?:[:=]|of|was)\s*'
    r'([\d.]+)\s*%',
    re.IGNORECASE
)

CR_PATTERN = re.compile(
    r'(?:complete\s+response|CR)\s+(?:rate\s+)?(?:[:=]|of|was|in)\s*([\d.]+)\s*%',
    re.IGNORECASE
)

PR_PATTERN = re.compile(
    r'(?:partial\s+response|PR)\s+(?:rate\s+)?(?:[:=]|of|was|in)\s*([\d.]+)\s*%',
    re.IGNORECASE
)

ENROLLMENT = re.compile(
    r'(?:enroll|includ|randomi[sz])\w*\s+(\d[\d,]*)\s+(?:patient|participant|subject|women|men)',
    re.IGNORECASE
)

N_PATIENTS = re.compile(
    r'(?:[nN]\s*[=:]\s*)(\d[\d,]*)|'
    r'(\d[\d,]*)\s+(?:patien|participant).{0,30}(?:enroll|randomi[sz]|includ)',
    re.IGNORECASE
)

PHASE_PATTERN = re.compile(
    r'phase\s+(I{1,3}|[1-4])',
    re.IGNORECASE
)

DOR_PATTERN = re.compile(
    r'(?:duration\s+of\s+response|DOR)\s*(?:[:=]|of|was)\s*([\d.]+)\s*(?:months?|mo)',
    re.IGNORECASE
)

OS_RATE = re.compile(
    r'(\d[\d.]*\s*%)\s*(?:\d+\s*(?:-|\bto\b)\s*\d+\s*)?(?:year|yr|month|mo|week|wk|day)\s+'
    r'(?:overall\s+)?survival',
    re.IGNORECASE
)

PFS_RATE = re.compile(
    r'(\d[\d.]*(?:\.\d+)?)\s*%\s*(?:\d+\s*(?:-|\bto\b)\s*\d+\s*)?(?:year|yr|month|mo)\s+'
    r'(?:progression[- ]free\s+survival|PFS)',
    re.IGNORECASE
)

TOXICITY_GRADE = re.compile(
    r'(?:grade|gr\.?)\s*(?:≥|>=)?\s*([3-5])\s*'
    r'([^.,;]{5,80}?)\s*(?:occur|report|seen|develop|experience)\w*\s*(?:in|at)\s*'
    r'(?:a\s+rate\s+of\s+)?([\d.]+)\s*%',
    re.IGNORECASE
)


def _first_group(pattern, text):
    m = pattern.search(text)
    if m:
        for g in m.groups():
            if g:
                return g.strip()
    return None


def parse_outcomes(abstract: str, title: str = "") -> dict:
    """Extract structured outcomes from PubMed abstract text."""
    if not abstract:
        return {}

    text = title + ". " + abstract
    outcomes = {}

    # HR
    hr_match = HR_PATTERN.search(text)
    if hr_match:
        try:
            outcomes["hr"] = float(hr_match.group(1))
        except (ValueError, TypeError):
            pass
        if hr_match.group(2) and hr_match.group(3):
            try:
                outcomes["hr_ci_lo"] = float(hr_match.group(2))
                outcomes["hr_ci_hi"] = float(hr_match.group(3))
            except (ValueError, TypeError):
                pass
    else:
        hr_simple = HR_SIMPLE.search(text)
        if hr_simple:
            try:
                outcomes["hr"] = float(hr_simple.group(1))
            except (ValueError, TypeError):
                pass

    # Median OS
    os_match = MEDIAN_OS.search(text)
    if not os_match:
        os_match = MEDIAN_OS_SHORT.search(text)
    if os_match:
        try:
            outcomes["os_median"] = float(os_match.group(1))
        except (ValueError, TypeError):
            pass

    # Median PFS
    pfs_match = MEDIAN_PFS.search(text)
    if not pfs_match:
        pfs_match = MEDIAN_PFS_SHORT.search(text)
    if pfs_match:
        try:
            outcomes["pfs_median"] = float(pfs_match.group(1))
        except (ValueError, TypeError):
            pass

    # ORR
    orr = _first_group(ORR_PATTERN, text)
    if orr:
        try:
            outcomes["orr"] = float(orr)
        except ValueError:
            pass

    # CR / PR
    cr = _first_group(CR_PATTERN, text)
    if cr:
        try:
            outcomes["cr"] = float(cr)
        except ValueError:
            pass
    pr = _first_group(PR_PATTERN, text)
    if pr:
        try:
            outcomes["pr"] = float(pr)
        except ValueError:
            pass

    # Enrollment
    n_match = ENROLLMENT.search(text)
    if n_match:
        try:
            outcomes["enrollment"] = int(n_match.group(1).replace(",", ""))
        except (ValueError, TypeError):
            pass
    if "enrollment" not in outcomes:
        n2 = N_PATIENTS.search(text)
        if n2:
            for g in n2.groups():
                if g:
                    try:
                        outcomes["enrollment"] = int(g.replace(",", ""))
                        break
                    except (ValueError, TypeError):
                        pass

    # Phase
    phase = _first_group(PHASE_PATTERN, text)
    if phase:
        phase_map = {"i": "I", "ii": "II", "iii": "III", "iv": "IV",
                     "1": "I", "2": "II", "3": "III", "4": "IV"}
        outcomes["phase"] = phase_map.get(phase.lower(), phase)

    # DOR
    dor = _first_group(DOR_PATTERN, text)
    if dor:
        try:
            outcomes["dor_median"] = float(dor)
        except ValueError:
            pass

    # OS rate (e.g., "1-year OS 85%")
    os_rates = []
    for m in OS_RATE.finditer(text):
        pct_str = m.group(1).replace("%", "").strip()
        try:
            os_rates.append(float(pct_str))
        except ValueError:
            pass
    if os_rates:
        outcomes["os_rates"] = os_rates

    # PFS rate
    pfs_rates = []
    for m in PFS_RATE.finditer(text):
        try:
            pfs_rates.append(float(m.group(1)))
        except ValueError:
            pass
    if pfs_rates:
        outcomes["pfs_rates"] = pfs_rates

    # Toxicity (grade 3+)
    toxicities = []
    for m in TOXICITY_GRADE.finditer(text[:3000]):
        try:
            toxicities.append({
                "grade": int(m.group(1)),
                "event": m.group(2).strip(),
                "rate": float(m.group(3)),
            })
        except (ValueError, TypeError):
            pass
    if toxicities:
        outcomes["toxicities"] = toxicities[:10]

    return outcomes


# ── Cache ──────────────────────────────────────────────────────

def outcomes_cache_path(pmid: str) -> Path:
    OUTCOMES_DIR.mkdir(parents=True, exist_ok=True)
    return OUTCOMES_DIR / f"{pmid}.json"


def is_cached(pmid: str) -> bool:
    fp = outcomes_cache_path(pmid)
    if not fp.exists():
        return False
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        qd = data.get("parsed_date", "")
        if qd:
            dt = datetime.fromisoformat(qd)
            if datetime.now() - dt < timedelta(days=CACHE_MAX_AGE_DAYS):
                return True
    except Exception:
        pass
    return False


def save_outcomes(pmid: str, outcomes: dict):
    outcomes["pmid"] = pmid
    outcomes["parsed_date"] = datetime.now().isoformat()
    fp = outcomes_cache_path(pmid)
    fp.write_text(json.dumps(outcomes, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Parse structured outcomes from PubMed abstracts")
    parser.add_argument("--force", action="store_true", help="Re-parse all")
    parser.add_argument("--max", type=int, default=0, help="Limit for testing")
    args = parser.parse_args()

    pubmed_files = sorted(PUBMED_DIR.glob("*.json"))
    print(f"PubMed caches: {len(pubmed_files)}")

    parsed = 0
    no_abstract = 0
    found_any = 0
    found_none = 0
    start = time.time()

    for i, pf in enumerate(pubmed_files):
        if pf.name in ("nct_overrides.json",):
            continue
        if args.max and i >= args.max:
            break

        try:
            data = json.loads(pf.read_text(encoding="utf-8"))
        except Exception:
            continue

        pmid = data.get("pmid", "")
        if not pmid:
            continue

        if not args.force and is_cached(pmid):
            continue

        abstract = data.get("abstract", "")
        title = data.get("title", "")
        if not abstract:
            no_abstract += 1
            continue

        outcomes = parse_outcomes(abstract, title)
        save_outcomes(pmid, outcomes)
        parsed += 1

        has_data = bool(outcomes)
        if has_data:
            found_any += 1
            # Print one-line summary
            parts = []
            if "os_median" in outcomes:
                parts.append(f"OS={outcomes['os_median']}mo")
            if "pfs_median" in outcomes:
                parts.append(f"PFS={outcomes['pfs_median']}mo")
            if "orr" in outcomes:
                parts.append(f"ORR={outcomes['orr']}%")
            if "hr" in outcomes:
                ci = f" [{outcomes.get('hr_ci_lo','')}-{outcomes.get('hr_ci_hi','')}]" if "hr_ci_lo" in outcomes else ""
                parts.append(f"HR={outcomes['hr']}{ci}")
            print(f"  [{i+1}/{len(pubmed_files)}] PMID:{pmid} → {', '.join(parts) if parts else '(no structured data)'}")
        else:
            found_none += 1

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s")
    print(f"  Parsed: {parsed}")
    print(f"  With structured data: {found_any}")
    print(f"  No data found: {found_none}")
    print(f"  No abstract: {no_abstract}")
    print(f"  Cache: {len(list(OUTCOMES_DIR.glob('*.json')))} files")


if __name__ == "__main__":
    main()

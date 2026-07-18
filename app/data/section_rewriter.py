"""
Unified section rewriter: DeepSeek Flash restructures handbook prose into
chart-ready structured JSON for all 24 sections across all 41 sites.

Usage:
    python -m app.data.section_rewriter                    # process all uncached
    python -m app.data.section_rewriter --force            # reprocess all
    python -m app.data.section_rewriter --site breast      # single site only
    python -m app.data.section_rewriter --section molecular_pathogenesis  # single section
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
load_dotenv(dotenv_path=str(SOURCE_PROJECT / ".env"), override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INTERMEDIATE_DIR = PROJECT_ROOT / "data" / "intermediate"
CACHE_DIR = PROJECT_ROOT / "data" / "rewritten" / "sections"

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL") or os.environ.get("LLM_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")


# ── Section rewrite configs ─────────────────────────────────────────────

SECTION_CONFIGS: dict[str, dict] = {
    "epidemiology": {
        "dict_section": True,
        "prompt": """Restructure this epidemiology data into chart-ready JSON. NEVER lose any original text.

The input is a dict with keys like incidence, mortality, trends, demographics (each a text string).

OUTPUT JSON:
{
  "sections": [{"heading": "...", "content": "original text verbatim"}],
  "chart_data": {
    "labels": ["Global", "US", "UK", "Europe"],
    "incidence": [2300000, 300000, 55000, 400000],
    "mortality": [685000, 43000, 11500, 138000]
  },
  "stat_cards": [
    {"label": "Annual Incidence (US)", "value": "~300,000", "icon": "bi-people-fill", "color": "#6366f1"},
    {"label": "Mortality (US)", "value": "~43,000", "icon": "bi-graph-down", "color": "#ef4444"}
  ]
}

Extract NUMBERS: "approximately 300,000 cases" → value: "~300,000". If no exact number, skip that stat card.
ALL original text must appear verbatim in sections[].content. Do not summarize."""},

    "subtypes": {
        "dict_section": True,
        "prompt": """Restructure cancer subtype data into sunburst chart-ready JSON. NEVER lose details.

Input is a list of dicts with name, description, frequency (text like "70-80%").

OUTPUT JSON:
{
  "sections": [{"heading": "Subtypes", "content": "original descriptions verbatim"}],
  "sunburst_data": {
    "labels": ["Breast Cancer", "Ductal", "Lobular", "HER2+"],
    "parents": ["", "Breast Cancer", "Breast Cancer", "Breast Cancer"],
    "values": [100, 75, 15, 10]
  },
  "cards": [
    {"name": "Ductal Carcinoma", "description": "orig text", "frequency": "70-80%", "color": "#6366f1"}
  ]
}

Parse frequency text like "70-80%" into numeric values for the sunburst (use midpoint: 75).
If exact percentages are given, extract them verbatim. ALL original descriptions preserved."""},

    "molecular_pathogenesis": {
        "dict_section": False,
        "prompt": """Restructure molecular pathogenesis prose into a Cytoscape network diagram format. NEVER lose any original text or gene names.

Input is a single long text string describing molecular pathways, genes, and mutations.

OUTPUT JSON:
{
  "sections": [{"heading": "Receptor Tyrosine Kinases", "content": "original verbatim"}, ...],
  "network": {
    "nodes": [
      {"id": "EGFR", "label": "EGFR", "type": "targetable"},
      {"id": "PI3K", "label": "PI3K/AKT", "type": "pathway"},
      {"id": "mTOR", "label": "mTOR", "type": "drug"}
    ],
    "edges": [
      {"source": "EGFR", "target": "PI3K", "type": "activates"},
      {"source": "PI3K", "target": "mTOR", "type": "activates"}
    ]
  },
  "pathway_summaries": [
    {"pathway": "RTK-RAS-RAF", "genes": ["EGFR","KRAS","BRAF"], "targetable": true, "drugs": "Cetuximab, Panitumumab"}
  ]
}

Node types: "pathway", "targetable" (druggable), "drug", "gene".
Edge types: "activates", "inhibits", "binds".
Split prose into sections by biological pathway. Extract every gene/drug name mentioned.
ALL original text preserved verbatim in sections[].content. Do NOT summarize."""},

    "risk_factors": {
        "dict_section": True,
        "prompt": """Restructure risk factor data into waterfall chart format. NEVER lose details.

Input is a list of dicts with factor, type, detail, strength fields.

OUTPUT JSON:
{
  "sections": [{"heading": "Genetic Risk Factors", "content": "verbatim detail text"}],
  "waterfall_data": {
    "labels": ["BRCA1 mutation", "Family history", "Alcohol", "Obesity", "HRT"],
    "values": [45, 25, 12, 10, -5]
  },
  "cards": [
    {"factor": "BRCA1 mutation", "type": "Genetic", "strength": "High", "detail": "...", "color": "#ef4444"}
  ]
}

For values in waterfall: extract OR/RR/% where stated. If no number, estimate relative impact.
ALL original text verbatim. Every factor gets a card. Do not drop any factor."""},

    "protective_factors": {
        "dict_section": False,
        "prompt": """Restructure protective factor list into structured cards. NEVER lose details.

Input is a list of strings. OUTPUT JSON:
{
  "sections": [{"heading": "Protective Factors", "content": "original list verbatim"}],
  "cards": [{"factor": "Breastfeeding", "detail": "Full original text", "color": "#10b981"}]
}
ALL original text. Every factor preserved."""},

    "clinical_features": {
        "dict_section": False,
        "prompt": """Restructure clinical features/symptoms into chart-ready format. NEVER lose details.

Input may be a dict or string describing presenting symptoms, signs, and red flags.

OUTPUT JSON:
{
  "sections": [{"heading": "Presenting Symptoms", "content": "original verbatim"}],
  "chart_data": {"labels": ["Lump", "Pain", "Nipple discharge", "Skin changes"], "values": [70, 30, 15, 10]},
  "symptom_cards": [
    {"name": "Breast lump", "detail": "...", "frequency": "70%", "alarm": false, "color": "#f59e0b"}
  ],
  "alarms": [{"name": "Peau d'orange", "detail": "...", "color": "#ef4444"}]
}
Extract frequency percentages where stated. Mark alarm/red flag symptoms. ALL text verbatim."""},

    "red_flags": {
        "dict_section": False,
        "prompt": """Restructure red flag list into alert cards. NEVER lose details.

Input is a list of strings. OUTPUT JSON:
{
  "sections": [{"heading": "Red Flags", "content": "original verbatim"}],
  "alerts": [{"title": "Haemoptysis", "body": "Full text", "icon": "bi-exclamation-triangle-fill"}]
}
ALL text verbatim. Every red flag preserved."""},

    "investigations": {
        "dict_section": False,
        "prompt": """Restructure investigations into timeline + table format. NEVER lose details.

Input is a dict with keys like imaging, pathology, lab_tests, or a list of test dicts.

OUTPUT JSON:
{
  "sections": [{"heading": "Imaging", "content": "original verbatim"}],
  "timeline": [{"title": "Initial workup", "body": "...", "icon": "bi-camera"}],
  "table_data": {
    "columns": [{"field": "test", "headerName": "Test"}, {"field": "rationale", "headerName": "Rationale"}],
    "rows": [{"test": "Mammogram", "rationale": "..."}]
  }
}
ALL text verbatim in sections. Timeline for diagnostic sequence. Table for test details."""},

    "staging": {
        "dict_section": False,
        "prompt": """Extract structured TNM staging data from prose. NEVER lose details.

Input may be prose text containing T/N/M categories with sizes and descriptions.

OUTPUT JSON:
{
  "sections": [{"heading": "TNM Staging", "content": "original verbatim"}],
  "t_stages": [{"category": "T1", "description": "Tumor <=20mm"}],
  "n_stages": [{"category": "N0", "description": "No nodal involvement"}],
  "m_stages": [{"category": "M0", "description": "No distant metastases"}],
  "stage_groups": [{"stage": "IA", "t": "T1", "n": "N0", "m": "M0", "survival": "99%"}],
  "chart_data": {"stages": ["I","II","III","IV"], "os_5yr": [99, 85, 55, 28]}
}
Extract EXACT survival rates if stated. ALL text verbatim in sections."""},

    "management_principles": {
        "dict_section": True,
        "prompt": """Restructure management principles into flowchart + structured sections.

Input is a dict with keys like overview, by_intent (list), mdt_requirements, performance_status_guide.

OUTPUT JSON:
{
  "sections": [{"heading": "Overview", "content": "original verbatim"}],
  "flowchart": {
    "nodes": [{"id": "n1", "label": "PS 0-1", "type": "decision"}, {"id": "n2", "label": "Curative intent", "type": "treatment"}],
    "edges": [{"source": "n1", "target": "n2", "label": "Yes"}]
  },
  "intent_cards": [{"intent": "Curative", "detail": "...", "color": "#10b981"}]
}
Build a decision flowchart from the by_intent and PS guide data. ALL text verbatim."""},

    "management_pathways": {
        "dict_section": True,
        "prompt": """Transform management pathway decision trees into Cytoscape flowchart data.

Input is a list of pathway objects with pathway_id, title, branching_basis, nodes (each with criteria, options, adjuvant_logic).

OUTPUT JSON:
{
  "sections": [{"heading": "Pathway: First-line systemic therapy", "content": "original verbatim"}],
  "flowcharts": [{
    "title": "First-line systemic",
    "nodes": [{"id": "p1_n1", "label": "ER+/HER2-", "type": "decision"}],
    "edges": [{"source": "p1_n1", "target": "p1_n2", "label": "Endocrine therapy"}]
  }]
}
Create a separate flowchart per pathway. ALL text verbatim in sections. Do NOT simplify criteria."""},

    "pretreatment_evaluation": {
        "dict_section": True,
        "prompt": """Restructure pretreatment evaluation into grouped cards.

Input is a list with category and items fields. OUTPUT JSON:
{
  "sections": [{"heading": "Pretreatment Evaluation", "content": "original verbatim"}],
  "groups": [{"category": "Imaging", "items": [{"text": "...", "recommendation": "Required"}], "color": "#6366f1"}]
}
ALL original text. Preserve category grouping. Every test preserved."""},

    "surgery": {
        "dict_section": True,
        "prompt": """Restructure surgery section into comparison table + procedure cards.

Input is a dict with role, principles, procedures, resectability_criteria.

OUTPUT JSON:
{
  "sections": [{"heading": "Surgical Role", "content": "original verbatim"}],
  "table_data": {
    "columns": [{"field": "procedure", "headerName": "Procedure"}, {"field": "indications", "headerName": "Indications"}],
    "rows": [{"procedure": "Wide local excision", "indications": "..."}]
  },
  "principles": ["Original principle text 1", "Original principle text 2"]
}
ALL text verbatim. Every procedure in table. Principles preserved as list."""},

    "radiation_therapy": {
        "dict_section": True,
        "prompt": """Enrich radiation therapy section with dose visualization data.

Input is a dict with role, principles (list), dose_frameworks (list of dicts), approaches.

OUTPUT JSON:
{
  "sections": [{"heading": "Role", "content": "original verbatim"}],
  "dose_timeline": [{"title": "Conventional fractionation", "body": "50 Gy in 25 fractions over 5 weeks", "icon": "bi-lightning"}],
  "dose_gauges": [{"label": "Total Dose", "value": 50, "unit": "Gy", "color": "#6366f1"}],
  "table_data": {...}
}
Extract EXACT Gy/fractions. ALL text verbatim."""},

    "systemic_therapy": {
        "dict_section": True,
        "prompt": """Enrich systemic therapy section with treatment line timeline and regimen cards.

Input is a dict with overview, by_stage_and_setting (list), key_regimens (list).

OUTPUT JSON:
{
  "sections": [{"heading": "Overview", "content": "original verbatim"}],
  "treatment_timeline": [{"title": "1st line", "body": "...", "icon": "bi-1-circle-fill"}],
  "regimen_cards": [{"name": "AC-T", "setting": "Adjuvant", "drugs": "Doxorubicin, Cyclophosphamide, Paclitaxel", "detail": "..."}]
}
ALL text verbatim. Every regimen/drug preserved. Treatment sequence in timeline order."""},

    "treatment_response_assessment": {
        "dict_section": True,
        "prompt": """Restructure response assessment into timeline + criteria cards.

Input is a dict with timing, response_logic, imaging_recommendations.

OUTPUT JSON:
{
  "sections": [{"heading": "Response Assessment", "content": "original verbatim"}],
  "timeline": [{"title": "Baseline imaging", "body": "...", "icon": "bi-camera"}],
  "criteria_card": {"title": "RECIST 1.1", "detail": "..."}
}
ALL text verbatim."""},

    "surveillance": {
        "dict_section": True,
        "prompt": """Restructure surveillance follow-up into Gantt-style timeline.

Input is a dict with clinical_follow_up_schedule, imaging_strategy, laboratory_monitoring, supportive_follow_up.

OUTPUT JSON:
{
  "sections": [{"heading": "Clinical Follow-up", "content": "original verbatim"}],
  "timeline": [{"title": "Year 1-2: Every 3-4 months", "body": "History, physical exam", "icon": "bi-calendar-check"}],
  "schedule_table": {
    "columns": [{"field": "timepoint", "headerName": "Timepoint"}, {"field": "action", "headerName": "Action"}],
    "rows": [{"timepoint": "Every 3-4 mo (Yr 1-2)", "action": "Clinical exam"}]
  }
}
Extract EXACT intervals and frequencies. ALL text verbatim."""},

    "complications": {
        "dict_section": True,
        "prompt": """Restructure complications into bar chart + severity-coded cards.

Input is a dict with disease_related (list), treatment_related (list).

OUTPUT JSON:
{
  "sections": [{"heading": "Disease-related", "content": "original verbatim"}],
  "chart_data": {
    "labels": ["Lymphedema", "Neutropenia", "Neuropathy", "Fatigue"],
    "values": [25, 40, 30, 60],
    "severities": ["moderate", "severe", "moderate", "mild"]
  },
  "complication_cards": [{"name": "Neutropenia", "incidence": "40%", "severity": "severe", "color": "#ef4444", "detail": "..."}]
}
Extract EXACT incidence percentages. If exact number not stated, estimate from text context. ALL text verbatim."""},

    "supportive_care": {
        "dict_section": True,
        "prompt": """Restructure supportive care into protocol cards.

Input is a dict with keys like overview, nutritional_support, anti_emetic_protocol, gcsf_guidance, vte_prophylaxis, pain_management, psychosocial_support.

OUTPUT JSON:
{
  "sections": [{"heading": "Anti-emetic Protocol", "content": "original verbatim"}],
  "protocol_cards": [{"name": "Highly Emetogenic", "drugs": "NK1 + 5HT3 + Dexamethasone", "detail": "...", "color": "#ef4444"}]
}
ALL text verbatim. Every protocol/drug preserved."""},

    "prognosis": {
        "dict_section": True,
        "prompt": """Restructure prognosis into survival bar chart + stage-stratified cards.

Input is a dict with overall, by_stage (list of dicts), prognostic_factors.

OUTPUT JSON:
{
  "sections": [{"heading": "Overall Prognosis", "content": "original verbatim"}],
  "chart_data": {"stages": ["I","II","III","IV"], "os_5yr": [99, 85, 55, 28]},
  "factor_cards": [{"factor": "ER positivity", "impact": "Favorable", "detail": "...", "color": "#10b981"}]
}
Extract EXACT survival percentages. ALL text verbatim."""},

    "follow_up": {
        "dict_section": True,
        "prompt": """Restructure follow-up into timeline + late effects cards.

Input is a dict with post_curative_treatment, surveillance_rationale, late_effects_screening, recurrence_patterns.

OUTPUT JSON:
{
  "sections": [{"heading": "Post-curative Follow-up", "content": "original verbatim"}],
  "timeline": [{"title": "Year 1-5: Annual mammogram", "body": "...", "icon": "bi-calendar-check"}],
  "late_effects": [{"name": "Cardiotoxicity", "detail": "...", "color": "#ef4444"}]
}
ALL text verbatim."""},

    "clinical_pearls": {
        "dict_section": False,
        "prompt": """Restructure clinical pearls into categorized highlight cards.

Input is a list of strings. OUTPUT JSON:
{
  "sections": [{"heading": "Clinical Pearls", "content": "full original list verbatim"}],
  "cards": [{"text": "...", "category": "Diagnosis", "color": "#f59e0b"}]
}
Infer category from content (Diagnosis, Staging, Treatment, Prognosis, Complications). ALL text verbatim."""},

    "special_situations": {
        "dict_section": False,
        "prompt": """Restructure special situations into accordion cards.

Input is a list of dicts with variable keys. OUTPUT JSON:
{
  "sections": [{"heading": "Special Situations", "content": "original verbatim"}],
  "cards": [{"title": "Pregnancy", "detail": "...", "color": "#ec4899"}]
}
ALL text verbatim. Every situation preserved."""},

    "guidelines_resources": {
        "dict_section": False,
        "prompt": """Restructure guidelines into reference cards with links.

Input is a list of dicts. OUTPUT JSON:
{
  "sections": [{"heading": "Guidelines & Resources", "content": "original verbatim"}],
  "cards": [{"name": "NCCN Guidelines v2.2026", "organisation": "NCCN", "detail": "...", "color": "#6366f1"}]
}
ALL text verbatim."""},
}


# ── Processing logic ────────────────────────────────────────────────────


def _load_handbook(site_id: str) -> tuple[dict | None, str | None]:
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
            if handbook:
                return handbook, fp.name
        except (json.JSONDecodeError, OSError):
            continue
    return None, None


def _call_deepseek(prompt: str, value_str: str, label: str) -> dict | None:
    if not DEEPSEEK_KEY:
        print(f"  [SKIP] {label}: No DEEPSEEK_API_KEY")
        return None
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url=DEEPSEEK_BASE)
    for attempt in range(1, 5):
        print(f"  Calling DeepSeek ({label})", end="")
        if attempt > 1:
            print(f" [attempt {attempt}/4]", end="")
        print("...")
        try:
            resp = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": value_str},
                ],
                max_tokens=8192, temperature=0.1,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else parts[-1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            data = json.loads(raw)
            return data
        except json.JSONDecodeError as e:
            print(f"  [ERR] {label}: JSON parse: {e}")
            if attempt < 4:
                time.sleep(3)
        except Exception as e:
            print(f"  [ERR] {label}: {e}")
            if attempt < 4:
                time.sleep(5)
    return None


def _cache_path(site_id: str, section: str) -> Path:
    return CACHE_DIR / site_id / f"{section}.json"


def _section_value(handbook: dict, section: str) -> str | None:
    value = handbook.get(section)
    if value is None:
        return None
    if isinstance(value, str) and len(value.strip()) < 100:
        return None
    if isinstance(value, (list, dict)) and len(json.dumps(value)) < 100:
        return None
    return value


def process_section(site_id: str, handbook: dict, section: str,
                    force: bool = False) -> bool:
    cache = _cache_path(site_id, section)
    if cache.exists() and not force:
        return True

    config = SECTION_CONFIGS.get(section)
    if not config:
        return False

    value = _section_value(handbook, section)
    if value is None:
        return False

    value_str = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    result = _call_deepseek(config["prompt"], value_str, f"{site_id}/{section}")
    if result is None:
        return False

    result["_section"] = section
    result["_site_id"] = site_id
    result["_model"] = DEEPSEEK_MODEL
    result["_original_chars"] = len(value_str)

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def process_all(force: bool = False, site_filter: str | None = None,
                section_filter: str | None = None) -> dict:
    if not INTERMEDIATE_DIR.is_dir():
        print(f"[ERROR] No intermediate data at {INTERMEDIATE_DIR}")
        return {"total": 0, "ok": 0, "skip": 0, "fail": 0}

    site_dirs = sorted([d for d in INTERMEDIATE_DIR.iterdir() if d.is_dir()],
                       key=lambda d: d.name.lower())

    if site_filter:
        site_dirs = [d for d in site_dirs if d.name == site_filter]

    sections_to_process = [section_filter] if section_filter else list(SECTION_CONFIGS)

    stats: dict[str, int] = {"total": 0, "ok": 0, "skip": 0, "fail": 0}

    for site_dir in site_dirs:
        site_id = site_dir.name
        handbook, source_file = _load_handbook(site_id)
        if not handbook:
            continue

        for section in sections_to_process:
            stats["total"] += 1
            label = f"{site_id}/{section}"
            try:
                if process_section(site_id, handbook, section, force=force):
                    stats["ok"] += 1
                else:
                    stats["fail"] += 1
            except Exception as e:
                print(f"  [ERR] {label}: {e}")
                stats["fail"] += 1
            time.sleep(0.8)

    print(f"\nDone. {stats['ok']} ok, {stats['fail']} fail, {stats['skip']} skip ({stats['total']} total)")
    return stats


if __name__ == "__main__":
    force = "--force" in sys.argv
    site_filter = None
    section_filter = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg.startswith("--site="):
            site_filter = arg.split("=", 1)[1]
        elif arg == "--site" and i + 1 < len(sys.argv) - 1:
            site_filter = sys.argv[i + 2]
        elif arg.startswith("--section="):
            section_filter = arg.split("=", 1)[1]
        elif arg == "--section" and i + 1 < len(sys.argv) - 1:
            section_filter = sys.argv[i + 2]

    process_all(force=force, site_filter=site_filter, section_filter=section_filter)

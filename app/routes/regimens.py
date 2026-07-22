import re
from flask import Blueprint, current_app, render_template
from app.data.loader import get_all_regimens, get_regimens_for_site, get_site, site_exists
from app.data.category_map import SYSTEMS

regimens_bp = Blueprint("regimens", __name__)


def _classify_intent(setting: str) -> str:
    s = setting.lower()
    if any(w in s for w in ["adjuvant", "postsurgical"]):
        return "Adjuvant"
    if any(w in s for w in ["preoperative", "neoadjuvant", "preop"]):
        return "Neoadjuvant"
    if any(w in s for w in ["first-line", "first line"]):
        return "First-line"
    if any(w in s for w in ["second", "third", "fourth"]):
        return "Second-line+"
    if "maintenance" in s:
        return "Maintenance"
    if "metastatic" in s:
        return "Metastatic"
    return "Other"


def _classify_line(setting: str) -> str:
    s = setting.lower()
    if any(w in s for w in ["adjuvant", "preoperative", "neoadjuvant", "preop", "postsurgical", "primary"]):
        return "Adjuvant/Neoadjuvant"
    if any(w in s for w in ["first-line", "first line"]):
        return "First-line"
    if any(w in s for w in ["second-line", "second line"]):
        return "Second-line"
    if any(w in s for w in ["third", "fourth"]):
        return "Third-line+"
    return "Any"


def _extract_subsite(site_val: str) -> str:
    if not site_val:
        return "Other"
    # Take the part before the first parenthesis
    m = re.match(r"^([^(]+)", site_val)
    if m:
        return m.group(1).strip()
    return site_val.strip()


def _safe_falsy(v):
    """Check truthiness safely for numpy arrays and other edge cases."""
    if v is None:
        return True
    if hasattr(v, '__len__'):
        try:
            return len(v) == 0
        except ValueError:
            return False
    try:
        return not v
    except ValueError:
        return False


def _process_regimen(r: dict) -> dict:
    setting = r.get("setting", "") or ""
    subsite = _extract_subsite(r.get("site", ""))
    intent = _classify_intent(setting)
    line = _classify_line(setting)
    modality = r.get("Modality", "") if not _safe_falsy(r.get("Modality")) else ""
    evidence = r.get("evidence_level", "") if not _safe_falsy(r.get("evidence_level")) else ""
    guideline = r.get("guideline_category", "") if not _safe_falsy(r.get("guideline_category")) else ""
    drugs_raw = r.get("drugs", [])
    if isinstance(drugs_raw, list):
        drug_names = [d.get("name", "") for d in drugs_raw if isinstance(d, dict)]
        drugs_short = " + ".join(drug_names)
    else:
        drugs_raw = drugs_raw.tolist() if hasattr(drugs_raw, 'tolist') else drugs_raw
        drugs_short = str(drugs_raw) if not _safe_falsy(drugs_raw) else ""
    raw_td = r.get("trial_data")
    if isinstance(raw_td, (list, tuple)):
        raw_td = raw_td[0] if raw_td else None
    if not isinstance(raw_td, dict):
        raw_td = {}
    trial_data = _trial_summary(raw_td)
    return {
        "regimen_name": r.get("regimen_name", ""),
        "setting": setting, "subsite": subsite, "intent": intent, "line": line,
        "modality": modality, "drugs_short": drugs_short,
        "evidence_level": evidence, "guideline_category": guideline,
        "has_trial": trial_data is not None,
        "drugs": r.get("drugs", []), "biomarkers": r.get("biomarkers", []),
        "trial_data": trial_data, "notes": r.get("notes", ""),
        "site_name": r.get("_site_display", r.get("_site_id", "")),
        "site_id": r.get("_site_id", ""),
    }


def _trial_summary(td) -> dict | None:
    if not td or not isinstance(td, dict):
        return None
    non_null = {}
    for k, v in td.items():
        if v is None:
            continue
        if hasattr(v, "__len__") and len(v) == 0:
            continue
        try:
            if isinstance(v, str) and v == "":
                continue
            if hasattr(v, "__iter__") and not isinstance(v, (str, dict)):
                non_null[k] = str(v)
            else:
                non_null[k] = v
        except (ValueError, TypeError):
            non_null[k] = str(v)
    if not non_null:
        return None
    return non_null


@regimens_bp.route("/regimens/<site_id>")
def regimens_page(site_id):
    if not site_exists(site_id):
        return render_template("base.html", content=f"<h2>Site not found</h2><p><a href='/'>Back to home</a></p>"), 404

    site = get_site(site_id)
    df = get_regimens_for_site(site_id)

    subsites_set = set()
    intents_set = set()
    lines_set = set()
    modalities_set = set()
    evidence_set = set()
    guideline_set = set()

    regimens = []
    for _, row in df.iterrows():
        r = row.to_dict()
        pr = _process_regimen(r)
        subsites_set.add(pr["subsite"])
        intents_set.add(pr["intent"])
        lines_set.add(pr["line"])
        if pr["modality"]: modalities_set.add(pr["modality"])
        if pr["evidence_level"]: evidence_set.add(pr["evidence_level"])
        if pr["guideline_category"]: guideline_set.add(pr["guideline_category"])
        regimens.append(pr)

    regimens_json = regimens  # Already list of dicts, json-safe

    filter_options = {
        "subsites": sorted(subsites_set),
        "intents": sorted(intents_set, key=lambda x: ["Adjuvant", "Neoadjuvant", "First-line", "Second-line+", "Metastatic", "Maintenance", "Other"].index(x) if x in ["Adjuvant", "Neoadjuvant", "First-line", "Second-line+", "Metastatic", "Maintenance", "Other"] else 99),
        "lines": sorted(lines_set, key=lambda x: ["Adjuvant/Neoadjuvant", "First-line", "Second-line", "Third-line+", "Any"].index(x) if x in ["Adjuvant/Neoadjuvant", "First-line", "Second-line", "Third-line+", "Any"] else 99),
        "modalities": sorted(modalities_set) if len(modalities_set) <= 20 else [],
        "evidence_levels": sorted(evidence_set),
        "guideline_categories": sorted(guideline_set),
    }

    site_info = {
        "display_name": site.get("display_name", site_id),
        "archetype": site.get("archetype", "?"),
        "description": site.get("description", ""),
        "regimen_count": len(regimens),
    }

    return render_template(
        "regimens.html",
        site=site_info,
        site_id=site_id,
        regimens_json=regimens_json,
        filter_options=filter_options,
    )


@regimens_bp.route("/regimens")
def regimens_all():
    from app.data.loader import get_all_regimens
    all_data = get_all_regimens()
    if not all_data:
        return render_template("base.html", content="<h2>No regimen data available</h2><p><a href='/'>Back to home</a></p>")

    subsites_set = set()
    intents_set = set()
    lines_set = set()
    sites_set = set()

    regimens = []
    for r in all_data:
        pr = _process_regimen(r)
        subsites_set.add(pr["subsite"])
        intents_set.add(pr["intent"])
        lines_set.add(pr["line"])
        sites_set.add(pr["site_name"])
        regimens.append(pr)

    _intent_order = ["Adjuvant", "Neoadjuvant", "First-line", "Second-line+", "Metastatic", "Maintenance", "Other"]
    _line_order = ["Adjuvant/Neoadjuvant", "First-line", "Second-line", "Third-line+", "Any"]

    filter_options = {
        "subsites": sorted(subsites_set),
        "intents": sorted(intents_set, key=lambda x: _intent_order.index(x) if x in _intent_order else 99),
        "lines": sorted(lines_set, key=lambda x: _line_order.index(x) if x in _line_order else 99),
        "sites": sorted(sites_set),
    }

    return render_template(
        "regimens.html",
        site=None,
        site_id=None,
        regimens_json=regimens,
        filter_options=filter_options,
    )

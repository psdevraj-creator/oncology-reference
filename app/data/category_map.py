SYSTEMS = {
    "breast":    {"name": "Breast",           "icon": "bi-gender-female",    "color": "#db2777", "order": 0},
    "thoracic":  {"name": "Thoracic",         "icon": "bi-lungs-fill",      "color": "#2563eb", "order": 1},
    "gi_upper":  {"name": "GI \u2014 Upper",  "icon": "bi-cup-straw",       "color": "#d97706", "order": 2},
    "gi_lower":  {"name": "GI \u2014 Lower",  "icon": "bi-arrow-down-circle", "color": "#059669", "order": 3},
    "gu":        {"name": "Genitourinary",    "icon": "bi-droplet",         "color": "#4f46e5", "order": 4},
    "gyn":       {"name": "Gynaecologic",     "icon": "bi-flower1",         "color": "#c026d3", "order": 5},
    "head_neck": {"name": "Head & Neck",      "icon": "bi-ear-fill",        "color": "#dc2626", "order": 6},
    "net":       {"name": "Neuroendocrine",   "icon": "bi-lightning-charge","color": "#7c3aed", "order": 7},
    "skin":      {"name": "Skin",             "icon": "bi-brightness-high", "color": "#ea580c", "order": 8},
    "sarcoma":   {"name": "Sarcoma & Bone",   "icon": "bi-screwdriver",     "color": "#475569", "order": 9},
    "cns":       {"name": "CNS",              "icon": "bi-cpu",             "color": "#0d9488", "order": 10},
    "heme":      {"name": "Hematologic",      "icon": "bi-eyedropper",      "color": "#b91c1c", "order": 11},
}

SITE_SYSTEM = {
    "breast": "breast",
    "lung": "thoracic",
    "mesothelioma_pleural": "thoracic",
    "thymic": "thoracic",
    "oesophageal": "gi_upper",
    "gastric": "gi_upper",
    "pancreatic": "gi_upper",
    "ampullary": "gi_upper",
    "biliary": "gi_upper",
    "hcc": "gi_upper",
    "hepatobiliary": "gi_upper",
    "lower_gi": "gi_lower",
    "anal": "gi_lower",
    "small_bowel": "gi_lower",
    "mesothelioma_peritoneal": "gi_lower",
    "kidney": "gu",
    "bladder": "gu",
    "prostate": "gu",
    "penile": "gu",
    "testicular": "gu",
    "cervical": "gyn",
    "ovarian": "gyn",
    "uterine": "gyn",
    "vaginal": "gyn",
    "vulvar": "gyn",
    "head_and_neck": "head_neck",
    "thyroid": "head_neck",
    "occult_primary": "head_neck",
    "Neuroendocrine": "net",
    "melanoma": "skin",
    "Skin_cancer": "skin",
    "merkel": "skin",
    "kaposi": "skin",
    "cutaneous_lymphoma": "skin",
    "bone": "sarcoma",
    "sarcoma": "sarcoma",
    "GIST": "sarcoma",
    "cns": "cns",
    "neuroblastoma": "cns",
    "hodgkin_lymphoma": "heme",
    "myeloma": "heme",
}


def get_system_for_site(site_id: str) -> dict | None:
    key = SITE_SYSTEM.get(site_id)
    if key:
        return SYSTEMS[key]
    return None


def group_sites_by_system(sites: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for site in sites:
        key = SITE_SYSTEM.get(site["id"])
        if key:
            grouped.setdefault(key, []).append(site)
    return dict(sorted(grouped.items(), key=lambda x: SYSTEMS[x[0]]["order"]))

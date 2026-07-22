import json
import logging
from pathlib import Path
from typing import Any
from markupsafe import Markup

import markdown as md_lib

logger = logging.getLogger(__name__)

REWRITTEN_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "rewritten"

_SECTION_ICONS = {
    "definition": "bookmark-check",
    "epidemiology": "graph-up",
    "subtypes": "clipboard2-pulse",
    "molecular_pathogenesis": "dna",
    "risk_factors": "shield-exclamation",
    "protective_factors": "shield-check",
    "clinical_features": "heart-pulse",
    "red_flags": "exclamation-triangle",
    "investigations": "search",
    "staging": "diagram-3",
    "management_principles": "bullseye",
    "management_pathways": "signpost-2",
    "pretreatment_evaluation": "clipboard-check",
    "surgery": "scissors",
    "radiation_therapy": "radioactive",
    "systemic_therapy": "capsule",
    "treatment_response_assessment": "graph-up-arrow",
    "surveillance": "binoculars",
    "complications": "exclamation-circle",
    "supportive_care": "heart",
    "prognosis": "clock-history",
    "follow_up": "calendar-check",
    "key_trials": "journal-richtext",
    "clinical_pearls": "lightbulb",
    "special_situations": "exclamation-diamond",
    "guidelines_resources": "journal-check",
    "drug_information": "info-circle",
}

import re as _re


def _md(text: str) -> str:
    """Render markdown, stripping embedded headings (section_html.py provides its own)."""
    if not text:
        return ""
    cleaned = _re.sub(r'^#{1,4}\s+', '', text, flags=_re.MULTILINE)
    return md_lib.markdown(cleaned, extensions=["extra", "sane_lists"])


def _icon(icon_name: str) -> str:
    return f'<i class="bi bi-{icon_name} me-2"></i>'


def _section_id(key: str) -> str:
    return key


def _label(key: str) -> str:
    return key.replace("_", " ").title()


def _heading(key: str, tag: str = "h3") -> str:
    icon = _SECTION_ICONS.get(key, "file-medical")
    label = _label(key)
    return f'<{tag} class="section-heading" id="{_section_id(key)}"><i class="bi bi-chevron-down collapse-icon"></i>{_icon(icon)}{label}<span class="collapse-label">Click to collapse</span></{tag}>'


def _subheading(label: str) -> str:
    return f'<h4 class="subsection-heading">{label}</h4>'


def _card(title: str, body: str, icon: str = "file-medical", color: str = "#6366f1", badge: str = "") -> str:
    badge_html = f'<span class="badge rounded-pill" style="background:{color}">{badge}</span>' if badge else ""
    title_html = f'<h6 class="card-subtitle mb-2">{title}</h6>' if title else ""
    return f'''<div class="col-12 col-sm-6 mb-3">
  <div class="clinical-card h-100" style="border-left: 3px solid {color};">
    <div class="card-body">
      {badge_html}
      {_icon(icon)}
      {title_html}
      <div class="card-text">{body}</div>
    </div>
  </div>
</div>'''


def _stat_card(label: str, value: str, icon: str = "graph-up", color: str = "#6366f1") -> str:
    return f'''<div class="col-12 col-sm-6 col-md-3 mb-3">
  <div class="card stat-card h-100 text-center border-0 shadow-sm" style="background: linear-gradient(135deg, {color}15, {color}08);">
    <div class="card-body">
      <div class="stat-icon mb-1" style="color:{color};font-size:1.5rem;">{_icon(icon)}</div>
      <div class="stat-value h4 mb-0" style="color:{color};">{value}</div>
      <div class="stat-label small text-muted">{label}</div>
    </div>
  </div>
</div>'''


def _alert_card(title: str, body: str, severity: str = "danger", icon: str = "exclamation-triangle-fill") -> str:
    return f'''<div class="alert-card d-flex align-items-start mb-3" role="alert">
  <div class="me-3 fs-4" style="color: var(--clinical-danger);">{_icon(icon)}</div>
  <div>
    <strong>{title}</strong><br>{body}
  </div>
</div>'''


def _table(rows: list[dict], cols: list[str] | None = None) -> str:
    if not rows:
        return ""
    if cols is None:
        cols = list(rows[0].keys())
    header = "".join(f"<th>{_label(c)}</th>" for c in cols)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{str(row.get(c, ''))}</td>" for c in cols) + "</tr>"
    return f'''<div class="table-responsive">
  <table class="table section-table">
    <thead><tr>{header}</tr></thead>
    <tbody>{body}</tbody>
  </table>
</div>'''


def _kv_list(items: list[tuple[str, str]]) -> str:
    return "<dl class='row'>" + "".join(
        f"<dt class='col-sm-4'>{k}</dt><dd class='col-sm-8'>{v}</dd>" for k, v in items
    ) + "</dl>"


def _card_grid(items: list[str]) -> str:
    return f'<div class="row g-3 card-grid">{"".join(items)}</div>'


def _definition_section(value: Any) -> str:
    parts = [_heading("definition", "h3")]
    if isinstance(value, dict) and value.get("sections"):
        for sec in value["sections"]:
            heading = sec.get("heading", "")
            content = _md(sec.get("content", ""))
            cite = f'<figcaption class="blockquote-footer mt-1">{heading}</figcaption>' if heading else ""
            parts.append(
                f'<div class="definition-callout">'
                f'{content}{cite}'
                f"</div>"
            )
    elif isinstance(value, str) and value.strip():
        parts.append(
            f'<div class="definition-callout">{_md(value)}</div>'
        )
    return "\n".join(parts)


def _epidemiology_section(value: Any) -> str:
    parts = [_heading("epidemiology", "h3")]
    if not isinstance(value, dict):
        if isinstance(value, str) and value.strip():
            parts.append(f'<div class="clinical-card">{_md(value)}</div>')
        return "\n".join(parts)
    stats = []
    for key, label, icon, color in [
        ("incidence", "Annual Incidence", "people-fill", "#6366f1"),
        ("mortality", "Annual Mortality", "graph-down-arrow", "#ef4444"),
        ("trends", "Trend & Projections", "graph-up", "#f59e0b"),
        ("demographics", "Demographics", "globe2", "#3b82f6"),
    ]:
        val = value.get(key, "")
        if isinstance(val, str) and val.strip():
            stats.append(_stat_card(label, val, icon, color))
    if stats:
        parts.append(_card_grid(stats))
    return "\n".join(parts)


def _subtypes_section(value: Any) -> str:
    parts = [_heading("subtypes", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)
    cards = []
    colors = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6"]
    for i, s in enumerate(value):
        if isinstance(s, dict):
            cards.append(_card(
                title=s.get("name", f"Subtype {i+1}"),
                body=_md(s.get("description", "")),
                icon="clipboard2-pulse",
                color=colors[i % len(colors)],
                badge=s.get("frequency", ""),
            ))
    if cards:
        parts.append(_card_grid(cards))
    return "\n".join(parts)


def _risk_factors_section(value: Any) -> str:
    parts = [_heading("risk_factors", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)
    type_colors = {"Genetic": "#ef4444", "Lifestyle": "#f59e0b", "Environmental": "#3b82f6",
                   "Demographic": "#6366f1", "Medical": "#ec4899", "Hormonal": "#8b5cf6"}
    cards = []
    for rf in value:
        if isinstance(rf, dict):
            color = type_colors.get(rf.get("type", ""), "#64748b")
            badges = []
            if rf.get("strength"):
                badges.append(f'<span class="badge bg-primary me-1">{rf["strength"]}</span>')
            if rf.get("type"):
                badges.append(f'<span class="badge bg-light text-dark me-1">{rf["type"]}</span>')
            cards.append(_card(
                title=rf.get("factor", ""),
                body=_md(rf.get("detail", "")),
                icon="shield-exclamation", color=color,
            ))
    if cards:
        parts.append(_card_grid(cards))
    return "\n".join(parts)


def _clinical_features_section(value: Any) -> str:
    parts = [_heading("clinical_features", "h3")]
    if not value:
        return "\n".join(parts)
    if isinstance(value, dict):
        for sub_key, sub_val in value.items():
            label = _label(sub_key)
            if isinstance(sub_val, list):
                cards = []
                for item in sub_val:
                    if isinstance(item, dict):
                        alarm = item.get("alarm", False)
                        color = "#ef4444" if alarm else "#f59e0b"
                        icon = "exclamation-diamond-fill" if alarm else "clipboard-pulse"
                        cards.append(_card(
                            title=item.get("name", ""),
                            body=_md(item.get("detail", "")),
                            icon=icon, color=color,
                            badge=item.get("frequency", ""),
                        ))
                if cards:
                    parts.append(_subheading(label))
                    parts.append(_card_grid(cards))
            elif isinstance(sub_val, str) and sub_val.strip():
                parts.append(_subheading(label))
                parts.append(f'<div class="clinical-card">{_md(sub_val)}</div>')
    elif isinstance(value, str) and value.strip():
        parts.append(f'<div class="clinical-card">{_md(value)}</div>')
    elif isinstance(value, list):
        cards = []
        for item in value:
            if isinstance(item, dict):
                cards.append(_card(
                    title=item.get("name", ""),
                    body=_md(item.get("detail", "")),
                    icon="clipboard-pulse", color="#f59e0b",
                ))
        if cards:
            parts.append(_card_grid(cards))
    return "\n".join(parts)


def _red_flags_section(value: Any) -> str:
    parts = [_heading("red_flags", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)
    for rf in value:
        text = rf if isinstance(rf, str) else rf.get("detail", str(rf))
        title = "Red Flag" if isinstance(rf, str) else rf.get("name", "Red Flag")
        parts.append(_alert_card(title, _md(text), "danger", "exclamation-triangle-fill"))
    return "\n".join(parts)


def _investigations_section(value: Any) -> str:
    parts = [_heading("investigations", "h3")]
    if not value:
        return "\n".join(parts)
    if isinstance(value, dict):
        for key, sub_val in value.items():
            label = _label(key)
            if isinstance(sub_val, list):
                cards = []
                for item in sub_val:
                    if isinstance(item, dict):
                        text = item.get("rationale", "") or item.get("text", "")
                        cards.append(_card(
                            title=item.get("test", item.get("name", key)),
                            body=_md(text),
                            icon="search", color="#7c3aed",
                        ))
                if cards:
                    parts.append(_subheading(label))
                    parts.append(_card_grid(cards))
            elif isinstance(sub_val, str) and sub_val.strip():
                parts.append(_subheading(label))
                parts.append(f'<div class="clinical-card"><div class="card-body">{_md(sub_val)}</div></div>')
    elif isinstance(value, list):
        cards = []
        for item in value:
            if isinstance(item, dict):
                cards.append(_card(
                    title=item.get("test", item.get("name", "")),
                    body=_md(item.get("rationale", "")),
                    icon="search", color="#7c3aed",
                ))
        if cards:
            parts.append(_card_grid(cards))
    elif isinstance(value, str) and value.strip():
        parts.append(f'<div class="clinical-card">{_md(value)}</div>')
    return "\n".join(parts)


def _staging_section(value: dict) -> str:
    if not value:
        return ""
    parts = [_heading("staging", "h3")]
    if value.get("system"):
        parts.append(f'<p class="text-muted">{value["system"]}</p>')
    t = value.get("t_stages") or value.get("t_categories", [])
    n = value.get("n_stages") or value.get("n_categories", [])
    m = value.get("m_stages") or value.get("m_categories", [])
    sg = value.get("stage_groups") or value.get("stage_groupings", [])
    if t:
        parts.append(_subheading("T Categories"))
        parts.append(_table(t))
    if n:
        parts.append(_subheading("N Categories"))
        parts.append(_table(n))
    if m:
        parts.append(_subheading("M Categories"))
        parts.append(_table(m))
    if sg:
        parts.append(_subheading("Stage Groupings"))
        parts.append(_table(sg))
    pearls = value.get("staging_pearls", [])
    if pearls:
        parts.append(_subheading("Staging Pearls"))
        parts.append("<ul>" + "".join(f"<li>{p}</li>" for p in pearls) + "</ul>")
    return "\n".join(parts)


def _management_principles_section(value: Any) -> str:
    parts = [_heading("management_principles", "h3")]
    if not isinstance(value, dict):
        if isinstance(value, str) and value.strip():
            parts.append(f'<div class="clinical-card">{_md(value)}</div>')
        return "\n".join(parts)
    if isinstance(value.get("overview"), str) and value["overview"].strip():
        parts.append(f'<div class="clinical-card">{_md(value["overview"])}</div>')
    if isinstance(value.get("by_intent"), list):
        cards = []
        for item in value["by_intent"]:
            if isinstance(item, str):
                text = item
                intent = "Management"
            else:
                approach = item.get("approach", "")
                patient_group = item.get("patient_group", "")
                text = approach
                if patient_group:
                    text = f"{patient_group}<br><br>{approach}" if approach else patient_group
                intent = item.get("intent", "Management")
            color = "#10b981" if "curative" in intent.lower() else "#f59e0b" if "palliative" in intent.lower() else "#6366f1"
            cards.append(_card(title=intent, body=_md(text), icon="bullseye", color=color))
        if cards:
            parts.append(_card_grid(cards))
    for key in value:
        if key in ("overview", "by_intent"):
            continue
        sub = value[key]
        if isinstance(sub, str) and sub.strip():
            parts.append(f'<figure class="mb-3"><blockquote class="blockquote">{_md(sub)}</blockquote><figcaption class="blockquote-footer">{_label(key)}</figcaption></figure>')
    return "\n".join(parts)


def _management_pathways_section(value: Any) -> str:
    if not value:
        return ""
    parts = [_heading("management_pathways", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)
    for pw in value:
        if not isinstance(pw, dict):
            continue
        title = pw.get("title", pw.get("pathway_id", "Pathway"))
        branching = pw.get("branching_basis", [])
        nodes = pw.get("nodes", [])
        pw_html = f'<div class="card pathway-card mb-3"><div class="card-header"><strong>{title}</strong></div><div class="card-body">'
        if branching:
            pw_html += f'<p class="small text-muted">Branching: {", ".join(branching)}</p>'
        for node in nodes:
            criteria = node.get("criteria", "")
            options = node.get("options", [])
            opt_text = "; ".join(
                f"{o.get('label', o.get('type', ''))} ({o.get('preference', o.get('recommendation', ''))})"
                for o in options if isinstance(o, dict)
            )
            adj = node.get("adjuvant_logic", {})
            adj_text = ""
            if isinstance(adj, dict):
                adj_text = adj.get("summary", "") if adj.get("applies") is not False else ""
            pw_html += '<div class="card pathway-node-card mb-2">'
            pw_html += '<div class="card-body py-2">'
            if criteria:
                pw_html += f"<strong>{criteria}</strong><br>"
            if opt_text:
                pw_html += f'<div class="small text-muted">{opt_text}</div>'
            if adj_text:
                pw_html += f'<div class="small text-info">{adj_text}</div>'
            pw_html += "</div></div>"
        pw_html += "</div></div>"
        parts.append(pw_html)
    return "\n".join(parts)


def _surgery_section(value: Any) -> str:
    parts = [_heading("surgery", "h3")]
    if not isinstance(value, dict):
        return "\n".join(parts)
    if isinstance(value.get("role"), str) and value["role"].strip():
        parts.append(f'<figure class="mb-3"><blockquote class="blockquote">{_md(value["role"])}</blockquote><figcaption class="blockquote-footer">Surgical Role</figcaption></figure>')
    principles = value.get("principles", [])
    if isinstance(principles, str):
        principles = [principles]
    for p in principles:
        if isinstance(p, str) and p.strip():
            parts.append(_card(title="", body=_md(p), icon="check-circle", color="#6366f1"))
    if isinstance(value.get("procedures"), list):
        cards = []
        for proc in value["procedures"]:
            if isinstance(proc, dict):
                cards.append(_card(
                    title=proc.get("name", proc.get("procedure", "")),
                    body=_md(proc.get("description", proc.get("detail", proc.get("indications", "")))),
                    icon="scissors", color="#ec4899",
                ))
        if cards:
            parts.append(_subheading("Procedures"))
            parts.append(_card_grid(cards))
    return "\n".join(parts)


def _radiation_therapy_section(value: Any) -> str:
    if not value:
        return ""
    parts = [_heading("radiation_therapy", "h3")]
    if isinstance(value, dict):
        if value.get("role"):
            parts.append(f'<p class="text-muted">{value["role"]}</p>')
        principles = value.get("principles", [])
        if principles:
            parts.append(_subheading("Principles"))
            parts.append("<ul>" + "".join(f"<li>{p}</li>" for p in principles) + "</ul>")
        dose_fw = value.get("dose_frameworks", [])
        if dose_fw:
            parts.append(_subheading("Dose Frameworks"))
            parts.append(_table(dose_fw))
        approaches = value.get("approaches", [])
        if approaches:
            parts.append(_subheading("Approaches"))
            parts.append(_table(approaches))
    elif isinstance(value, str) and value.strip():
        parts.append(f'<div class="clinical-card">{_md(value)}</div>')
    return "\n".join(parts)


def _systemic_therapy_section(value: Any) -> str:
    if not value:
        return ""
    parts = [_heading("systemic_therapy", "h3")]
    if not isinstance(value, dict):
        if isinstance(value, str) and value.strip():
            parts.append(f'<div class="clinical-card">{_md(value)}</div>')
        return "\n".join(parts)
    overview = value.get("overview", "")
    if overview:
        parts.append(f'<div class="clinical-card">{_md(overview)}</div>')
    by_stage = value.get("by_stage_and_setting", [])
    if isinstance(by_stage, list):
        cards = []
        for item in by_stage:
            if isinstance(item, dict):
                extra = ""
                if item.get("rationale"):
                    extra += f'<div class="small text-muted">{item["rationale"]}</div>'
                if item.get("preferred_regimen"):
                    extra += f'<div class="small">Preferred: {item["preferred_regimen"]}</div>'
                cards.append(f'<div class="col-12 mb-3"><div class="card systemic-card shadow-sm"><div class="card-body"><strong>{item.get("setting", "")}</strong>{extra}</div></div></div>')
        if cards:
            parts.append(f'<div class="row">{"".join(cards)}</div>')
    key_regimens = value.get("key_regimens", [])
    if isinstance(key_regimens, list) and key_regimens:
        parts.append(_subheading("Key Regimens"))
        for kr in key_regimens:
            if isinstance(kr, dict):
                drugs = kr.get("drugs", [])
                drug_strs = []
                for d in (drugs if isinstance(drugs, list) else []):
                    if isinstance(d, dict):
                        day_or_schedule = d.get("day") or d.get("schedule", "")
                        drug_strs.append(f"{d.get('name', '')} {d.get('dose', '')} {d.get('route', '')} {day_or_schedule}".strip())
                parts.append(f'<div class="card systemic-card mb-2"><div class="card-body"><strong>{kr.get("name", kr.get("setting", ""))}</strong><div class="small text-muted">{" + ".join(drug_strs)}</div></div></div>')
    return "\n".join(parts)


def _complications_section(value: Any) -> str:
    parts = [_heading("complications", "h3")]
    if not isinstance(value, dict):
        return "\n".join(parts)
    for key, label in [("disease_related", "Disease-Related"), ("treatment_related", "Treatment-Related")]:
        items = value.get(key, [])
        if isinstance(items, list) and items:
            rows = []
            for item in items:
                if isinstance(item, dict):
                    rows.append({
                        "Complication": item.get("complication", item.get("name", "")),
                        "Management": item.get("management", item.get("detail", "")),
                    })
                elif isinstance(item, str):
                    rows.append({"Complication": label, "Management": item})
            if rows:
                parts.append(_subheading(label))
                parts.append(_table(rows))
    return "\n".join(parts)


def _supportive_care_section(value: Any) -> str:
    parts = [_heading("supportive_care", "h3")]
    if not isinstance(value, dict):
        return "\n".join(parts)
    for key, sub_val in value.items():
        label = _label(key)
        if key == "overview" and isinstance(sub_val, str) and sub_val.strip():
            parts.append(f'<div class="clinical-card">{_md(sub_val)}</div>')
        elif isinstance(sub_val, (str, dict)):
            body = ""
            if isinstance(sub_val, str) and sub_val.strip():
                body = _md(sub_val)
            elif isinstance(sub_val, dict):
                items = []
                for sk, sv in sub_val.items():
                    if isinstance(sv, str) and sv.strip():
                        items.append(f"**{_label(sk)}**: {sv}")
                body = _md("\n\n".join(items)) if items else ""
            if body:
                parts.append(f'<div class="card mb-2"><div class="card-header"><strong>{label}</strong></div><div class="card-body">{body}</div></div>')
    return "\n".join(parts)


def _surveillance_section(value: Any) -> str:
    parts = [_heading("surveillance", "h3")]
    if not isinstance(value, dict):
        return "\n".join(parts)
    for key, sub_val in value.items():
        label = _label(key)
        if not sub_val:
            continue
        parts.append(_subheading(label))
        if isinstance(sub_val, list):
            if all(isinstance(v, dict) for v in sub_val):
                parts.append(_table(sub_val))
            else:
                items = [v for v in sub_val if isinstance(v, str)]
                if items:
                    parts.append("<ul>" + "".join(f"<li>{v}</li>" for v in items) + "</ul>")
        elif isinstance(sub_val, str) and sub_val.strip():
            parts.append(f"<p>{sub_val}</p>")
    return "\n".join(parts)


def _prognosis_section(value: Any) -> str:
    parts = [_heading("prognosis", "h3")]
    if not isinstance(value, dict):
        return "\n".join(parts)
    if isinstance(value.get("overall"), str) and value["overall"].strip():
        parts.append(f'<figure class="mb-3"><blockquote class="blockquote">{_md(value["overall"])}</blockquote><figcaption class="blockquote-footer">Overall Prognosis</figcaption></figure>')
    by_stage = value.get("by_stage", [])
    if by_stage:
        parts.append(_subheading("By Stage"))
        parts.append(_table(by_stage))
    factors = value.get("prognostic_factors", [])
    if factors:
        parts.append(_subheading("Prognostic Factors"))
        parts.append("<ul>" + "".join(f"<li>{f}</li>" if isinstance(f, str) else f"<li>{f.get('factor', '')}: {f.get('detail', f)}</li>" for f in factors) + "</ul>")
    return "\n".join(parts)


def _follow_up_section(value: Any) -> str:
    parts = [_heading("follow_up", "h3")]
    if not isinstance(value, dict):
        return "\n".join(parts)
    for key, sub_val in value.items():
        label = _label(key)
        if not sub_val:
            continue
        parts.append(_subheading(label))
        if isinstance(sub_val, list):
            if all(isinstance(v, dict) for v in sub_val):
                parts.append(_table(sub_val))
            else:
                items = [v for v in sub_val if isinstance(v, str)]
                if items:
                    parts.append("<ul>" + "".join(f"<li>{v}</li>" for v in items) + "</ul>")
        elif isinstance(sub_val, str) and sub_val.strip():
            parts.append(f"<p>{sub_val}</p>")
    return "\n".join(parts)


def _key_trials_section(value: Any) -> str:
    if not value:
        return ""
    parts = [_heading("key_trials", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)

    _SKIP_KEYS = {"_site_id", "_site_display", "_archetype"}

    # Collect all keys across all trials
    all_keys = []
    seen_keys = set()
    for t in value:
        if isinstance(t, dict):
            for k in t:
                if k not in seen_keys and k not in _SKIP_KEYS:
                    seen_keys.add(k)
                    all_keys.append(k)

    # Order: clinical columns first, then remaining
    priority = ["acronym", "trial_name", "full_name", "phase", "year", "n",
                 "intervention", "comparator", "population", "primary_endpoint",
                 "key_result", "secondary_outcomes", "practice_change", "journal"]
    ordered = [c for c in priority if c in all_keys] + [c for c in all_keys if c not in priority]

    rows = []
    for t in value:
        if not isinstance(t, dict):
            continue
        row = {}
        for c in ordered:
            val = t.get(c, "")
            if isinstance(val, (int, float)):
                row[c] = str(val)
            else:
                row[c] = val
        rows.append(row)

    if rows:
        parts.append(f'<div class="table-responsive">{_table(rows, ordered)}</div>')
    return "\n".join(parts)


def _clinical_pearls_section(value: Any) -> str:
    parts = [_heading("clinical_pearls", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)
    items = []
    for i, pearl in enumerate(value):
        text = pearl if isinstance(pearl, str) else pearl.get("text", str(pearl))
        items.append(f"<li><strong>Pearl {i+1}:</strong> {text}</li>")
    if items:
        parts.append("<ul>" + "\n".join(items) + "</ul>")
    return "\n".join(parts)


def _special_situations_section(value: Any) -> str:
    parts = [_heading("special_situations", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)
    cards = []
    for item in value:
        if isinstance(item, dict):
            cards.append(_card(
                title=item.get("name", item.get("situation", "")),
                body=_md(item.get("detail", item.get("description", ""))),
                icon="exclamation-diamond", color="#ec4899",
                badge=item.get("type", ""),
            ))
        elif isinstance(item, str):
            cards.append(_card(title="", body=item, icon="exclamation-diamond", color="#ec4899"))
    if cards:
        parts.append(_card_grid(cards))
    return "\n".join(parts)


def _guidelines_resources_section(value: Any) -> str:
    parts = [_heading("guidelines_resources", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)
    cards = []
    for item in value:
        if isinstance(item, dict):
            org = item.get("organisation", item.get("org", ""))
            badge = org or ""
            cards.append(_card(
                title=item.get("name", item.get("title", "")),
                body=_md(item.get("detail", item.get("description", ""))),
                icon="journal-check", color="#6366f1",
                badge=badge,
            ))
    if cards:
        parts.append(_card_grid(cards))
    return "\n".join(parts)


def _treatment_response_section(value: Any) -> str:
    parts = [_heading("treatment_response_assessment", "h3")]
    if not isinstance(value, dict):
        return "\n".join(parts)
    for key, sub_val in value.items():
        label = _label(key)
        if isinstance(sub_val, str) and sub_val.strip():
            parts.append(f'<div class="card shadow-sm mb-3"><div class="card-body"><h6 class="fw-semibold text-primary mb-2">{label}</h6>{_md(sub_val)}</div></div>')
        elif isinstance(sub_val, list):
            text = "\n\n".join(f"- {item}" for item in sub_val if isinstance(item, str))
            if text:
                parts.append(f'<div class="card shadow-sm mb-3"><div class="card-body"><h6 class="fw-semibold text-primary mb-2">{label}</h6>{_md(text)}</div></div>')
    return "\n".join(parts)


def _molecular_pathogenesis_section(value: Any) -> str:
    parts = [_heading("molecular_pathogenesis", "h3")]
    if not isinstance(value, str) or not value.strip():
        return "\n".join(parts)
    rendered = _md(value)
    paragraphs = rendered.count("<p>")
    if paragraphs <= 2 and len(value) < 200:
        parts.append(f'<div class="definition-callout"><p class="text-muted mb-0">{value}</p></div>')
    else:
        parts.append(f'<div class="definition-callout">{rendered}</div>')
    return "\n".join(parts)


def _pretreatment_evaluation_section(value: Any) -> str:
    if not value:
        return ""
    parts = [_heading("pretreatment_evaluation", "h3")]
    if not isinstance(value, list):
        return "\n".join(parts)
    for cat in value:
        if not isinstance(cat, dict):
            continue
        category = cat.get("category", "")
        items = cat.get("items", [])
        item_cards = []
        for it in items:
            if isinstance(it, dict):
                item_cards.append(
                    f'<div class="card pre-eval-card mb-2"><div class="card-body py-2">'
                    f'<strong>{it.get("text", "")}</strong>'
                    + (f'<div class="small text-muted">{it.get("recommendation", "")}</div>' if it.get("recommendation") else "")
                    + "</div></div>"
                )
        if item_cards:
            parts.append(f'<h6 class="pre-eval-category">{category}</h6>')
            parts.extend(item_cards)
    return "\n".join(parts)


def _fallback_section(key: str, value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str) and value.strip():
        return f'<div class="clinical-card"><div class="card-body">{_md(value)}</div></div>'
    if isinstance(value, (int, float)):
        return f'<div class="clinical-card"><div class="card-body">{value}</div></div>'
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, str):
                items.append(f"<li>{item}</li>")
            elif isinstance(item, dict):
                items.append("<li>" + json.dumps(item, ensure_ascii=False) + "</li>")
        if items:
            return f"<h4>{_label(key)}</h4><ul>{''.join(items)}</ul>"
    if isinstance(value, dict):
        sub = []
        for k, v in value.items():
            if isinstance(v, (str, int, float)) and v:
                sub.append(f"<p><strong>{_label(k)}:</strong> {v}</p>")
            elif isinstance(v, list) and v:
                li = "".join(f"<li>{i}</li>" for i in v if isinstance(i, str))
                if li:
                    sub.append(f"<h5>{_label(k)}</h5><ul>{li}</ul>")
        if sub:
            return f"<h4>{_label(key)}</h4>" + "".join(sub)
    return ""


_CUSTOM_RENDERERS = {
    "definition": _definition_section,
    "epidemiology": _epidemiology_section,
    "subtypes": _subtypes_section,
    "molecular_pathogenesis": _molecular_pathogenesis_section,
    "risk_factors": _risk_factors_section,
    "clinical_features": _clinical_features_section,
    "red_flags": _red_flags_section,
    "investigations": _investigations_section,
    "staging": _staging_section,
    "management_principles": _management_principles_section,
    "management_pathways": _management_pathways_section,
    "pretreatment_evaluation": _pretreatment_evaluation_section,
    "surgery": _surgery_section,
    "radiation_therapy": _radiation_therapy_section,
    "systemic_therapy": _systemic_therapy_section,
    "treatment_response_assessment": _treatment_response_section,
    "surveillance": _surveillance_section,
    "complications": _complications_section,
    "supportive_care": _supportive_care_section,
    "prognosis": _prognosis_section,
    "follow_up": _follow_up_section,
    "key_trials": _key_trials_section,
    "clinical_pearls": _clinical_pearls_section,
    "special_situations": _special_situations_section,
    "guidelines_resources": _guidelines_resources_section,
}

_SECTION_BLOCK_CLASSES = {
    "definition": "definition-block",
    "epidemiology": "epidemiology-block",
    "subtypes": "subtypes-block",
    "molecular_pathogenesis": "molecular-block",
    "risk_factors": "risk-block",
    "protective_factors": "risk-block",
    "clinical_features": "clinical-block",
    "red_flags": "red-flag-block",
    "investigations": "investigations-block",
    "staging": "staging-block",
    "management_principles": "management-block",
    "management_pathways": "pathway-block",
    "pretreatment_evaluation": "pretreatment-block",
    "surgery": "surgery-block",
    "radiation_therapy": "rt-block",
    "systemic_therapy": "systemic-block",
    "treatment_response_assessment": "response-block",
    "surveillance": "surveillance-block",
    "complications": "complications-block",
    "supportive_care": "supportive-block",
    "prognosis": "prognosis-block",
    "follow_up": "followup-block",
    "key_trials": "trials-block",
    "clinical_pearls": "pearl-block",
    "special_situations": "other-block",
    "guidelines_resources": "other-block",
    "drug_information": "other-block",
}


def _section_block_class(key: str) -> str:
    return _SECTION_BLOCK_CLASSES.get(key, "other-block")


def render_section(key: str, value: Any, handbook_key: str = "") -> str:
    parts = []
    section_key = handbook_key or key
    if not value:
        return ""

    renderer = _CUSTOM_RENDERERS.get(key)
    if renderer:
        try:
            html = renderer(value)
            if html:
                _block_cls = _section_block_class(key)
                parts.append(f'<div class="section-block {_block_cls}" id="{_section_id(key)}">{html}</div>')
            return "\n".join(parts)
        except Exception as e:
            logger.warning("Custom renderer failed for %s: %s", key, e)
            return _fallback_section(key, value)

    _block_cls = _section_block_class(key)
    if isinstance(value, str) and value.strip():
        parts.append(f'<div class="section-block {_block_cls}" id="{_section_id(key)}"><h3 class="section-heading"><i class="bi bi-chevron-down collapse-icon"></i>{_icon("file-medical")}{_label(key)}<span class="collapse-label">Click to collapse</span></h3><div class="clinical-card"><div class="card-body">{_md(value)}</div></div></div>')
    elif isinstance(value, list) and value:
        if all(isinstance(v, dict) for v in value):
            parts.append(f'<div class="section-block {_block_cls}" id="{_section_id(key)}"><h3 class="section-heading"><i class="bi bi-chevron-down collapse-icon"></i>{_icon("file-medical")}{_label(key)}<span class="collapse-label">Click to collapse</span></h3>' + _card_grid([_card(title=v.get("name", v.get("factor", f"Item {i}")), body=_md(str(v.get("detail", v.get("description", "")))), icon="file-medical", color="#6366f1") for i, v in enumerate(value)]) + '</div>')
        else:
            parts.append(f'<div class="section-block {_block_cls}" id="{_section_id(key)}"><h3 class="section-heading"><i class="bi bi-chevron-down collapse-icon"></i>{_icon("file-medical")}{_label(key)}<span class="collapse-label">Click to collapse</span></h3><ul>{"".join(f"<li>{v}</li>" for v in value if isinstance(v, str))}</ul></div>')
    elif isinstance(value, dict) and value:
        flat = all(isinstance(v, (str, int, float, bool)) for v in value.values())
        if flat:
            kv = [(f"<strong>{_label(k)}:</strong> {v}") for k, v in value.items() if v]
            parts.append(f'<div class="section-block {_block_cls}" id="{_section_id(key)}"><h3 class="section-heading"><i class="bi bi-chevron-down collapse-icon"></i>{_icon("file-medical")}{_label(key)}<span class="collapse-label">Click to collapse</span></h3><div class="clinical-card"><div class="card-body">{"<br>".join(kv)}</div></div></div>')
        else:
            sub = [_render_sub_section(k, v, 1) for k, v in value.items() if v]
            if sub:
                parts.append(f'<div class="section-block {_block_cls}" id="{_section_id(key)}"><h3 class="section-heading"><i class="bi bi-chevron-down collapse-icon"></i>{_icon("file-medical")}{_label(key)}<span class="collapse-label">Click to collapse</span></h3>{"".join(sub)}</div>')

    return "\n".join(parts)


def _render_sub_section(key: str, value: Any, depth: int = 1) -> str:
    tag = "h4" if depth == 1 else "h5"
    if isinstance(value, str) and value.strip():
        return f'<{tag}>{_label(key)}</{tag}><div class="clinical-card"><div class="card-body">{_md(value)}</div></div>'
    if isinstance(value, list) and value:
        if all(isinstance(v, dict) for v in value):
            return f'<{tag}>{_label(key)}</{tag}>' + _card_grid([
                _card(title=v.get("name", f"Item {i}"), body=_md(str(v.get("detail", v.get("description", "")))), icon="file-medical", color="#6366f1")
                for i, v in enumerate(value)
            ])
        li = "".join(f"<li>{v}</li>" for v in value if isinstance(v, str))
        if li:
            return f'<{tag}>{_label(key)}</{tag}><ul>{li}</ul>'
    return ""


_STANDARD_SECTIONS = {
    "definition", "epidemiology", "subtypes", "molecular_pathogenesis",
    "risk_factors", "protective_factors", "clinical_features", "red_flags",
    "investigations", "staging", "management_principles", "management_pathways",
    "pretreatment_evaluation", "surgery", "radiation_therapy",
    "systemic_therapy", "treatment_response_assessment", "surveillance",
    "complications", "supportive_care", "prognosis", "follow_up",
    "key_trials", "clinical_pearls", "special_situations",
    "guidelines_resources", "drug_information",
}


def _aggregate_subsite_keys(handbook: dict) -> dict:
    """Detect subsection keys (e.g. subtypes_mycosis_fungoides) and merge into parent sections."""
    result = dict(handbook)
    subsite_groups = {}

    for key in list(result.keys()):
        parts = key.split("_", 1)
        if len(parts) != 2:
            continue
        section, subsite = parts
        if section not in _STANDARD_SECTIONS:
            continue
        if not result[key]:
            continue
        subsite_groups.setdefault(section, []).append((subsite, result[key]))
        # Always remove the subsite key — we'll render the merged version
        del result[key]

    for section, items in subsite_groups.items():
        # Only create merged section if it doesn't already exist or is empty
        if result.get(section):
            continue

        values = [v for _, v in items]
        first = values[0] if values else None

        if isinstance(first, str):
            # Merge string sections as dict with sections array
            merged = {"sections": [{"heading": subsite.replace("_", " ").title(), "content": val} for subsite, val in items]}
            result[section] = merged
        elif isinstance(first, dict):
            merged = {}
            for subsite, val in items:
                merged[subsite.replace("_", " ").title()] = val
            result[section] = merged
        elif isinstance(first, list):
            merged = []
            for _, val in items:
                if isinstance(val, list):
                    merged.extend(val)
            result[section] = merged
        else:
            result[section] = first

    return result


def get_section_toc(handbook: dict) -> list[dict]:
    handbook = _aggregate_subsite_keys(handbook)
    priority_keys = [
        "definition", "epidemiology", "subtypes", "molecular_pathogenesis",
        "risk_factors", "clinical_features", "red_flags",
        "investigations", "staging",
        "management_principles", "management_pathways",
        "pretreatment_evaluation", "surgery", "radiation_therapy",
        "systemic_therapy", "treatment_response_assessment",
        "surveillance", "complications", "supportive_care",
        "prognosis", "follow_up", "key_trials", "clinical_pearls",
        "special_situations", "guidelines_resources",
    ]
    toc = []
    seen = set()
    for key in priority_keys:
        if key in handbook and handbook[key]:
            seen.add(key)
            toc.append({"id": key, "label": _label(key), "icon": _SECTION_ICONS.get(key, "file-medical")})
    for key in handbook:
        if key not in seen and handbook[key]:
            toc.append({"id": key, "label": _label(key), "icon": _SECTION_ICONS.get(key, "file-medical")})
    return toc


def render_handbook(handbook: dict, site_id: str = "") -> str:
    if not handbook:
        return '<p class="text-muted">No handbook data available for this site.</p>'

    handbook = _aggregate_subsite_keys(handbook)

    priority_keys = [
        "definition", "epidemiology", "subtypes", "molecular_pathogenesis",
        "risk_factors", "clinical_features", "red_flags",
        "investigations", "staging",
        "management_principles", "management_pathways",
        "pretreatment_evaluation", "surgery", "radiation_therapy",
        "systemic_therapy", "treatment_response_assessment",
        "surveillance", "complications", "supportive_care",
        "prognosis", "follow_up", "key_trials", "clinical_pearls",
        "special_situations", "guidelines_resources",
    ]

    all_parts = []
    seen = set()

    def render_key(key: str):
        if key in seen or key not in handbook:
            return ""
        seen.add(key)
        value = handbook[key]
        if not value:
            return ""
        return render_section(key, value)

    for key in priority_keys:
        html = render_key(key)
        if html:
            all_parts.append(html)

    for key in handbook:
        html = render_key(key)
        if html:
            all_parts.append(html)

    return "\n".join(all_parts)

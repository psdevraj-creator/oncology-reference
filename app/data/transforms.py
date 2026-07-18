from typing import Any

import pandas as pd


def regimen_drug_list(drugs: list[dict[str, Any]]) -> str:
    if not drugs:
        return ""
    return " + ".join(d.get("name", "?") for d in drugs if isinstance(d, dict))


def regimen_biomarker_list(biomarkers: list[dict[str, Any]]) -> str:
    if not biomarkers:
        return ""
    parts: list[str] = []
    for b in biomarkers:
        if not isinstance(b, dict):
            continue
        marker = b.get("marker", "")
        req = b.get("requirement", "")
        if req:
            parts.append(f"{marker}: {req}")
        else:
            parts.append(marker)
    return "; ".join(parts)


def flatten_regimens_for_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "drugs" in out.columns:
        out["Drugs"] = out["drugs"].apply(regimen_drug_list)
    if "biomarkers" in out.columns:
        out["Biomarkers"] = out["biomarkers"].apply(regimen_biomarker_list)
    if "treatment_modality" in out.columns:
        out["Modality"] = out["treatment_modality"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else ""
        )
    return out


def extract_trial_outcomes(trial_data: dict[str, Any] | None) -> dict[str, str]:
    if not trial_data or not isinstance(trial_data, dict):
        return {}
    outcomes: dict[str, str] = {}
    mapping = {
        "os_median_experimental": "OS Experimental",
        "os_median_control": "OS Control",
        "os_hr": "OS HR",
        "pfs_median_experimental": "PFS Experimental",
        "pfs_median_control": "PFS Control",
        "pfs_hr": "PFS HR",
        "dfs_median_experimental": "DFS Experimental",
        "dfs_median_control": "DFS Control",
        "dfs_hr": "DFS HR",
        "orr_experimental": "ORR Experimental",
        "orr_control": "ORR Control",
    }
    for key, label in mapping.items():
        val = trial_data.get(key)
        if val:
            outcomes[label] = str(val)
    if trial_data.get("os_ci"):
        outcomes["OS 95% CI"] = str(trial_data["os_ci"])
    if trial_data.get("pfs_ci"):
        outcomes["PFS 95% CI"] = str(trial_data["pfs_ci"])
    return outcomes

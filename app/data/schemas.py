from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Drug(BaseModel):
    name: str
    dose: Optional[str] = None
    route: Optional[str] = None
    schedule: Optional[str] = None


class Biomarker(BaseModel):
    marker: str
    requirement: Optional[str] = None
    mandatory: bool = False


class TrialData(BaseModel):
    trial_name: Optional[str] = None
    phase: Optional[str] = None
    n_patients: Optional[str] = None
    population: Optional[str] = None
    primary_endpoint: Optional[str] = None
    os_median_experimental: Optional[str] = None
    os_median_control: Optional[str] = None
    os_hr: Optional[str] = None
    os_ci: Optional[str] = None
    pfs_median_experimental: Optional[str] = None
    pfs_median_control: Optional[str] = None
    pfs_hr: Optional[str] = None
    pfs_ci: Optional[str] = None
    dfs_median_experimental: Optional[str] = None
    dfs_median_control: Optional[str] = None
    dfs_hr: Optional[str] = None
    orr_experimental: Optional[str] = None
    orr_control: Optional[str] = None
    key_subgroup: Optional[str] = None
    reference_numbers: list[str] = Field(default_factory=list)


class Regimen(BaseModel):
    regimen_name: str
    site: Optional[str] = None
    setting: Optional[str] = None
    treatment_modality: list[str] = Field(default_factory=list)
    drugs: list[Drug] = Field(default_factory=list)
    biomarkers: list[Biomarker] = Field(default_factory=list)
    cycle_length_days: Optional[str] = None
    evidence_level: Optional[str] = None
    guideline_category: Optional[str] = None
    trial_data: Optional[TrialData] = None
    notes: Optional[str] = None


class SiteEntry(BaseModel):
    id: str
    display_name: str
    description: str = ""
    color_accent: str = "#2563eb"
    emoji: str = ""
    regimen_count: int = 0
    last_processed: Optional[str] = None
    archetype: Optional[str] = None
    status: str = "active"

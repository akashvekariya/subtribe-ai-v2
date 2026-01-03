"""
Pydantic models for fact extraction tools.

These models define:
- Input from LLM extraction (RawDateInput, RawExperienceInput)
- Output after tool processing (EnrichedExperience, ExperienceSummary)
"""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ExperienceType(str, Enum):
    FULL_TIME = "full_time"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    CONTRACT = "contract"
    PART_TIME = "part_time"
    STARTUP_FOUNDER = "startup_founder"
    ACADEMIC_PROJECT = "academic_project"
    PERSONAL_PROJECT = "personal_project"


class DateAnomaly(str, Enum):
    INVERTED = "inverted"  # start_date > end_date
    FUTURE_START = "future_start"  # start_date is in the future
    FUTURE_END = "future_end"  # end_date is in the future (not ongoing)
    MISSING_START = "missing_start"  # no start date
    MISSING_BOTH = "missing_both"  # no dates at all
    DURATION_MISMATCH = "duration_mismatch"  # calculated != stated duration (>20%)


# ============================================================================
# INPUT MODELS - From LLM extraction
# ============================================================================


class RawDateInput(BaseModel):
    """Date as extracted by LLM - separate year and month."""

    year: int = Field(description="4-digit year")
    month: int = Field(ge=1, le=12, description="Month 1-12")
    is_estimated: bool = Field(
        default=False, description="True if month was estimated"
    )


class RawExperienceInput(BaseModel):
    """Experience entry as extracted by LLM - before tool processing."""

    company: str
    title: str
    location: Optional[str] = None
    experience_type: ExperienceType = ExperienceType.FULL_TIME

    start_date: Optional[RawDateInput] = Field(
        default=None, description="Start date. Null if not mentioned."
    )
    end_date: Optional[RawDateInput] = Field(
        default=None, description="End date. Null if ongoing OR not mentioned."
    )
    is_ongoing: bool = Field(
        default=False, description="True if explicitly ongoing (Present/Current)"
    )

    duration_stated: Optional[str] = Field(
        default=None, description="Duration as stated in resume, e.g., '2.5 years'"
    )

    key_contributions: list[str] = Field(default_factory=list)
    skills_demonstrated: list[str] = Field(default_factory=list)


# ============================================================================
# OUTPUT MODELS - After tool processing (enriched)
# ============================================================================


class EnrichedExperience(BaseModel):
    """Experience entry after tool processing - with calculated duration."""

    # Copied from input
    company: str
    title: str
    location: Optional[str] = None
    experience_type: ExperienceType

    # Parsed dates
    start_date: Optional[date] = Field(description="Parsed start date")
    end_date: Optional[date] = Field(
        description="Parsed end date. None if ongoing."
    )
    is_ongoing: bool

    # Calculated by tool
    duration_months: int = Field(description="Calculated duration in months")
    start_estimated: bool = Field(
        default=False, description="True if start month was estimated"
    )
    end_estimated: bool = Field(
        default=False, description="True if end month was estimated"
    )

    # Validation
    duration_stated: Optional[str] = None
    duration_stated_months: Optional[int] = Field(
        default=None, description="Parsed duration from stated text"
    )
    duration_divergence: Optional[float] = Field(
        default=None,
        description="Divergence between calculated and stated (e.g., 0.2 = 20%)",
    )
    anomaly: Optional[DateAnomaly] = None

    # Preserved from input
    key_contributions: list[str] = Field(default_factory=list)
    skills_demonstrated: list[str] = Field(default_factory=list)


class EmploymentGap(BaseModel):
    """Gap between two employment periods."""

    after_company: str
    before_company: str
    gap_start: date
    gap_end: date
    gap_months: int
    is_significant: bool = Field(description="True if gap > 6 months")


class ExperienceSummary(BaseModel):
    """
    Aggregated experience summary - final output of fact processing.
    This is passed to Phase 2 evaluation as ground truth.
    """

    # Totals
    total_months: int = Field(description="Total experience (overlap-adjusted)")
    total_years: float = Field(description="Total in years for display")

    # By type
    full_time_months: int = 0
    internship_months: int = 0
    freelance_months: int = 0
    contract_months: int = 0
    part_time_months: int = 0
    startup_months: int = 0
    project_months: int = 0

    # Overlap handling
    has_overlaps: bool = False
    overlap_months: int = 0

    # Gap detection
    gaps: list[EmploymentGap] = Field(default_factory=list)
    has_significant_gaps: bool = False

    # Anomalies
    anomalies: list[str] = Field(
        default_factory=list, description="Human-readable anomaly descriptions"
    )

    # All entries (enriched)
    entries: list[EnrichedExperience] = Field(default_factory=list)


# ============================================================================
# EDUCATION AND CERTIFICATION (simpler, less processing needed)
# ============================================================================


class EducationEntry(BaseModel):
    """Education entry - minimal processing."""

    institution: str
    degree: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    graduation_month: Optional[int] = None
    grade: Optional[str] = None
    is_current: bool = False


class CertificationEntry(BaseModel):
    """Certification entry."""

    name: str
    issuer: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None


# ============================================================================
# COMPLETE ENRICHED FACTS
# ============================================================================


class EnrichedFacts(BaseModel):
    """
    Complete enriched facts after post-processing.
    This is what gets passed to Phase 2 evaluation.
    """

    experience: ExperienceSummary
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    skill_keywords: list[str] = Field(default_factory=list)
    years_since_graduation: Optional[float] = None

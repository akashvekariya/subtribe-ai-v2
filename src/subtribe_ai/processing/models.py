"""
Resume Parser - Post-Processing Models

Only models for COMPUTED fields that post-processing adds.
BAML output is used directly - no duplication.

Post-processing adds:
- Duration calculations from date strings
- Experience aggregation (totals, gaps, overlaps)
- Date warnings
- Years since graduation
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DateWarning(str, Enum):
    """Warnings generated during date processing."""
    VAGUE_DATE = "vague_date"  # Year-only date (month unknown)
    MISSING_START = "missing_start"
    MISSING_BOTH = "missing_both"
    INVERTED = "inverted"  # End before start
    FUTURE_START = "future_start"
    FUTURE_END = "future_end"


class ExperienceMetrics(BaseModel):
    """Computed metrics for a single experience entry."""
    index: int  # Index in original experience array
    duration_months: int = 0
    warnings: list[str] = Field(default_factory=list)


class Gap(BaseModel):
    """Gap between two experiences."""
    after_company: str
    before_company: str
    months: int
    significant: bool = False  # True if >= 6 months


class ExperienceSummary(BaseModel):
    """Aggregated experience metrics."""
    total_months: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)

    has_overlaps: bool = False
    overlap_months: int = 0

    gaps: list[Gap] = Field(default_factory=list)
    has_significant_gaps: bool = False

    entry_metrics: list[ExperienceMetrics] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProjectMetrics(BaseModel):
    """Computed metrics for a single project entry."""
    index: int
    duration_months: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)


class ComputedFields(BaseModel):
    """
    All computed fields added by post-processing.

    This is returned alongside the original BAML output,
    not replacing it.
    """
    experience_summary: ExperienceSummary
    project_metrics: list[ProjectMetrics] = Field(default_factory=list)

    months_since_graduation: Optional[int] = None
    highest_education_level: Optional[str] = None

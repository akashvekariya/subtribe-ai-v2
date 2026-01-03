"""Utility modules for subtribe-ai.

Contains shared utilities for PDF processing, date parsing,
experience calculations, and tracing.
"""

from subtribe_ai.utils.dates import DateParser
from subtribe_ai.utils.experience import ExperienceCalculator
from subtribe_ai.utils.models import (
    # Input models (from LLM)
    RawDateInput,
    RawExperienceInput,
    # Output models (enriched)
    EnrichedExperience,
    ExperienceSummary,
    EnrichedFacts,
    # Supporting models
    ExperienceType,
    DateAnomaly,
    EmploymentGap,
    EducationEntry,
    CertificationEntry,
)
from subtribe_ai.utils.pdf import extract_links, pdf_to_base64, LinkEntry
from subtribe_ai.utils.link_preprocessor import preprocess_links, links_to_prompt_text

__all__ = [
    # Date/Experience tools
    "DateParser",
    "ExperienceCalculator",
    "RawDateInput",
    "RawExperienceInput",
    "EnrichedExperience",
    "ExperienceSummary",
    "EnrichedFacts",
    "ExperienceType",
    "DateAnomaly",
    "EmploymentGap",
    "EducationEntry",
    "CertificationEntry",
    # PDF utilities
    "extract_links",
    "pdf_to_base64",
    "LinkEntry",
    # Link preprocessing
    "preprocess_links",
    "links_to_prompt_text",
]

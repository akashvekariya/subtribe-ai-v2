"""Utility modules for subtribe-ai.

Contains shared utilities for PDF processing, date parsing,
experience calculations, and tracing.
"""

from subtribe_ai.utils.calibration_helpers import (
    build_calibration_skill_ids,
    build_calibration_tradeoff_ids,
    build_skill_selection_lookup,
    extract_framework_skill_ids,
    extract_framework_tradeoff_ids,
    extract_selected_items,
    extract_selected_skill_ids,
    extract_selected_tradeoff_ids,
    get_calibration_skill_info,
)
from subtribe_ai.utils.dates import DateParser
from subtribe_ai.utils.experience import ExperienceCalculator
from subtribe_ai.utils.link_preprocessor import links_to_prompt_text, preprocess_links
from subtribe_ai.utils.models import (
    CertificationEntry,
    DateAnomaly,
    EducationEntry,
    EmploymentGap,
    # Output models (enriched)
    EnrichedExperience,
    EnrichedFacts,
    ExperienceSummary,
    # Supporting models
    ExperienceType,
    # Input models (from LLM)
    RawDateInput,
    RawExperienceInput,
)
from subtribe_ai.utils.pdf import LinkEntry, extract_links, pdf_to_base64
from subtribe_ai.utils.string_similarity import (
    find_best_match,
    fuzzy_text_match,
    levenshtein_distance,
    similarity_ratio,
)

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
    # String similarity
    "levenshtein_distance",
    "similarity_ratio",
    "find_best_match",
    "fuzzy_text_match",
    # Calibration helpers
    "extract_selected_skill_ids",
    "extract_framework_skill_ids",
    "extract_selected_tradeoff_ids",
    "extract_framework_tradeoff_ids",
    "extract_selected_items",
    "get_calibration_skill_info",
    "build_skill_selection_lookup",
    "build_calibration_skill_ids",
    "build_calibration_tradeoff_ids",
]

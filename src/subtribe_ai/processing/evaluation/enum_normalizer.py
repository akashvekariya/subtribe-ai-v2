"""Enum value normalization for evaluation output.

BAML Python enums serialize as PascalCase, but we expect snake_case.
"""

from typing import Any

# Enum value normalization mappings (PascalCase -> snake_case)
ENUM_NORMALIZATIONS = {
    # SourceType
    "Experience": "experience",
    "Project": "project",
    "Education": "education",
    "Inferred": "inferred",
    "KeywordOnly": "keyword_only",
    # ConstraintStatus
    "Pass": "pass",
    "Fail": "fail",
    "Deferred": "deferred",
    # CandidateDirection
    "OptionA": "option_a",
    "OptionB": "option_b",
    "Balanced": "balanced",
    "Unclear": "unclear",
    # DimensionLevel
    "Strong": "strong",
    "Good": "good",
    "Moderate": "moderate",
    "Weak": "weak",
    "Poor": "poor",
    # RedFlagType
    "ShortTenure": "short_tenure",
    "EmploymentGap": "employment_gap",
    "TitleExperienceMismatch": "title_experience_mismatch",
    "VagueContributions": "vague_contributions",
    "UnverifiableClaims": "unverifiable_claims",
    # RedFlagSeverity
    "Info": "info",
    "Investigate": "investigate",
    "Concern": "concern",
}


def normalize_evaluation_enums(evaluation: dict) -> dict[str, Any]:
    """Normalize enum values in evaluation output (PascalCase -> snake_case).

    Returns dict with normalized_count.
    """
    normalized_count = 0

    # Normalize skill_matches
    for match in evaluation.get("skill_matches", []):
        source_type = match.get("source_type", "")
        if source_type in ENUM_NORMALIZATIONS:
            match["source_type"] = ENUM_NORMALIZATIONS[source_type]
            normalized_count += 1

    # Normalize constraint_results
    for result in evaluation.get("constraint_results", []):
        status = result.get("status", "")
        if status in ENUM_NORMALIZATIONS:
            result["status"] = ENUM_NORMALIZATIONS[status]
            normalized_count += 1

    # Normalize tradeoff_signals
    for signal in evaluation.get("tradeoff_signals", []):
        direction = signal.get("direction", "")
        if direction in ENUM_NORMALIZATIONS:
            signal["direction"] = ENUM_NORMALIZATIONS[direction]
            normalized_count += 1

    # Normalize dimension_assessments
    for assessment in evaluation.get("dimension_assessments", []):
        level = assessment.get("raw_level", "")
        if level in ENUM_NORMALIZATIONS:
            assessment["raw_level"] = ENUM_NORMALIZATIONS[level]
            normalized_count += 1

    # Normalize red_flags
    for flag in evaluation.get("red_flags", []):
        flag_type = flag.get("flag_type", "")
        if flag_type in ENUM_NORMALIZATIONS:
            flag["flag_type"] = ENUM_NORMALIZATIONS[flag_type]
            normalized_count += 1
        severity = flag.get("severity", "")
        if severity in ENUM_NORMALIZATIONS:
            flag["severity"] = ENUM_NORMALIZATIONS[severity]
            normalized_count += 1

    return {"normalized_count": normalized_count}

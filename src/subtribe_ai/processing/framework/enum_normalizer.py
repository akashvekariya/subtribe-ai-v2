"""Enum value normalization for framework output.

BAML Python enums serialize as PascalCase, but we expect snake_case.
"""

from typing import Any

# Enum value normalization mappings (PascalCase -> snake_case)
ENUM_NORMALIZATIONS = {
    # ConstraintType
    "Dealbreaker": "dealbreaker",
    "RequiredDay1": "required_day1",
    "AcceptableGap": "acceptable_gap",
    # ConstraintSeverity
    "Critical": "critical",
    "Important": "important",
    "Minor": "minor",
    # AssessmentMethod
    "Resume": "resume",
    "Interview": "interview",
    "Both": "both",
    # TradeoffDirection
    "OptionA": "option_a",
    "OptionB": "option_b",
    "Balanced": "balanced",
    # PreferenceStrength
    "Strong": "strong",
    "Slight": "slight",
    "Neutral": "neutral",
    # SuspiciousActionTaken
    "Sanitized": "sanitized",
    "Excluded": "excluded",
    "Flagged": "flagged",
    # SuspiciousConcernType
    "InappropriateContent": "inappropriate_content",
    "PromptInjection": "prompt_injection",
    "UnrealisticExpectation": "unrealistic_expectation",
}


def normalize_enum_value(value: str) -> str:
    """Normalize a single enum value from PascalCase to snake_case."""
    return ENUM_NORMALIZATIONS.get(value, value)


def normalize_enum_values_in_framework(framework: dict) -> dict[str, Any]:
    """Normalize all enum values from PascalCase to snake_case.

    BAML Python enums serialize as PascalCase but we expect snake_case.
    This runs FIRST before any other processing.

    Returns:
        Normalization stats dict with normalized_count and fields_processed.
    """
    result: dict[str, Any] = {
        "normalized_count": 0,
        "fields_processed": [],
    }

    # Normalize hard_constraints
    for constraint in framework.get("hard_constraints", []):
        # constraint_type
        orig_type = constraint.get("constraint_type", "")
        normalized_type = normalize_enum_value(orig_type)
        if orig_type != normalized_type:
            constraint["constraint_type"] = normalized_type
            result["normalized_count"] += 1
            result["fields_processed"].append(
                f"hard_constraints.constraint_type: {orig_type} -> {normalized_type}"
            )

        # severity
        orig_sev = constraint.get("severity", "")
        normalized_sev = normalize_enum_value(orig_sev)
        if orig_sev != normalized_sev:
            constraint["severity"] = normalized_sev
            result["normalized_count"] += 1
            result["fields_processed"].append(
                f"hard_constraints.severity: {orig_sev} -> {normalized_sev}"
            )

        # assessment_method
        orig_method = constraint.get("assessment_method", "")
        normalized_method = normalize_enum_value(orig_method)
        if orig_method != normalized_method:
            constraint["assessment_method"] = normalized_method
            result["normalized_count"] += 1
            result["fields_processed"].append(
                f"hard_constraints.assessment_method: {orig_method} -> {normalized_method}"
            )

    # Normalize tradeoff_preferences
    for tradeoff in framework.get("tradeoff_preferences", []):
        # preferred_direction
        orig_dir = tradeoff.get("preferred_direction", "")
        normalized_dir = normalize_enum_value(orig_dir)
        if orig_dir != normalized_dir:
            tradeoff["preferred_direction"] = normalized_dir
            result["normalized_count"] += 1
            result["fields_processed"].append(
                f"tradeoff_preferences.preferred_direction: {orig_dir} -> {normalized_dir}"
            )

        # strength
        orig_str = tradeoff.get("strength", "")
        normalized_str = normalize_enum_value(orig_str)
        if orig_str != normalized_str:
            tradeoff["strength"] = normalized_str
            result["normalized_count"] += 1
            result["fields_processed"].append(
                f"tradeoff_preferences.strength: {orig_str} -> {normalized_str}"
            )

    # Normalize suspicious_items
    for item in framework.get("suspicious_items", []):
        # action_taken
        orig_act = item.get("action_taken", "")
        normalized_act = normalize_enum_value(orig_act)
        if orig_act != normalized_act:
            item["action_taken"] = normalized_act
            result["normalized_count"] += 1
            result["fields_processed"].append(
                f"suspicious_items.action_taken: {orig_act} -> {normalized_act}"
            )

        # concern_type
        orig_concern = item.get("concern_type", "")
        normalized_concern = normalize_enum_value(orig_concern)
        if orig_concern != normalized_concern:
            item["concern_type"] = normalized_concern
            result["normalized_count"] += 1
            result["fields_processed"].append(
                f"suspicious_items.concern_type: {orig_concern} -> {normalized_concern}"
            )

    return result

"""
Framework Post-Processing Pipeline

Deterministic post-processing layer that runs after LLM generates the evaluation framework.
Ensures data integrity, normalizes weights, and handles edge cases.

Approved Decisions:
1. Dimension weights: LLM weights + override if >20% divergence from derived
2. ID mismatch: Accept + fix using Levenshtein distance (CPU-only)
3. Missing items: <=30% add default weight, >30% error + notify
4. Input: camelCase, Output: snake_case (already handled by BAML)

IMPORTANT: This module is role-agnostic. No hardcoded role-specific logic.
All derivations are purely algorithmic based on selection patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PostProcessingConfig:
    """
    Configurable thresholds for post-processing.
    All values are configurable - no magic numbers in the code.
    """
    # Completeness thresholds
    missing_error_threshold_pct: float = 30.0  # Error if missing > this %

    # ID matching thresholds
    id_match_similarity_threshold: float = 0.6  # Min similarity for ID fuzzy match

    # Text matching thresholds (for challenges, milestones, constraints)
    text_match_similarity_threshold: float = 0.7  # Min similarity for text fuzzy match

    # Weight divergence threshold
    weight_divergence_threshold_pct: float = 20.0  # Warn if LLM diverges > this %

    # Selection multipliers
    selected_multiplier: float = 1.0  # Multiplier for selected items
    unselected_multiplier: float = 0.3  # Multiplier for unselected items

    # Default weights for missing items
    default_weight_custom: int = 4  # Default weight for custom items (higher priority)
    default_weight_llm: int = 3  # Default weight for LLM-suggested items


# Default config instance
DEFAULT_CONFIG = PostProcessingConfig()


@dataclass
class PostProcessingResult:
    """Result of post-processing pipeline."""
    framework: dict
    metadata: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    requires_human_review: bool = False


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


def normalize_enum_values_in_framework(framework: dict) -> dict:
    """
    Stage 0: Normalize all enum values from PascalCase to snake_case.

    BAML Python enums serialize as PascalCase but we expect snake_case.
    This runs FIRST before any other processing.

    Returns normalization stats.
    """
    result = {
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
            result["fields_processed"].append(f"hard_constraints.constraint_type: {orig_type} -> {normalized_type}")

        # severity
        orig_sev = constraint.get("severity", "")
        normalized_sev = normalize_enum_value(orig_sev)
        if orig_sev != normalized_sev:
            constraint["severity"] = normalized_sev
            result["normalized_count"] += 1
            result["fields_processed"].append(f"hard_constraints.severity: {orig_sev} -> {normalized_sev}")

        # assessment_method
        orig_method = constraint.get("assessment_method", "")
        normalized_method = normalize_enum_value(orig_method)
        if orig_method != normalized_method:
            constraint["assessment_method"] = normalized_method
            result["normalized_count"] += 1
            result["fields_processed"].append(f"hard_constraints.assessment_method: {orig_method} -> {normalized_method}")

    # Normalize tradeoff_preferences
    for tradeoff in framework.get("tradeoff_preferences", []):
        # preferred_direction
        orig_dir = tradeoff.get("preferred_direction", "")
        normalized_dir = normalize_enum_value(orig_dir)
        if orig_dir != normalized_dir:
            tradeoff["preferred_direction"] = normalized_dir
            result["normalized_count"] += 1
            result["fields_processed"].append(f"tradeoff_preferences.preferred_direction: {orig_dir} -> {normalized_dir}")

        # strength
        orig_str = tradeoff.get("strength", "")
        normalized_str = normalize_enum_value(orig_str)
        if orig_str != normalized_str:
            tradeoff["strength"] = normalized_str
            result["normalized_count"] += 1
            result["fields_processed"].append(f"tradeoff_preferences.strength: {orig_str} -> {normalized_str}")

    # Normalize suspicious_items
    for item in framework.get("suspicious_items", []):
        # action_taken
        orig_act = item.get("action_taken", "")
        normalized_act = normalize_enum_value(orig_act)
        if orig_act != normalized_act:
            item["action_taken"] = normalized_act
            result["normalized_count"] += 1
            result["fields_processed"].append(f"suspicious_items.action_taken: {orig_act} -> {normalized_act}")

        # concern_type
        orig_concern = item.get("concern_type", "")
        normalized_concern = normalize_enum_value(orig_concern)
        if orig_concern != normalized_concern:
            item["concern_type"] = normalized_concern
            result["normalized_count"] += 1
            result["fields_processed"].append(f"suspicious_items.concern_type: {orig_concern} -> {normalized_concern}")

    return result


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    CPU-only implementation, no external dependencies.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """
    Calculate similarity ratio (0.0 to 1.0) between two strings.
    Higher = more similar.
    """
    if not s1 or not s2:
        return 0.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    distance = levenshtein_distance(s1.lower(), s2.lower())
    return 1.0 - (distance / max_len)


def find_best_match(
    target_id: str,
    candidate_ids: list[str],
    threshold: float
) -> tuple[str | None, float]:
    """
    Find the best matching ID from candidates using Levenshtein distance.
    Returns (best_match, similarity_score) or (None, 0) if no match above threshold.
    """
    best_match = None
    best_score = 0.0

    for candidate in candidate_ids:
        score = similarity_ratio(target_id, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= threshold:
        return best_match, best_score
    return None, 0.0


def fuzzy_text_match(
    expected_items: set[str],
    found_items: set[str],
    threshold: float
) -> list[str]:
    """
    Find items from expected that don't have a fuzzy match in found.
    Returns list of missing items.
    Role-agnostic - purely string-based matching.
    """
    missing = []
    for exp in expected_items:
        found = False
        for fnd in found_items:
            if similarity_ratio(exp, fnd) >= threshold:
                found = True
                break
        if not found:
            missing.append(exp)
    return missing


def extract_selected_skill_ids(calibration: dict) -> set[str]:
    """Extract all selected skill IDs from calibration (both mustHave and goodToHave)."""
    skill_ids = set()
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})

    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            if item.get("selected", False):
                skill_ids.add(item.get("id", ""))

    return skill_ids


def extract_framework_skill_ids(framework: dict) -> set[str]:
    """Extract all skill IDs from framework output."""
    skill_ids = set()
    skill_criteria = framework.get("skill_criteria", {})
    for skill in skill_criteria.get("skills", []):
        skill_ids.add(skill.get("skill_id", ""))
    return skill_ids


def extract_selected_tradeoff_ids(calibration: dict) -> set[str]:
    """Extract all answered tradeoff IDs from calibration."""
    tradeoff_ids = set()
    cal_summary = calibration.get("calibrationSummary", {})
    tradeoffs = cal_summary.get("tradeoffs", {})

    for section_key in ["experience", "roleSpecific"]:
        section = tradeoffs.get(section_key, {})
        for item in section.get("items", []):
            if item.get("answered", False):
                tradeoff_ids.add(item.get("id", ""))

    return tradeoff_ids


def extract_framework_tradeoff_ids(framework: dict) -> set[str]:
    """Extract all tradeoff IDs from framework output."""
    tradeoff_ids = set()
    for tradeoff in framework.get("tradeoff_preferences", []):
        tradeoff_ids.add(tradeoff.get("tradeoff_id", ""))
    return tradeoff_ids


def extract_selected_items(calibration: dict, section_path: list[str]) -> list[str]:
    """
    Extract selected item values from a nested calibration section.
    section_path: list of keys to traverse, e.g., ["redFlags", "rejectionBehaviors"]
    """
    items = []
    current = calibration.get("calibrationSummary", {})

    for key in section_path:
        current = current.get(key, {})
        if not current:
            return items

    for item in current.get("items", []):
        if item.get("selected", False):
            items.append(item.get("value", ""))

    return items


def validate_completeness(
    calibration: dict,
    framework: dict,
    config: PostProcessingConfig
) -> dict:
    """
    Stage 1: Validate that all selected items from calibration appear in framework.
    Returns validation result with missing items.
    """
    result = {
        "passed": True,
        "missing_skills": [],
        "missing_tradeoffs": [],
        "missing_challenges": [],
        "missing_milestones": [],
        "missing_dealbreakers": [],
        "missing_trainable_gaps": [],
        "missing_required_day1": [],
        "total_expected": 0,
        "total_found": 0,
        "missing_percentage": 0.0,
    }

    text_threshold = config.text_match_similarity_threshold

    # Check skills (exact ID match)
    expected_skills = extract_selected_skill_ids(calibration)
    found_skills = extract_framework_skill_ids(framework)
    missing_skills = expected_skills - found_skills
    result["missing_skills"] = list(missing_skills)

    # Check tradeoffs (exact ID match)
    expected_tradeoffs = extract_selected_tradeoff_ids(calibration)
    found_tradeoffs = extract_framework_tradeoff_ids(framework)
    missing_tradeoffs = expected_tradeoffs - found_tradeoffs
    result["missing_tradeoffs"] = list(missing_tradeoffs)

    # Check challenges (fuzzy text match - LLM may rephrase)
    expected_challenges = set(extract_selected_items(calibration, ["challenges"]))
    found_challenges = set(framework.get("success_criteria", {}).get("key_challenges", []))
    result["missing_challenges"] = fuzzy_text_match(expected_challenges, found_challenges, text_threshold)

    # Check day 60 milestones (fuzzy text match)
    expected_milestones = set(extract_selected_items(calibration, ["day60Milestones"]))
    found_milestones = set(framework.get("success_criteria", {}).get("day_60_milestones", []))
    result["missing_milestones"] = fuzzy_text_match(expected_milestones, found_milestones, text_threshold)

    # Check hard constraints by type
    expected_dealbreakers = set(extract_selected_items(calibration, ["redFlags", "rejectionBehaviors"]))
    expected_trainable = set(extract_selected_items(calibration, ["redFlags", "trainableGaps"]))
    expected_day1 = set(extract_selected_items(calibration, ["redFlags", "nonTrainableGaps"]))

    found_constraints = framework.get("hard_constraints", [])
    found_dealbreakers = set()
    found_trainable = set()
    found_day1 = set()

    for constraint in found_constraints:
        orig_text = constraint.get("original_text", "")
        constraint_type = constraint.get("constraint_type", "")
        if constraint_type == "dealbreaker":
            found_dealbreakers.add(orig_text)
        elif constraint_type == "acceptable_gap":
            found_trainable.add(orig_text)
        elif constraint_type == "required_day1":
            found_day1.add(orig_text)

    result["missing_dealbreakers"] = fuzzy_text_match(expected_dealbreakers, found_dealbreakers, text_threshold)
    result["missing_trainable_gaps"] = fuzzy_text_match(expected_trainable, found_trainable, text_threshold)
    result["missing_required_day1"] = fuzzy_text_match(expected_day1, found_day1, text_threshold)

    # Calculate totals
    total_expected = (
        len(expected_skills) + len(expected_tradeoffs) +
        len(expected_challenges) + len(expected_milestones) +
        len(expected_dealbreakers) + len(expected_trainable) + len(expected_day1)
    )
    total_missing = (
        len(result["missing_skills"]) + len(result["missing_tradeoffs"]) +
        len(result["missing_challenges"]) + len(result["missing_milestones"]) +
        len(result["missing_dealbreakers"]) + len(result["missing_trainable_gaps"]) +
        len(result["missing_required_day1"])
    )
    total_found = total_expected - total_missing

    result["total_expected"] = total_expected
    result["total_found"] = total_found
    result["missing_percentage"] = (total_missing / total_expected * 100) if total_expected > 0 else 0.0
    result["passed"] = total_missing == 0

    return result


def validate_and_fix_ids(
    calibration: dict,
    framework: dict,
    config: PostProcessingConfig
) -> dict:
    """
    Stage 2: Validate skill_id and tradeoff_id match input exactly.
    If not exact match, try fuzzy match and fix.
    Returns validation result with fixes applied.
    """
    result = {
        "passed": True,
        "skill_fixes": [],
        "tradeoff_fixes": [],
        "unfixable_skills": [],
        "unfixable_tradeoffs": [],
    }

    id_threshold = config.id_match_similarity_threshold

    # Build calibration ID sets
    calibration_skill_ids = set()
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})
    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            calibration_skill_ids.add(item.get("id", ""))

    calibration_tradeoff_ids = set()
    tradeoffs = cal_summary.get("tradeoffs", {})
    for section_key in ["experience", "roleSpecific"]:
        section = tradeoffs.get(section_key, {})
        for item in section.get("items", []):
            calibration_tradeoff_ids.add(item.get("id", ""))

    # Fix skill IDs
    skill_criteria = framework.get("skill_criteria", {})
    for skill in skill_criteria.get("skills", []):
        skill_id = skill.get("skill_id", "")
        if skill_id not in calibration_skill_ids:
            # Try fuzzy match
            best_match, score = find_best_match(skill_id, list(calibration_skill_ids), id_threshold)
            if best_match:
                result["skill_fixes"].append({
                    "original": skill_id,
                    "fixed_to": best_match,
                    "similarity": round(score, 3)
                })
                skill["skill_id"] = best_match
            else:
                result["unfixable_skills"].append(skill_id)
                result["passed"] = False

    # Fix tradeoff IDs
    for tradeoff in framework.get("tradeoff_preferences", []):
        tradeoff_id = tradeoff.get("tradeoff_id", "")
        if tradeoff_id not in calibration_tradeoff_ids:
            # Try fuzzy match
            best_match, score = find_best_match(tradeoff_id, list(calibration_tradeoff_ids), id_threshold)
            if best_match:
                result["tradeoff_fixes"].append({
                    "original": tradeoff_id,
                    "fixed_to": best_match,
                    "similarity": round(score, 3)
                })
                tradeoff["tradeoff_id"] = best_match
            else:
                result["unfixable_tradeoffs"].append(tradeoff_id)
                result["passed"] = False

    return result


def normalize_weights(framework: dict) -> dict:
    """
    Stage 3: Normalize weights to sum to 1.0.
    Role-agnostic - works with any weight arrays.
    Returns normalization result.
    """
    result = {
        "dimension_weights_adjusted": False,
        "category_weights_adjusted": False,
        "original_dimension_total": 0.0,
        "original_category_total": 0.0,
    }

    # Normalize dimension weights
    dimension_weights = framework.get("dimension_weights", [])
    if dimension_weights:
        total = sum(d.get("weight", 0) for d in dimension_weights)
        result["original_dimension_total"] = round(total, 4)
        if total > 0 and abs(total - 1.0) > 0.001:
            for d in dimension_weights:
                d["weight"] = round(d["weight"] / total, 3)
            result["dimension_weights_adjusted"] = True

    # Normalize category weights
    skill_criteria = framework.get("skill_criteria", {})
    category_weights = skill_criteria.get("category_weights", [])
    if category_weights:
        total = sum(c.get("weight", 0) for c in category_weights)
        result["original_category_total"] = round(total, 4)
        if total > 0 and abs(total - 1.0) > 0.001:
            for c in category_weights:
                c["weight"] = round(c["weight"] / total, 3)
            result["category_weights_adjusted"] = True

    return result


def apply_selection_multipliers(
    calibration: dict,
    framework: dict,
    config: PostProcessingConfig
) -> dict:
    """
    Stage 4: Apply selection multipliers.
    Adds effective_weight to each skill.
    Role-agnostic - multipliers from config.
    """
    result = {
        "skills_processed": 0,
        "selected_count": 0,
        "unselected_count": 0,
    }

    # Build selection lookup from calibration
    selection_lookup = {}
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})
    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            skill_id = item.get("id", "")
            selection_lookup[skill_id] = item.get("selected", False)

    # Apply multipliers from config
    skill_criteria = framework.get("skill_criteria", {})
    for skill in skill_criteria.get("skills", []):
        skill_id = skill.get("skill_id", "")
        weight = skill.get("weight", 3)

        is_selected = selection_lookup.get(skill_id, True)  # Default to selected if not found
        multiplier = config.selected_multiplier if is_selected else config.unselected_multiplier

        skill["effective_weight"] = round(weight * multiplier, 2)
        skill["selection_multiplier"] = multiplier

        result["skills_processed"] += 1
        if is_selected:
            result["selected_count"] += 1
        else:
            result["unselected_count"] += 1

    return result


def validate_custom_boost(calibration: dict, framework: dict) -> dict:
    """
    Stage 5: Validate custom items received appropriate weight.
    Role-agnostic - just checks source="custom" items.
    """
    result = {
        "custom_items_found": 0,
        "items_with_low_weight": [],
    }

    # Find custom items in calibration
    custom_skill_ids = set()
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})
    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            if item.get("source") == "custom":
                custom_skill_ids.add(item.get("id", ""))

    result["custom_items_found"] = len(custom_skill_ids)

    # Check weights - custom items should have boosted weights
    skill_criteria = framework.get("skill_criteria", {})
    for skill in skill_criteria.get("skills", []):
        skill_id = skill.get("skill_id", "")
        if skill_id in custom_skill_ids:
            current_weight = skill.get("weight", 3)
            skill["source"] = "custom"
            # Flag if weight seems low for a custom item (recruiter-added = important)
            if current_weight < 3:
                result["items_with_low_weight"].append({
                    "skill_id": skill_id,
                    "current_weight": current_weight,
                    "concern": "Custom item has low weight - verify LLM applied boost"
                })

    return result


def validate_skill_counts(framework: dict) -> dict:
    """
    Stage 6: Recalculate and validate skill counts.
    Role-agnostic - counts based on is_required field.
    """
    result = {
        "original_required": 0,
        "original_preferred": 0,
        "calculated_required": 0,
        "calculated_preferred": 0,
        "counts_adjusted": False,
    }

    skill_criteria = framework.get("skill_criteria", {})
    result["original_required"] = skill_criteria.get("total_required_skills", 0)
    result["original_preferred"] = skill_criteria.get("total_preferred_skills", 0)

    # Recalculate based on actual skills array
    required_count = 0
    preferred_count = 0
    for skill in skill_criteria.get("skills", []):
        if skill.get("is_required", False):
            required_count += 1
        else:
            preferred_count += 1

    result["calculated_required"] = required_count
    result["calculated_preferred"] = preferred_count

    # Fix if counts don't match
    if result["original_required"] != required_count or result["original_preferred"] != preferred_count:
        skill_criteria["total_required_skills"] = required_count
        skill_criteria["total_preferred_skills"] = preferred_count
        result["counts_adjusted"] = True

    return result


def derive_dimension_weights_from_selections(calibration: dict) -> dict:
    """
    Stage 7: Derive dimension weights purely from selection patterns.

    ROLE-AGNOSTIC APPROACH:
    - No hardcoded category names or role-specific logic
    - Weights derived purely from selection ratios in each calibration section
    - Works for any role type (technical, sales, creative, etc.)

    Algorithm:
    Each dimension weight is derived from selection ratios in related sections.
    The mapping is based on what data logically feeds into each dimension:
    - technical_fit: skills selection ratio
    - experience_fit: tradeoff values (1-5 scale converted to weight)
    - trajectory_fit: trajectory selection + tradeoff patterns
    - culture_fit: soft priorities + red flags patterns
    - problem_solving_fit: problem types + challenges selection

    All weights use ONLY selection ratios from the data - no magic multipliers.
    Final weights are normalized to sum to 1.0.
    """
    cal_summary = calibration.get("calibrationSummary", {})

    # Calculate selection ratios from each section
    ratios = {}

    # 1. Skills selection ratio
    skills = cal_summary.get("skills", {})
    total_skills = 0
    selected_skills = 0
    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            total_skills += 1
            if item.get("selected", False):
                selected_skills += 1
    ratios["skills"] = selected_skills / total_skills if total_skills > 0 else 0.5

    # 2. Tradeoff values (convert 1-5 scale to 0-1)
    tradeoffs = cal_summary.get("tradeoffs", {})
    tradeoff_values = []
    for section_key in ["experience", "roleSpecific"]:
        section = tradeoffs.get(section_key, {})
        for item in section.get("items", []):
            if item.get("answered", False):
                tradeoff_values.append(item.get("value", 3))
    avg_tradeoff = sum(tradeoff_values) / len(tradeoff_values) if tradeoff_values else 3.0
    ratios["tradeoffs"] = (avg_tradeoff - 1) / 4  # 1->0, 3->0.5, 5->1

    # 3. Problem types selection ratio
    problem_types = cal_summary.get("problemTypes", {})
    problem_stats = problem_types.get("stats", {})
    ratios["problems"] = problem_stats.get("selected", 0) / max(problem_stats.get("total", 1), 1)

    # 4. Challenges selection ratio
    challenges = cal_summary.get("challenges", {})
    challenge_stats = challenges.get("stats", {})
    ratios["challenges"] = challenge_stats.get("selected", 0) / max(challenge_stats.get("total", 1), 1)

    # 5. Assessment priorities selection ratio
    priorities = cal_summary.get("assessmentPriorities", {})
    priority_stats = priorities.get("stats", {})
    ratios["priorities"] = priority_stats.get("selected", 0) / max(priority_stats.get("total", 1), 1)

    # 6. Red flags selection ratio (indicates culture/behavioral focus)
    red_flags = cal_summary.get("redFlags", {})
    total_flags = 0
    selected_flags = 0
    for section_key in ["rejectionBehaviors", "trainableGaps", "nonTrainableGaps"]:
        section = red_flags.get(section_key, {})
        stats = section.get("stats", {})
        total_flags += stats.get("total", 0)
        selected_flags += stats.get("selected", 0)
    ratios["redflags"] = selected_flags / total_flags if total_flags > 0 else 0.5

    # 7. Day 60 milestones selection ratio
    milestones = cal_summary.get("day60Milestones", {})
    milestone_stats = milestones.get("stats", {})
    ratios["milestones"] = milestone_stats.get("selected", 0) / max(milestone_stats.get("total", 1), 1)

    # Derive dimension weights purely from ratios
    # Each dimension = average of relevant ratios (no magic multipliers)
    derived = {}

    # technical_fit: driven by skills + priorities
    derived["technical_fit"] = (ratios["skills"] + ratios["priorities"]) / 2

    # experience_fit: inversely related to tradeoff value
    # (low tradeoff value = prefer experienced = higher weight)
    derived["experience_fit"] = 1.0 - ratios["tradeoffs"]

    # trajectory_fit: driven by milestones + tradeoffs
    derived["trajectory_fit"] = (ratios["milestones"] + ratios["tradeoffs"]) / 2

    # culture_fit: driven by red flags + priorities
    derived["culture_fit"] = (ratios["redflags"] + ratios["priorities"]) / 2

    # problem_solving_fit: driven by problems + challenges
    derived["problem_solving_fit"] = (ratios["problems"] + ratios["challenges"]) / 2

    # Normalize to sum to 1.0
    total = sum(derived.values())
    if total > 0:
        for key in derived:
            derived[key] = round(derived[key] / total, 3)

    return derived


REQUIRED_DIMENSIONS = [
    "technical_fit",
    "experience_fit",
    "trajectory_fit",
    "culture_fit",
    "problem_solving_fit",
]


def ensure_all_dimensions_present(
    framework: dict,
    derived_weights: dict
) -> dict:
    """
    Ensure all 5 required dimensions are present in framework.
    Add missing dimensions with derived weights.
    """
    result = {
        "missing_dimensions": [],
        "dimensions_added": [],
    }

    dimension_weights = framework.get("dimension_weights", [])
    existing_dims = {d.get("dimension", "") for d in dimension_weights}

    for dim in REQUIRED_DIMENSIONS:
        if dim not in existing_dims:
            result["missing_dimensions"].append(dim)
            derived_weight = derived_weights.get(dim, 0.15)  # Default fallback

            new_dimension = {
                "dimension": dim,
                "weight_rationale": f"Added during post-processing - was missing from LLM output. Weight derived from calibration selection patterns.",
                "weight": derived_weight,
                "description": f"{dim.replace('_', ' ').title()} dimension for candidate evaluation",
                "selected_signals": [],
                "unselected_signals": [],
            }
            dimension_weights.append(new_dimension)
            result["dimensions_added"].append(dim)

    return result


def compare_dimension_weights(
    llm_weights: list[dict],
    derived_weights: dict,
    config: PostProcessingConfig
) -> dict:
    """
    Compare LLM-generated dimension weights with derived weights.
    Flag if divergence exceeds threshold.
    Role-agnostic - compares whatever dimensions exist.
    """
    result = {
        "max_divergence": 0.0,
        "divergent_dimensions": [],
        "needs_override": False,
    }

    threshold = config.weight_divergence_threshold_pct / 100.0

    llm_lookup = {}
    for w in llm_weights:
        dim = w.get("dimension", "")
        llm_lookup[dim] = w.get("weight", 0)

    for dim, derived_value in derived_weights.items():
        llm_value = llm_lookup.get(dim, 0)
        if derived_value > 0:
            divergence = abs(llm_value - derived_value) / derived_value
            if divergence > result["max_divergence"]:
                result["max_divergence"] = divergence
            if divergence > threshold:
                result["divergent_dimensions"].append({
                    "dimension": dim,
                    "llm_weight": llm_value,
                    "derived_weight": derived_value,
                    "divergence_pct": round(divergence * 100, 1)
                })

    result["needs_override"] = result["max_divergence"] > threshold
    result["max_divergence"] = round(result["max_divergence"] * 100, 1)

    return result


def review_suspicious_items(framework: dict) -> dict:
    """
    Stage 8: Review suspicious items flagged by LLM.
    Role-agnostic - just checks action_taken field.
    """
    result = {
        "flagged_count": 0,
        "excluded_count": 0,
        "sanitized_count": 0,
        "needs_human_review": False,
        "flagged_items": [],
    }

    suspicious_items = framework.get("suspicious_items", [])
    for item in suspicious_items:
        action = item.get("action_taken", "")
        if action == "flagged":
            result["flagged_count"] += 1
            result["flagged_items"].append(item)
            result["needs_human_review"] = True
        elif action == "excluded":
            result["excluded_count"] += 1
        elif action == "sanitized":
            result["sanitized_count"] += 1

    return result


def add_missing_items_with_defaults(
    calibration: dict,
    framework: dict,
    missing: dict,
    config: PostProcessingConfig
) -> dict:
    """
    Add missing items to framework with default weights.
    Only called when missing <= threshold.
    Role-agnostic - preserves original category from calibration.
    """
    result = {
        "skills_added": 0,
        "constraints_added": 0,
    }

    # Build lookup for calibration items - preserve ALL original fields
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})
    skill_lookup = {}
    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            skill_lookup[item.get("id", "")] = {
                "name": item.get("name", ""),
                "category": item.get("category", ""),  # Preserve original, don't default
                "source": item.get("source", "llm"),
                "is_required": section_key == "mustHave",
            }

    # Add missing skills with appropriate default weight
    skill_criteria = framework.get("skill_criteria", {})
    for skill_id in missing.get("missing_skills", []):
        if skill_id in skill_lookup:
            info = skill_lookup[skill_id]
            # Use config for default weights
            default_weight = (
                config.default_weight_custom
                if info["source"] == "custom"
                else config.default_weight_llm
            )
            new_skill = {
                "skill_id": skill_id,
                "name": info["name"],
                "category": info["category"],
                "weight_rationale": "Added during post-processing - was missing from LLM output",
                "weight": default_weight,
                "is_required": info["is_required"],
                "is_dealbreaker": False,
                "effective_weight": default_weight * config.selected_multiplier,
                "selection_multiplier": config.selected_multiplier,
            }
            if info["source"] == "custom":
                new_skill["source"] = "custom"
            skill_criteria.setdefault("skills", []).append(new_skill)
            result["skills_added"] += 1

    # Add missing constraints
    hard_constraints = framework.setdefault("hard_constraints", [])

    for text in missing.get("missing_dealbreakers", []):
        hard_constraints.append({
            "constraint_type": "dealbreaker",
            "original_text": text,
            "description": text,
            "resume_check": "Check resume for any indication of this",
            "severity": "important",
        })
        result["constraints_added"] += 1

    for text in missing.get("missing_trainable_gaps", []):
        hard_constraints.append({
            "constraint_type": "acceptable_gap",
            "original_text": text,
            "description": text,
            "resume_check": "Acceptable if missing - can be trained",
            "severity": "minor",
        })
        result["constraints_added"] += 1

    for text in missing.get("missing_required_day1", []):
        hard_constraints.append({
            "constraint_type": "required_day1",
            "original_text": text,
            "description": text,
            "resume_check": "Must be evident in resume - non-trainable",
            "severity": "critical",
        })
        result["constraints_added"] += 1

    return result


def run_post_processing_pipeline(
    calibration: dict,
    framework: dict,
    config: PostProcessingConfig | None = None
) -> PostProcessingResult:
    """
    Main entry point: Run the complete post-processing pipeline.

    Pipeline stages (all role-agnostic):
    1. Completeness validation
    2. ID validation and fixing
    3. Weight normalization
    4. Selection multiplier application
    5. Custom item boost validation
    6. Skill count validation
    7. Dimension weight derivation and comparison
    8. Suspicious items review

    Args:
        calibration: Original calibration dict (camelCase)
        framework: LLM-generated framework dict (snake_case)
        config: Optional config overrides. Uses DEFAULT_CONFIG if not provided.

    Returns:
        PostProcessingResult with processed framework, metadata, errors, warnings
    """
    if config is None:
        config = DEFAULT_CONFIG

    result = PostProcessingResult(framework=framework)
    metadata = {
        "completed_at": datetime.utcnow().isoformat(),
        "version": "1.1",
        "config": {
            "missing_error_threshold_pct": config.missing_error_threshold_pct,
            "id_match_similarity_threshold": config.id_match_similarity_threshold,
            "text_match_similarity_threshold": config.text_match_similarity_threshold,
            "weight_divergence_threshold_pct": config.weight_divergence_threshold_pct,
        },
        "stages": {}
    }

    # Stage 0: Enum normalization (MUST run first)
    # BAML Python enums serialize as PascalCase, we need snake_case
    enum_norm = normalize_enum_values_in_framework(framework)
    metadata["stages"]["enum_normalization"] = enum_norm
    if enum_norm["normalized_count"] > 0:
        result.warnings.append({
            "stage": "enum_normalization",
            "message": f"Normalized {enum_norm['normalized_count']} enum values from PascalCase to snake_case",
        })

    # Stage 1: Completeness validation
    completeness = validate_completeness(calibration, framework, config)
    metadata["stages"]["completeness"] = completeness

    # Decision: If missing > threshold, raise error. Otherwise, add defaults.
    if completeness["missing_percentage"] > config.missing_error_threshold_pct:
        result.errors.append({
            "stage": "completeness",
            "message": f"Missing {completeness['missing_percentage']:.1f}% of selected items (threshold: {config.missing_error_threshold_pct}%)",
            "details": completeness
        })
    elif not completeness["passed"]:
        # Add missing items with defaults
        add_result = add_missing_items_with_defaults(calibration, framework, completeness, config)
        metadata["stages"]["completeness"]["items_added"] = add_result
        result.warnings.append({
            "stage": "completeness",
            "message": f"Added {add_result['skills_added']} skills and {add_result['constraints_added']} constraints with default weights",
        })

    # Stage 2: ID validation and fixing
    id_validation = validate_and_fix_ids(calibration, framework, config)
    metadata["stages"]["id_validation"] = id_validation

    if id_validation["skill_fixes"] or id_validation["tradeoff_fixes"]:
        result.warnings.append({
            "stage": "id_validation",
            "message": f"Fixed {len(id_validation['skill_fixes'])} skill IDs and {len(id_validation['tradeoff_fixes'])} tradeoff IDs using Levenshtein matching",
        })

    if not id_validation["passed"]:
        result.errors.append({
            "stage": "id_validation",
            "message": "Some IDs could not be matched to calibration",
            "details": {
                "unfixable_skills": id_validation["unfixable_skills"],
                "unfixable_tradeoffs": id_validation["unfixable_tradeoffs"],
            }
        })

    # Stage 3: Weight normalization
    weight_norm = normalize_weights(framework)
    metadata["stages"]["weight_normalization"] = weight_norm

    # Stage 4: Selection multipliers
    multipliers = apply_selection_multipliers(calibration, framework, config)
    metadata["stages"]["selection_multipliers"] = multipliers

    # Stage 5: Custom boost validation
    custom_boost = validate_custom_boost(calibration, framework)
    metadata["stages"]["custom_boost"] = custom_boost

    if custom_boost["items_with_low_weight"]:
        result.warnings.append({
            "stage": "custom_boost",
            "message": f"Found {len(custom_boost['items_with_low_weight'])} custom items with potentially low weights",
            "details": custom_boost["items_with_low_weight"],
        })

    # Stage 6: Skill counts
    skill_counts = validate_skill_counts(framework)
    metadata["stages"]["skill_counts"] = skill_counts

    # Stage 7: Dimension weight derivation and comparison
    derived_weights = derive_dimension_weights_from_selections(calibration)
    metadata["stages"]["derived_dimension_weights"] = derived_weights

    # Ensure all 5 required dimensions are present
    dimension_check = ensure_all_dimensions_present(framework, derived_weights)
    metadata["stages"]["dimension_completeness"] = dimension_check

    if dimension_check["dimensions_added"]:
        result.warnings.append({
            "stage": "dimension_completeness",
            "message": f"Added {len(dimension_check['dimensions_added'])} missing dimensions: {', '.join(dimension_check['dimensions_added'])}",
        })

    weight_comparison = compare_dimension_weights(
        framework.get("dimension_weights", []),
        derived_weights,
        config
    )
    metadata["stages"]["dimension_weight_comparison"] = weight_comparison

    if weight_comparison["needs_override"]:
        result.warnings.append({
            "stage": "dimension_weights",
            "message": f"LLM weights diverge from derived weights by {weight_comparison['max_divergence']}% (threshold: {config.weight_divergence_threshold_pct}%)",
            "details": weight_comparison["divergent_dimensions"],
        })
        # Note: We don't auto-override in v1, just warn

    # Stage 8: Suspicious items review
    suspicious = review_suspicious_items(framework)
    metadata["stages"]["suspicious_items"] = suspicious

    if suspicious["needs_human_review"]:
        result.requires_human_review = True
        result.warnings.append({
            "stage": "suspicious_items",
            "message": f"{suspicious['flagged_count']} items flagged for human review",
            "details": suspicious["flagged_items"],
        })

    # Add metadata to framework
    framework["post_processing"] = metadata
    result.metadata = metadata

    return result

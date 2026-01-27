"""Framework validation stages.

Each stage validates or fixes a specific aspect of the LLM-generated framework.
All validators are role-agnostic - no hardcoded role-specific logic.
"""

from typing import Any

from subtribe_ai.processing.framework.config import PostProcessingConfig
from subtribe_ai.utils.calibration_helpers import (
    build_calibration_skill_ids,
    build_calibration_tradeoff_ids,
    build_skill_selection_lookup,
    extract_framework_skill_ids,
    extract_framework_tradeoff_ids,
    extract_selected_items,
    extract_selected_skill_ids,
    extract_selected_tradeoff_ids,
)
from subtribe_ai.utils.string_similarity import find_best_match, fuzzy_text_match


def validate_completeness(
    calibration: dict,
    framework: dict,
    config: PostProcessingConfig
) -> dict[str, Any]:
    """Stage 1: Validate that all selected items from calibration appear in framework.

    Returns validation result with missing items.
    """
    result: dict[str, Any] = {
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
) -> dict[str, Any]:
    """Stage 2: Validate skill_id and tradeoff_id match input exactly.

    If not exact match, try fuzzy match and fix.
    Returns validation result with fixes applied.
    """
    result: dict[str, Any] = {
        "passed": True,
        "skill_fixes": [],
        "tradeoff_fixes": [],
        "unfixable_skills": [],
        "unfixable_tradeoffs": [],
    }

    id_threshold = config.id_match_similarity_threshold

    # Build calibration ID sets
    calibration_skill_ids = build_calibration_skill_ids(calibration)
    calibration_tradeoff_ids = build_calibration_tradeoff_ids(calibration)

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


def normalize_weights(framework: dict) -> dict[str, Any]:
    """Stage 3: Normalize weights to sum to 1.0.

    Role-agnostic - works with any weight arrays.
    Returns normalization result.
    """
    result: dict[str, Any] = {
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
) -> dict[str, Any]:
    """Stage 4: Apply selection multipliers.

    Adds effective_weight to each skill.
    Role-agnostic - multipliers from config.
    """
    result: dict[str, Any] = {
        "skills_processed": 0,
        "selected_count": 0,
        "unselected_count": 0,
    }

    # Build selection lookup from calibration
    selection_lookup = build_skill_selection_lookup(calibration)

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


def validate_custom_boost(calibration: dict, framework: dict) -> dict[str, Any]:
    """Stage 5: Validate custom items received appropriate weight.

    Role-agnostic - just checks source="custom" items.
    """
    result: dict[str, Any] = {
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


def validate_skill_counts(framework: dict) -> dict[str, Any]:
    """Stage 6: Recalculate and validate skill counts.

    Role-agnostic - counts based on is_required field.
    """
    result: dict[str, Any] = {
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


def review_suspicious_items(framework: dict) -> dict[str, Any]:
    """Stage 8: Review suspicious items flagged by LLM.

    Role-agnostic - just checks action_taken field.
    """
    result: dict[str, Any] = {
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
) -> dict[str, Any]:
    """Add missing items to framework with default weights.

    Only called when missing <= threshold.
    Role-agnostic - preserves original category from calibration.
    """
    result: dict[str, Any] = {
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

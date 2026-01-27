"""Evaluation post-processing pipeline.

Main entry point for evaluation scoring and enrichment.
"""

from typing import Any

from subtribe_ai.processing.evaluation.config import (
    DEFAULT_CONFIG,
    EvaluationConfig,
)
from subtribe_ai.processing.evaluation.enrichment import (
    enrich_evaluation,
    sanitize_for_frontend,
)
from subtribe_ai.processing.evaluation.enum_normalizer import normalize_evaluation_enums
from subtribe_ai.processing.evaluation.reconciliation import reconcile_skill_matches
from subtribe_ai.processing.evaluation.scoring import calculate_final_scores
from subtribe_ai.processing.evaluation.summaries import (
    calculate_experience_summary,
    calculate_red_flag_summary,
    calculate_source_summary,
)


def _determine_tier(score: float, config: EvaluationConfig) -> str:
    """Determine tier based on score."""
    if score >= config.tier_thresholds["strong_match"]:
        return "strong_match"
    elif score >= config.tier_thresholds["good_match"]:
        return "good_match"
    elif score >= config.tier_thresholds["moderate_match"]:
        return "moderate_match"
    elif score >= config.tier_thresholds["weak_match"]:
        return "weak_match"
    else:
        return "mismatch"


def _build_blockers(
    manipulation_check: dict,
    skill_analysis: dict,
    constraint_analysis: dict,
) -> list[dict[str, Any]]:
    """Build list of blocking issues."""
    blockers = []

    # Add manipulation blocker if detected (this is serious)
    if manipulation_check.get("attempt_detected", False):
        blockers.append({
            "type": "manipulation_attempt",
            "description": "Resume contains text attempting to manipulate AI evaluation",
            "details": manipulation_check.get("details", ""),
        })

    # Add dealbreaker skill failures
    for skill_id in skill_analysis.get("dealbreaker_failures", []):
        blockers.append({
            "type": "dealbreaker_skill",
            "skill_id": skill_id,
            "reason": "Required skill not found in resume"
        })

    # Add dealbreaker constraint failures
    for fc in constraint_analysis.get("failed_constraints", []):
        if fc.get("type") == "dealbreaker":
            blockers.append({
                "type": "dealbreaker_constraint",
                "description": fc.get("description", ""),
                "evidence": fc.get("evidence", "")
            })

    return blockers


def _build_warnings(
    manipulation_detected: bool,
    source_summary: dict,
    reconciliation_result: dict,
    red_flag_summary: dict,
) -> list[dict[str, Any]]:
    """Build list of warnings."""
    warnings = []

    if manipulation_detected:
        warnings.append({
            "type": "manipulation_attempt",
            "severity": "critical",
            "message": "Resume contains prompt injection or manipulation attempt",
        })

    if source_summary.get("keyword_stuffing_flag"):
        warnings.append({
            "type": "keyword_stuffing",
            "severity": "medium",
            "message": (
                f"{source_summary['counts']['keyword_only']} of "
                f"{source_summary['total_skills_matched']} matched skills have no supporting evidence"
            ),
        })

    if reconciliation_result.get("added_count", 0) > 0:
        warnings.append({
            "type": "skill_reconciliation",
            "severity": "info",
            "message": (
                f"{reconciliation_result['added_count']} skills "
                "auto-reconciled from experience entries"
            ),
            "skills_added": reconciliation_result.get("skills_added", []),
        })

    if red_flag_summary["verification_confidence"] == "low":
        warnings.append({
            "type": "low_confidence",
            "severity": "medium",
            "message": f"Multiple red flags detected: {red_flag_summary['summary']}",
        })

    return warnings


def _build_dimensions(
    dimension_scores: dict[str, float],
    dimension_weights: dict[str, float],
    dimension_assessments: list[dict],
) -> dict[str, dict[str, Any]]:
    """Build combined dimensions object.

    Merges dimension scores, weights, and assessments into a single
    structure keyed by dimension name.
    """
    # Build lookup for assessments by dimension
    assessments_lookup: dict[str, dict] = {}
    for da in dimension_assessments:
        dim = da.get("dimension", "")
        assessments_lookup[dim] = da

    dimensions: dict[str, dict[str, Any]] = {}

    for dim in dimension_scores:
        assessment = assessments_lookup.get(dim, {})
        dimensions[dim] = {
            "score": dimension_scores.get(dim, 0),
            "weight": dimension_weights.get(dim, 0),
            "level": assessment.get("raw_level"),
            "label": assessment.get("dimension_label"),
            "reasoning": assessment.get("reasoning"),
            "positive_signals": assessment.get("positive_signals", []),
            "negative_signals": assessment.get("negative_signals", []),
        }

    return dimensions


def run_evaluation_pipeline(
    evaluation: dict,
    framework: dict,
    config: EvaluationConfig | None = None,
) -> dict[str, Any]:
    """Run complete evaluation post-processing pipeline.

    Pipeline steps:
    1. Normalize enums (PascalCase -> snake_case)
    2. Reconcile skill_matches with skills_demonstrated
    3. Check for manipulation attempts
    4. Calculate red flag summary
    5. Calculate experience summary
    6. Calculate source summary
    7. Calculate scores
    8. Enrich with human-readable names
    9. Apply manipulation penalty if detected
    10. Build blockers and warnings
    11. Sanitize for frontend

    Args:
        evaluation: Raw LLM evaluation output
        framework: Evaluation framework with weights
        config: Optional config overrides

    Returns:
        Complete evaluation result with scores, analysis, and original evaluation data
    """
    if config is None:
        config = DEFAULT_CONFIG

    # Extract framework components (needed early for reconciliation)
    skill_criteria = framework.get("skill_criteria", {})
    framework_skills = skill_criteria.get("skills", [])

    # Step 1: Normalize enums
    enum_result = normalize_evaluation_enums(evaluation)

    # Step 2: Reconcile skill_matches with skills_demonstrated
    reconciliation_result = reconcile_skill_matches(evaluation, framework_skills)

    # Step 3: Check for manipulation attempts
    manipulation_check = evaluation.get("manipulation_check", {})
    manipulation_detected = manipulation_check.get("attempt_detected", False)

    # Step 4: Calculate red flag summary
    red_flags = evaluation.get("red_flags", [])
    red_flag_summary = calculate_red_flag_summary(red_flags)

    # Step 5: Calculate experience summary
    experience_summary = calculate_experience_summary(
        evaluation.get("experience_entries", [])
    )

    # Step 6: Calculate source summary (after reconciliation)
    source_summary = calculate_source_summary(
        evaluation.get("skill_matches", [])
    )

    # Step 7: Calculate scores
    scoring = calculate_final_scores(evaluation, framework, config)

    # Step 8: Enrich evaluation with human-readable names
    enrich_evaluation(evaluation, framework, config)

    # Step 9: Apply manipulation penalty if detected
    final_score = scoring.final_score
    if manipulation_detected:
        final_score = round(final_score * config.manipulation_penalty, 1)

    # Build blockers list
    blockers = _build_blockers(manipulation_check, scoring.skill_analysis, scoring.constraint_analysis)
    can_proceed = len(blockers) == 0

    # Recalculate tier with manipulation penalty applied (keep tier clean, no suffix)
    tier = scoring.tier
    if manipulation_detected:
        tier = _determine_tier(final_score, config)

    # Build dimensions (combined scores, weights, assessments)
    dimension_weights = scoring.metadata.get("dimension_weights_used", {})
    dimensions = _build_dimensions(
        scoring.dimension_scores,
        dimension_weights,
        evaluation.get("dimension_assessments", []),
    )

    # Build complete result with grouped structure
    eval_summary = evaluation.get("summary", {})
    skill_analysis = scoring.skill_analysis

    result = {
        "scores": {
            "final_score": final_score,
            "tier": tier,
            "is_dealbreaker": scoring.is_dealbreaker,
            "is_flagged": manipulation_detected,
            "can_proceed": can_proceed,
            "verification_confidence": red_flag_summary["verification_confidence"],
        },
        "summary": {
            "strengths": eval_summary.get("strengths", []),
            "concerns": eval_summary.get("concerns", []),
            "interview_questions": eval_summary.get("interview_questions", []),
        },
        "dimensions": dimensions,
        "skills": {
            "summary": {
                "total": skill_analysis.get("total_skills", 0),
                "matched": skill_analysis.get("matched_count", 0),
                "coverage": skill_analysis.get("skill_coverage", 0),
                "source_breakdown": source_summary.get("counts", {}),
                "keyword_stuffing_flag": source_summary.get("keyword_stuffing_flag", False),
            },
            "matches": evaluation.get("skill_matches", []),
            "missing": skill_analysis.get("missing_skills", []),
        },
        "experience": {
            "summary": experience_summary,
            "entries": evaluation.get("experience_entries", []),
        },
        "constraints": {
            "summary": {
                "passed": scoring.constraint_analysis.get("passed_count", 0),
                "failed": len(scoring.constraint_analysis.get("failed_constraints", [])),
                "deferred": scoring.constraint_analysis.get("deferred_count", 0),
                "total": scoring.constraint_analysis.get("total_assessed", 0),
            },
            "results": evaluation.get("constraint_results", []),
        },
        "tradeoffs": {
            "summary": {
                "aligned": scoring.tradeoff_analysis.get("aligned_count", 0),
                "misaligned": scoring.tradeoff_analysis.get("misaligned_count", 0),
                "total": scoring.tradeoff_analysis.get("total_tradeoffs", 0),
            },
            "signals": evaluation.get("tradeoff_signals", []),
        },
        "red_flags": {
            "summary": red_flag_summary,
            "flags": red_flags,
        },
        "blockers": blockers,
        "manipulation_check": {
            "detected": manipulation_detected,
            "details": manipulation_check.get("details") if manipulation_detected else None,
        },
        "metadata": {
            **scoring.metadata,
            "enum_normalization": enum_result,
            "manipulation_penalty_applied": manipulation_detected,
            "skill_reconciliation": reconciliation_result,
        },
    }

    # Add warnings
    warnings = _build_warnings(
        manipulation_detected,
        source_summary,
        reconciliation_result,
        red_flag_summary,
    )
    if warnings:
        result["warnings"] = warnings

    # Final: Sanitize for frontend (removes internal fields)
    return sanitize_for_frontend(result)

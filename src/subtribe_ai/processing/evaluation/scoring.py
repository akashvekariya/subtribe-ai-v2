"""Scoring calculations for evaluation.

Calculates skill, constraint, tradeoff, and final scores.
"""

from typing import Any

from subtribe_ai.processing.evaluation.config import (
    DEFAULT_CONFIG,
    EvaluationConfig,
    ScoringResult,
)


def calculate_skill_score(
    skill_matches: list[dict],
    framework_skills: list[dict],
    category_weights: list[dict],
    config: EvaluationConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Calculate technical fit component from skill matches.

    Returns:
        - technical_fit_score: 0-10 score
        - skill_coverage: % of required skills found
        - category_scores: per-category breakdown
        - dealbreaker_failures: skills marked as dealbreaker but missing
        - matched_count: number of skills found
        - total_skills: total skills in framework
    """
    # Build lookup for matched skills by ID
    matched_lookup = {m["skill_id"]: m for m in skill_matches}

    # Build category weight lookup (normalized)
    cat_weight_lookup: dict[str, float] = {}
    total_cat_weight = sum(cw.get("weight", 0) for cw in category_weights)
    for cw in category_weights:
        cat = cw.get("category", "")
        weight = cw.get("weight", 0.1)
        cat_weight_lookup[cat] = weight / total_cat_weight if total_cat_weight > 0 else 0.1

    # Process each skill
    category_scores: dict[str, dict] = {}  # category -> {"weighted_sum": x, "weight_sum": y}
    required_count = 0
    required_found = 0
    dealbreaker_failures = []
    missing_skills = []

    for skill in framework_skills:
        skill_id = skill.get("skill_id", "")
        category = skill.get("category", "other")
        skill_weight = skill.get("effective_weight", skill.get("weight", 3)) / 5.0
        is_required = skill.get("is_required", False)
        is_dealbreaker = skill.get("is_dealbreaker", False)

        if is_required:
            required_count += 1

        # Initialize category if needed
        if category not in category_scores:
            category_scores[category] = {"weighted_sum": 0.0, "weight_sum": 0.0}

        if skill_id in matched_lookup:
            # Skill found - calculate score based on source_type
            match = matched_lookup[skill_id]
            source = match.get("source_type", "keyword_only")
            score_mult = config.source_scores.get(source, ("listed", 0.35))[1]

            if is_required:
                required_found += 1

            category_scores[category]["weighted_sum"] += score_mult * skill_weight
            category_scores[category]["weight_sum"] += skill_weight
        else:
            # Skill not found
            category_scores[category]["weight_sum"] += skill_weight
            # weighted_sum stays 0 for this skill

            if is_required:
                missing_skills.append({
                    "skill_id": skill_id,
                    "skill_name": skill.get("name", skill_id),
                    "category": category,
                    "is_dealbreaker": is_dealbreaker,
                })

            if is_dealbreaker:
                dealbreaker_failures.append(skill_id)

    # Calculate per-category scores (0-10 scale)
    cat_score_results: dict[str, float] = {}
    total_weighted_score = 0.0

    for category, data in category_scores.items():
        if data["weight_sum"] > 0:
            cat_score = (data["weighted_sum"] / data["weight_sum"]) * 10
        else:
            cat_score = 5.0  # Neutral if no skills

        cat_score_results[category] = round(cat_score, 2)

        # Apply category weight for final aggregation
        cat_weight = cat_weight_lookup.get(category, 0.1)
        total_weighted_score += cat_score * cat_weight

    # Skill coverage
    skill_coverage = required_found / required_count if required_count > 0 else 1.0

    return {
        "technical_fit_score": round(total_weighted_score, 2),
        "skill_coverage": round(skill_coverage, 2),
        "category_scores": cat_score_results,
        "dealbreaker_failures": dealbreaker_failures,
        "missing_skills": missing_skills,
        "matched_count": len(skill_matches),
        "total_skills": len(framework_skills),
    }


def calculate_constraint_penalty(
    constraint_results: list[dict],
    framework_constraints: list[dict],
    config: EvaluationConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Calculate penalty factor from constraint results.

    Returns:
        - penalty_factor: 0-1 multiplier (1 = no penalty)
        - has_dealbreaker_failure: bool
        - failed_constraints: list of failure details
        - passed_count: number of passed constraints
        - deferred_count: number of deferred constraints
    """
    penalty_factor = 1.0
    has_dealbreaker_failure = False
    failed_constraints = []
    passed_count = 0
    deferred_count = 0

    for result in constraint_results:
        idx = result.get("constraint_idx", -1)
        status = result.get("status", "pass")

        if status == "pass":
            passed_count += 1
            continue

        if status == "deferred":
            deferred_count += 1
            continue

        # status == "fail"
        if 0 <= idx < len(framework_constraints):
            constraint = framework_constraints[idx]
            constraint_type = constraint.get("constraint_type", "acceptable_gap")

            penalty = config.constraint_penalties.get(constraint_type, 0.95)
            penalty_factor *= penalty

            if constraint_type == "dealbreaker":
                has_dealbreaker_failure = True

            failed_constraints.append({
                "idx": idx,
                "type": constraint_type,
                "description": constraint.get("description", ""),
                "evidence": result.get("evidence", ""),
                "severity": constraint.get("severity", "important"),
            })

    return {
        "penalty_factor": round(penalty_factor, 3),
        "has_dealbreaker_failure": has_dealbreaker_failure,
        "failed_constraints": failed_constraints,
        "passed_count": passed_count,
        "deferred_count": deferred_count,
        "total_assessed": len(constraint_results),
    }


def calculate_tradeoff_alignment(
    tradeoff_signals: list[dict],
    framework_tradeoffs: list[dict],
    config: EvaluationConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Calculate alignment score from tradeoff signals.

    Returns:
        - alignment_score: 0-10 score
        - alignments: per-tradeoff alignment details
        - aligned_count: number of aligned tradeoffs
        - misaligned_count: number of misaligned tradeoffs
    """
    # Build lookup for framework tradeoffs
    tradeoff_lookup = {t.get("tradeoff_id", ""): t for t in framework_tradeoffs}

    total_importance = 0.0
    weighted_alignment = 0.0
    alignments = []
    aligned_count = 0
    misaligned_count = 0

    for signal in tradeoff_signals:
        tradeoff_id = signal.get("tradeoff_id", "")
        candidate_dir = signal.get("direction", "unclear")

        if tradeoff_id not in tradeoff_lookup:
            continue

        framework_pref = tradeoff_lookup[tradeoff_id]
        recruiter_dir = framework_pref.get("preferred_direction", "balanced")
        importance = framework_pref.get("alignment_importance", "medium")
        imp_weight = config.importance_weights.get(importance, 0.5)

        # Calculate alignment score
        if candidate_dir == "unclear":
            alignment = 0.5  # Neutral
        elif candidate_dir == recruiter_dir:
            alignment = 1.0  # Full alignment
            aligned_count += 1
        elif candidate_dir == "balanced" or recruiter_dir == "balanced":
            alignment = 0.7  # Partial alignment
        else:
            alignment = 0.2  # Misalignment
            misaligned_count += 1

        total_importance += imp_weight
        weighted_alignment += alignment * imp_weight

        alignments.append({
            "tradeoff_id": tradeoff_id,
            "candidate_direction": candidate_dir,
            "recruiter_direction": recruiter_dir,
            "aligned": candidate_dir == recruiter_dir,
            "alignment_score": round(alignment, 2),
        })

    alignment_score = (
        (weighted_alignment / total_importance) * 10
        if total_importance > 0
        else 5.0  # Neutral if no tradeoffs
    )

    return {
        "alignment_score": round(alignment_score, 2),
        "alignments": alignments,
        "aligned_count": aligned_count,
        "misaligned_count": misaligned_count,
        "total_tradeoffs": len(tradeoff_signals),
    }


def calculate_final_scores(
    evaluation: dict,
    framework: dict,
    config: EvaluationConfig = DEFAULT_CONFIG,
) -> ScoringResult:
    """Calculate all scores from LLM evaluation output.

    Args:
        evaluation: LLM evaluation output (CandidateEvaluation)
        framework: Evaluation framework with weights
        config: Scoring configuration

    Returns:
        ScoringResult with dimension scores, final score, tier, and analysis details
    """
    # Extract framework components
    skill_criteria = framework.get("skill_criteria", {})
    framework_skills = skill_criteria.get("skills", [])
    category_weights = skill_criteria.get("category_weights", [])
    framework_constraints = framework.get("hard_constraints", [])
    framework_tradeoffs = framework.get("tradeoff_preferences", [])

    # Build dimension weight lookup
    dimension_weights: dict[str, float] = {}
    for dw in framework.get("dimension_weights", []):
        dim = dw.get("dimension", "")
        dimension_weights[dim] = dw.get("weight", 0.2)

    # Normalize dimension weights if needed
    total_dim_weight = sum(dimension_weights.values())
    if total_dim_weight > 0 and abs(total_dim_weight - 1.0) > 0.01:
        for dim in dimension_weights:
            dimension_weights[dim] /= total_dim_weight

    # Calculate component scores
    skill_analysis = calculate_skill_score(
        evaluation.get("skill_matches", []),
        framework_skills,
        category_weights,
        config,
    )

    constraint_analysis = calculate_constraint_penalty(
        evaluation.get("constraint_results", []),
        framework_constraints,
        config,
    )

    tradeoff_analysis = calculate_tradeoff_alignment(
        evaluation.get("tradeoff_signals", []),
        framework_tradeoffs,
        config,
    )

    # Get LLM dimension assessments
    dimension_assessments: dict[str, dict] = {}
    for da in evaluation.get("dimension_assessments", []):
        dim = da.get("dimension", "")
        dimension_assessments[dim] = da

    # Calculate dimension scores (blend LLM assessment with calculated components)
    dimension_scores: dict[str, float] = {}
    required_dims = [
        "technical_fit",
        "experience_fit",
        "trajectory_fit",
        "culture_fit",
        "problem_solving_fit",
    ]

    for dim in required_dims:
        if dim in dimension_assessments:
            raw_level = dimension_assessments[dim].get("raw_level", "moderate")
            base_score = config.level_scores.get(raw_level, 5.5)

            # Blend with calculated components for relevant dimensions
            if dim == "technical_fit":
                # 60% LLM assessment, 40% calculated skill score
                blended = (base_score * 0.6) + (skill_analysis["technical_fit_score"] * 0.4)
                dimension_scores[dim] = round(blended, 1)
            elif dim == "culture_fit":
                # 70% LLM assessment, 30% tradeoff alignment
                blended = (base_score * 0.7) + (tradeoff_analysis["alignment_score"] * 0.3)
                dimension_scores[dim] = round(blended, 1)
            else:
                dimension_scores[dim] = round(base_score, 1)
        else:
            # Dimension not assessed by LLM - use neutral
            dimension_scores[dim] = 5.0

    # Calculate weighted final score
    weighted_score = 0.0
    for dim, score in dimension_scores.items():
        weight = dimension_weights.get(dim, 0.2)
        weighted_score += score * weight

    # Apply constraint penalty
    final_score = weighted_score * constraint_analysis["penalty_factor"]
    final_score = round(final_score, 1)

    # Determine tier based on score
    if final_score >= config.tier_thresholds["strong_match"]:
        tier = "strong_match"
    elif final_score >= config.tier_thresholds["good_match"]:
        tier = "good_match"
    elif final_score >= config.tier_thresholds["moderate_match"]:
        tier = "moderate_match"
    elif final_score >= config.tier_thresholds["weak_match"]:
        tier = "weak_match"
    else:
        tier = "mismatch"

    # Check if dealbreaker requirement failed (separate from tier)
    is_dealbreaker = bool(
        constraint_analysis["has_dealbreaker_failure"]
        or skill_analysis.get("dealbreaker_failures")
    )

    return ScoringResult(
        dimension_scores=dimension_scores,
        final_score=final_score,
        tier=tier,
        is_dealbreaker=is_dealbreaker,
        skill_analysis=skill_analysis,
        constraint_analysis=constraint_analysis,
        tradeoff_analysis=tradeoff_analysis,
        metadata={
            "dimension_weights_used": dimension_weights,
            "penalty_applied": constraint_analysis["penalty_factor"],
        },
    )

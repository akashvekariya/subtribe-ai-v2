"""
Evaluation Post-Processing Pipeline

Calculates final scores from LLM evaluation output by applying framework weights.
This is SEPARATE from framework_post_processing.py.

Pipeline:
1. Calculate skill coverage and technical fit component
2. Calculate constraint penalty factor
3. Calculate tradeoff alignment score
4. Blend LLM dimension assessments with calculated components
5. Apply framework dimension weights for final score
6. Determine candidate tier
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class EvaluationConfig:
    """Configurable scoring parameters."""
    # Depth score mappings (skill depth -> score multiplier)
    depth_scores: dict = field(default_factory=lambda: {
        "strong": 1.0,
        "moderate": 0.7,
        "basic": 0.4,
        "unclear": 0.2,
    })

    # Evidence quality modifiers (applied to depth score)
    # keyword_only gets 30% reduction - still gets credit but less than evidenced skills
    evidence_modifiers: dict = field(default_factory=lambda: {
        "strong_evidence": 1.0,
        "weak_evidence": 0.85,
        "keyword_only": 0.7,
    })

    # Dimension level to numeric score mapping
    level_scores: dict = field(default_factory=lambda: {
        "strong": 9.5,
        "good": 7.5,
        "moderate": 5.5,
        "weak": 3.5,
        "poor": 1.5,
    })

    # Constraint type penalties on failure
    # Note: Dealbreaker no longer zeros score - we flag separately
    constraint_penalties: dict = field(default_factory=lambda: {
        "dealbreaker": 0.7,      # 30% penalty but preserves score signal
        "required_day1": 0.85,   # 15% penalty
        "acceptable_gap": 0.95,  # 5% penalty
    })

    # Manipulation attempt penalty
    manipulation_penalty: float = 0.7  # 30% reduction if manipulation detected

    # Tradeoff alignment importance weights
    importance_weights: dict = field(default_factory=lambda: {
        "high": 1.0,
        "medium": 0.6,
        "low": 0.3,
    })

    # Tier thresholds (score ranges)
    tier_thresholds: dict = field(default_factory=lambda: {
        "strong_match": 8.5,
        "good_match": 7.0,
        "moderate_match": 5.5,
        "weak_match": 4.0,
    })


DEFAULT_CONFIG = EvaluationConfig()


@dataclass
class ScoringResult:
    """Final scoring result."""
    dimension_scores: dict
    final_score: float
    tier: str
    skill_analysis: dict
    constraint_analysis: dict
    tradeoff_analysis: dict
    metadata: dict = field(default_factory=dict)


def calculate_experience_summary(experience_entries: list[dict]) -> dict:
    """
    Calculate total experience from extracted entries.
    LLM extracts each role separately, we sum here to avoid hallucination.

    Returns:
        - total_months: Sum of all experience durations
        - total_years: Rounded years
        - by_type: Breakdown by experience type
        - entries_count: Number of entries
        - has_current_role: Whether candidate is currently employed
    """
    total_months = 0
    by_type = {}
    has_current_role = False

    for entry in experience_entries:
        duration = entry.get("duration_months", 0)
        exp_type = entry.get("experience_type", "other")

        total_months += duration

        if exp_type not in by_type:
            by_type[exp_type] = {"count": 0, "months": 0}
        by_type[exp_type]["count"] += 1
        by_type[exp_type]["months"] += duration

        if entry.get("is_current", False):
            has_current_role = True

    return {
        "total_months": total_months,
        "total_years": round(total_months / 12, 1),
        "by_type": by_type,
        "entries_count": len(experience_entries),
        "has_current_role": has_current_role,
    }


def infer_depth_from_entry(entry: dict) -> str:
    """
    Infer skill depth from experience entry context.
    Uses title seniority and duration as heuristics.
    Works for any industry - no NLP required.
    """
    title_lower = entry.get("title", "").lower()
    duration = entry.get("duration_months", 0)

    # Check title for seniority indicators
    senior_indicators = ["senior", "lead", "principal", "head", "director", "manager", "chief", "vp", "architect"]
    junior_indicators = ["intern", "trainee", "junior", "associate", "assistant", "entry"]

    is_senior = any(indicator in title_lower for indicator in senior_indicators)
    is_junior = any(indicator in title_lower for indicator in junior_indicators)

    if is_senior or duration >= 24:
        return "strong"
    elif is_junior:
        return "basic"
    elif duration >= 12:
        return "moderate"
    elif duration >= 6:
        return "moderate"
    else:
        return "basic"


def reconcile_skill_matches(
    evaluation: dict,
    framework_skills: list[dict],
) -> dict:
    """
    Reconcile skills_demonstrated with skill_matches to catch LLM inconsistencies.

    The LLM sometimes identifies skills in experience entries (skills_demonstrated)
    but fails to create corresponding skill_match entries with detailed evidence.
    This function catches those gaps and creates basic entries.

    Args:
        evaluation: LLM evaluation output (will be modified in place)
        framework_skills: List of skills from framework to validate skill_ids

    Returns:
        Reconciliation stats: {added_count, skills_added, total_demonstrated, total_matched}
    """
    # Build set of valid skill_ids from framework
    valid_skill_ids = {s.get("skill_id", "") for s in framework_skills}

    # Collect all skills from skills_demonstrated across all experience entries
    demonstrated_skills = {}  # skill_id -> best experience entry
    for entry in evaluation.get("experience_entries", []):
        for skill_id in entry.get("skills_demonstrated", []):
            if skill_id not in valid_skill_ids:
                continue  # Skip invalid skill_ids

            # Keep the entry with longest duration or highest seniority
            if skill_id not in demonstrated_skills:
                demonstrated_skills[skill_id] = entry
            else:
                existing_entry = demonstrated_skills[skill_id]
                # Prefer longer duration or senior titles
                if entry.get("duration_months", 0) > existing_entry.get("duration_months", 0):
                    demonstrated_skills[skill_id] = entry

    # Get existing skill_matches
    existing_matches = {m.get("skill_id", "") for m in evaluation.get("skill_matches", [])}

    # Find skills that are demonstrated but not in skill_matches
    missing_skills = set(demonstrated_skills.keys()) - existing_matches

    # Create basic skill_match entries for missing skills
    added_entries = []
    for skill_id in missing_skills:
        entry = demonstrated_skills[skill_id]
        depth = infer_depth_from_entry(entry)

        # Build evidence from experience entry
        contributions = entry.get("key_contributions", [])
        contribution_text = "; ".join(contributions[:2]) if contributions else "See experience entry"

        new_match = {
            "skill_id": skill_id,
            "source_reference": entry.get("company", "Unknown"),
            "evidence": f"WHERE: {entry.get('company', 'N/A')}. WHAT: {contribution_text}. [Auto-reconciled from skills_demonstrated]",
            "evidence_quality": "weak_evidence",  # Conservative default
            "depth": depth,
            "_reconciled": True,  # Internal flag for debugging
        }
        added_entries.append(new_match)

    # Add to evaluation's skill_matches
    if "skill_matches" not in evaluation:
        evaluation["skill_matches"] = []
    evaluation["skill_matches"].extend(added_entries)

    return {
        "added_count": len(added_entries),
        "skills_added": list(missing_skills),
        "total_demonstrated": len(demonstrated_skills),
        "total_matched_after": len(evaluation["skill_matches"]),
    }


def calculate_evidence_quality_summary(skill_matches: list[dict]) -> dict:
    """
    Summarize evidence quality across all skill matches.
    Used to flag potential keyword stuffing.
    """
    quality_counts = {"strong_evidence": 0, "weak_evidence": 0, "keyword_only": 0}

    for match in skill_matches:
        quality = match.get("evidence_quality", "weak_evidence")
        if quality in quality_counts:
            quality_counts[quality] += 1

    total = len(skill_matches)
    keyword_only_ratio = quality_counts["keyword_only"] / total if total > 0 else 0

    return {
        "counts": quality_counts,
        "total_skills_matched": total,
        "keyword_only_ratio": round(keyword_only_ratio, 2),
        "keyword_stuffing_flag": keyword_only_ratio > 0.5 and total >= 3,
    }


def calculate_red_flag_summary(red_flags: list[dict]) -> dict:
    """
    Summarize red flags and calculate verification confidence.

    Confidence levels:
    - high: No red flags or only 'info' severity
    - medium: 1-2 'investigate' flags
    - low: 3+ 'investigate' flags OR any 'concern' flags
    """
    if not red_flags:
        return {
            "total_flags": 0,
            "by_severity": {"info": 0, "investigate": 0, "concern": 0},
            "by_type": {},
            "verification_confidence": "high",
            "summary": "No red flags detected",
        }

    by_severity = {"info": 0, "investigate": 0, "concern": 0}
    by_type = {}

    for flag in red_flags:
        severity = flag.get("severity", "investigate")
        flag_type = flag.get("flag_type", "unknown")

        if severity in by_severity:
            by_severity[severity] += 1

        if flag_type not in by_type:
            by_type[flag_type] = 0
        by_type[flag_type] += 1

    # Determine confidence level
    if by_severity["concern"] > 0:
        confidence = "low"
    elif by_severity["investigate"] >= 3:
        confidence = "low"
    elif by_severity["investigate"] > 0:
        confidence = "medium"
    else:
        confidence = "high"

    # Generate summary
    parts = []
    if by_severity["concern"] > 0:
        parts.append(f"{by_severity['concern']} concern(s)")
    if by_severity["investigate"] > 0:
        parts.append(f"{by_severity['investigate']} to investigate")
    if by_severity["info"] > 0:
        parts.append(f"{by_severity['info']} info note(s)")
    summary = ", ".join(parts) if parts else "No actionable flags"

    return {
        "total_flags": len(red_flags),
        "by_severity": by_severity,
        "by_type": by_type,
        "verification_confidence": confidence,
        "summary": summary,
    }


def calculate_skill_score(
    skill_matches: list[dict],
    framework_skills: list[dict],
    category_weights: list[dict],
    config: EvaluationConfig = DEFAULT_CONFIG,
) -> dict:
    """
    Calculate technical fit component from skill matches.

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
    cat_weight_lookup = {}
    total_cat_weight = sum(cw.get("weight", 0) for cw in category_weights)
    for cw in category_weights:
        cat = cw.get("category", "")
        weight = cw.get("weight", 0.1)
        cat_weight_lookup[cat] = weight / total_cat_weight if total_cat_weight > 0 else 0.1

    # Process each skill
    category_scores = {}  # category -> {"weighted_sum": x, "weight_sum": y}
    required_count = 0
    required_found = 0
    dealbreaker_failures = []

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
            category_scores[category] = {"weighted_sum": 0, "weight_sum": 0}

        if skill_id in matched_lookup:
            # Skill found - calculate score based on depth and evidence quality
            match = matched_lookup[skill_id]
            depth = match.get("depth", "unclear")
            depth_score = config.depth_scores.get(depth, 0.5)

            # Apply evidence quality modifier
            # keyword_only skills get reduced credit even if depth seems high
            evidence_quality = match.get("evidence_quality", "weak_evidence")
            evidence_modifier = config.evidence_modifiers.get(evidence_quality, 0.85)
            effective_depth_score = depth_score * evidence_modifier

            if is_required:
                required_found += 1

            category_scores[category]["weighted_sum"] += effective_depth_score * skill_weight
            category_scores[category]["weight_sum"] += skill_weight
        else:
            # Skill not found
            category_scores[category]["weight_sum"] += skill_weight
            # weighted_sum stays 0 for this skill

            if is_dealbreaker:
                dealbreaker_failures.append(skill_id)

    # Calculate per-category scores (0-10 scale)
    cat_score_results = {}
    total_weighted_score = 0

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
        "matched_count": len(skill_matches),
        "total_skills": len(framework_skills),
    }


def calculate_constraint_penalty(
    constraint_results: list[dict],
    framework_constraints: list[dict],
    config: EvaluationConfig = DEFAULT_CONFIG,
) -> dict:
    """
    Calculate penalty factor from constraint results.

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
) -> dict:
    """
    Calculate alignment score from tradeoff signals.

    Returns:
        - alignment_score: 0-10 score
        - alignments: per-tradeoff alignment details
        - aligned_count: number of aligned tradeoffs
        - misaligned_count: number of misaligned tradeoffs
    """
    # Build lookup for framework tradeoffs
    tradeoff_lookup = {t.get("tradeoff_id", ""): t for t in framework_tradeoffs}

    total_importance = 0
    weighted_alignment = 0
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

    if total_importance > 0:
        alignment_score = (weighted_alignment / total_importance) * 10
    else:
        alignment_score = 5.0  # Neutral if no tradeoffs

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
    """
    Main function: Calculate all scores from LLM evaluation output.

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
    dimension_weights = {}
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
    dimension_assessments = {}
    for da in evaluation.get("dimension_assessments", []):
        dim = da.get("dimension", "")
        dimension_assessments[dim] = da

    # Calculate dimension scores (blend LLM assessment with calculated components)
    dimension_scores = {}
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
    weighted_score = 0
    for dim, score in dimension_scores.items():
        weight = dimension_weights.get(dim, 0.2)
        weighted_score += score * weight

    # Apply constraint penalty
    final_score = weighted_score * constraint_analysis["penalty_factor"]
    final_score = round(final_score, 1)

    # Determine tier based on score (dealbreaker handled separately via blockers)
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

    # Append _blocked suffix if dealbreaker failed (preserves score tier info)
    if constraint_analysis["has_dealbreaker_failure"] or skill_analysis.get("dealbreaker_failures"):
        tier = f"{tier}_blocked"

    return ScoringResult(
        dimension_scores=dimension_scores,
        final_score=final_score,
        tier=tier,
        skill_analysis=skill_analysis,
        constraint_analysis=constraint_analysis,
        tradeoff_analysis=tradeoff_analysis,
        metadata={
            "dimension_weights_used": dimension_weights,
            "penalty_applied": constraint_analysis["penalty_factor"],
        },
    )


def normalize_evaluation_enums(evaluation: dict) -> dict:
    """
    Normalize enum values in evaluation output (PascalCase -> snake_case).
    Similar to framework enum normalization.
    """
    enum_map = {
        # SkillDepth
        "Strong": "strong",
        "Moderate": "moderate",
        "Basic": "basic",
        "Unclear": "unclear",
        # EvidenceQuality
        "StrongEvidence": "strong_evidence",
        "WeakEvidence": "weak_evidence",
        "KeywordOnly": "keyword_only",
        # ConstraintStatus
        "Pass": "pass",
        "Fail": "fail",
        "Deferred": "deferred",
        # CandidateDirection
        "OptionA": "option_a",
        "OptionB": "option_b",
        "Balanced": "balanced",
        # DimensionLevel
        "Good": "good",
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

    normalized_count = 0

    # Normalize skill_matches
    for match in evaluation.get("skill_matches", []):
        depth = match.get("depth", "")
        if depth in enum_map:
            match["depth"] = enum_map[depth]
            normalized_count += 1
        evidence_quality = match.get("evidence_quality", "")
        if evidence_quality in enum_map:
            match["evidence_quality"] = enum_map[evidence_quality]
            normalized_count += 1

    # Normalize constraint_results
    for result in evaluation.get("constraint_results", []):
        status = result.get("status", "")
        if status in enum_map:
            result["status"] = enum_map[status]
            normalized_count += 1

    # Normalize tradeoff_signals
    for signal in evaluation.get("tradeoff_signals", []):
        direction = signal.get("direction", "")
        if direction in enum_map:
            signal["direction"] = enum_map[direction]
            normalized_count += 1

    # Normalize dimension_assessments
    for assessment in evaluation.get("dimension_assessments", []):
        level = assessment.get("raw_level", "")
        if level in enum_map:
            assessment["raw_level"] = enum_map[level]
            normalized_count += 1

    # Normalize red_flags
    for flag in evaluation.get("red_flags", []):
        flag_type = flag.get("flag_type", "")
        if flag_type in enum_map:
            flag["flag_type"] = enum_map[flag_type]
            normalized_count += 1
        severity = flag.get("severity", "")
        if severity in enum_map:
            flag["severity"] = enum_map[severity]
            normalized_count += 1

    return {"normalized_count": normalized_count}


def run_evaluation_pipeline(
    evaluation: dict,
    framework: dict,
    config: EvaluationConfig | None = None,
) -> dict:
    """
    Main entry point: Run complete evaluation post-processing pipeline.

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
    # This catches when LLM identifies skills in experience entries but forgets
    # to create corresponding skill_match entries
    reconciliation_result = reconcile_skill_matches(evaluation, framework_skills)

    # Step 3: Check for manipulation attempts (CRITICAL)
    manipulation_check = evaluation.get("manipulation_check", {})
    manipulation_detected = manipulation_check.get("attempt_detected", False)

    # Step 4: Calculate red flag summary
    red_flags = evaluation.get("red_flags", [])
    red_flag_summary = calculate_red_flag_summary(red_flags)

    # Step 5: Calculate experience summary (from per-row extraction)
    experience_summary = calculate_experience_summary(
        evaluation.get("experience_entries", [])
    )

    # Step 6: Calculate evidence quality summary (after reconciliation)
    evidence_quality_summary = calculate_evidence_quality_summary(
        evaluation.get("skill_matches", [])
    )

    # Step 7: Calculate scores (skill_matches now includes reconciled entries)
    scoring = calculate_final_scores(evaluation, framework, config)

    # Step 8: Apply manipulation penalty if detected
    final_score = scoring.final_score
    if manipulation_detected:
        final_score = round(final_score * config.manipulation_penalty, 1)

    # Build blockers list
    blockers = []

    # Add manipulation blocker if detected (this is serious)
    if manipulation_detected:
        blockers.append({
            "type": "manipulation_attempt",
            "description": "Resume contains text attempting to manipulate AI evaluation",
            "details": manipulation_check.get("details", ""),
        })

    # Add dealbreaker skill failures
    for skill_id in scoring.skill_analysis.get("dealbreaker_failures", []):
        blockers.append({
            "type": "dealbreaker_skill",
            "skill_id": skill_id,
            "reason": "Required skill not found in resume"
        })

    # Add dealbreaker constraint failures
    for fc in scoring.constraint_analysis.get("failed_constraints", []):
        if fc.get("type") == "dealbreaker":
            blockers.append({
                "type": "dealbreaker_constraint",
                "description": fc.get("description", ""),
                "evidence": fc.get("evidence", "")
            })

    can_proceed = len(blockers) == 0

    # Recalculate tier with manipulation penalty applied
    tier = scoring.tier
    if manipulation_detected:
        # Recalculate tier based on penalized score
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
        tier = f"{tier}_flagged"  # Special suffix for manipulation

    # Build complete result
    result = {
        "scores": {
            "final_score": final_score,
            "tier": tier,
            "dimension_scores": scoring.dimension_scores,
            "verification_confidence": red_flag_summary["verification_confidence"],
        },
        "manipulation_check": {
            "detected": manipulation_detected,
            "details": manipulation_check.get("details") if manipulation_detected else None,
        },
        "red_flags": {
            "flags": red_flags,
            "summary": red_flag_summary,
        },
        "blockers": blockers,
        "can_proceed": can_proceed,
        "analysis": {
            "skill_analysis": scoring.skill_analysis,
            "constraint_analysis": scoring.constraint_analysis,
            "tradeoff_analysis": scoring.tradeoff_analysis,
            "experience_summary": experience_summary,
            "evidence_quality": evidence_quality_summary,
        },
        "evaluation": {
            "experience_entries": evaluation.get("experience_entries", []),
            "skill_matches": evaluation.get("skill_matches", []),
            "constraint_results": evaluation.get("constraint_results", []),
            "tradeoff_signals": evaluation.get("tradeoff_signals", []),
            "dimension_assessments": evaluation.get("dimension_assessments", []),
            "summary": evaluation.get("summary", {}),
        },
        "metadata": {
            **scoring.metadata,
            "enum_normalization": enum_result,
            "manipulation_penalty_applied": manipulation_detected,
            "skill_reconciliation": reconciliation_result,
        },
    }

    # Add warnings
    warnings = []

    if manipulation_detected:
        warnings.append({
            "type": "manipulation_attempt",
            "severity": "critical",
            "message": "Resume contains prompt injection or manipulation attempt",
        })

    if evidence_quality_summary.get("keyword_stuffing_flag"):
        warnings.append({
            "type": "keyword_stuffing",
            "severity": "medium",
            "message": f"{evidence_quality_summary['counts']['keyword_only']} of {evidence_quality_summary['total_skills_matched']} matched skills have no supporting evidence",
        })

    if reconciliation_result.get("added_count", 0) > 0:
        warnings.append({
            "type": "skill_reconciliation",
            "severity": "info",
            "message": f"{reconciliation_result['added_count']} skills auto-reconciled from experience entries",
            "skills_added": reconciliation_result.get("skills_added", []),
        })

    if red_flag_summary["verification_confidence"] == "low":
        warnings.append({
            "type": "low_confidence",
            "severity": "medium",
            "message": f"Multiple red flags detected: {red_flag_summary['summary']}",
        })

    if warnings:
        result["warnings"] = warnings

    return result

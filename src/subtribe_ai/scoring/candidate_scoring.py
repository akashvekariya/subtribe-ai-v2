"""
Candidate Scoring Algorithm

A comprehensive, hierarchical scoring system for evaluating candidates against
job evaluation frameworks. All computations are data-driven with no hardcoded
role-specific logic.

Scoring Hierarchy:
    Level 1: Individual Skill Matching (0-10 per skill)
    Level 2: Category Aggregation (weighted by category_weights)
    Level 3: Dimension Aggregation (weighted by dimension_weights)
    Level 4: Final Composite Score (0-10 with granularity to 0.01)

Specialist vs Generalist Handling:
    The algorithm computes three complementary metrics:
    1. Weighted Score: Favors specialists who excel at critical skills
    2. Coverage Score: Favors generalists with broad competence
    3. Top-K Critical Score: Measures excellence on most important skills

    These are combined based on the role's emphasis (derived from calibration).

Constraint Gating:
    - Dealbreakers cap the maximum achievable score
    - Required-day-1 gaps reduce the score ceiling
    - Acceptable gaps have minimal impact

All weights, thresholds, and formulas are configurable via ScoringConfig.
"""

from dataclasses import dataclass, field
from typing import Any
import math


@dataclass
class ScoringConfig:
    """
    Configurable parameters for the scoring algorithm.
    All values are adjustable - no magic numbers in the code.
    """
    # Skill matching thresholds
    exact_match_score: float = 10.0  # Score for exact skill match
    strong_match_score: float = 8.0  # Score for strong/related match
    partial_match_score: float = 5.0  # Score for partial match
    weak_match_score: float = 2.0  # Score for weak/tangential match
    no_match_score: float = 0.0  # Score for no match

    # Constraint impact on score ceiling
    dealbreaker_ceiling: float = 3.0  # Max score if dealbreaker triggered
    required_day1_penalty: float = 2.0  # Score reduction per missing requirement
    acceptable_gap_penalty: float = 0.5  # Score reduction per acceptable gap

    # Specialist vs Generalist weighting
    # These weights determine how much each metric contributes to skill dimension
    weighted_score_emphasis: float = 0.5  # Weight for depth (specialist)
    coverage_score_emphasis: float = 0.3  # Weight for breadth (generalist)
    topk_score_emphasis: float = 0.2  # Weight for critical skill excellence

    # Coverage calculation
    coverage_threshold: float = 5.0  # Minimum score to count as "covered"

    # Top-K calculation
    top_k_count: int = 5  # Number of top skills to consider for top-k score

    # Score precision
    score_precision: int = 2  # Decimal places for final scores (e.g., 9.12)

    # Minimum weights to prevent division issues
    min_weight_sum: float = 0.001


@dataclass
class SkillScore:
    """Score for an individual skill."""
    skill_id: str
    skill_name: str
    category: str
    raw_score: float  # 0-10 match quality
    weight: float  # From framework (1-5)
    effective_weight: float  # weight * selection_multiplier
    weighted_score: float  # raw_score * effective_weight
    is_required: bool
    is_dealbreaker: bool
    match_type: str  # exact, strong, partial, weak, none
    match_evidence: str  # What in the resume matched


@dataclass
class CategoryScore:
    """Aggregated score for a skill category."""
    category: str
    category_weight: float
    skill_scores: list[SkillScore]
    raw_average: float  # Simple average of skill scores
    weighted_average: float  # Weight-adjusted average
    coverage_ratio: float  # Fraction of skills above threshold
    weighted_contribution: float  # weighted_average * category_weight


@dataclass
class DimensionScore:
    """Aggregated score for an evaluation dimension."""
    dimension: str
    dimension_weight: float
    description: str
    raw_score: float  # Dimension-specific calculation
    weighted_contribution: float  # raw_score * dimension_weight
    contributing_factors: list[str]  # What fed into this score


@dataclass
class ConstraintResult:
    """Result of constraint evaluation."""
    constraint_type: str  # dealbreaker, required_day1, acceptable_gap
    original_text: str
    is_violated: bool
    severity: str
    evidence: str  # What in resume indicates violation/compliance
    score_impact: float  # How much this affects the ceiling


@dataclass
class CandidateScore:
    """Complete scoring result for a candidate."""
    # Identification
    candidate_id: str
    job_id: str

    # Hierarchical scores
    skill_scores: list[SkillScore]
    category_scores: list[CategoryScore]
    dimension_scores: list[DimensionScore]

    # Constraint evaluation
    constraint_results: list[ConstraintResult]
    constraint_ceiling: float  # Maximum achievable score after constraints

    # Aggregate metrics
    weighted_skill_score: float  # Specialist metric
    coverage_score: float  # Generalist metric
    topk_critical_score: float  # Critical skill excellence

    # Final scores
    raw_composite_score: float  # Before constraint capping
    final_score: float  # After constraint capping (0-10)
    percentile_rank: float  # Relative ranking (computed separately)

    # Metadata
    scoring_breakdown: dict  # Detailed breakdown for transparency
    match_summary: str  # Human-readable summary


# Default config instance
DEFAULT_SCORING_CONFIG = ScoringConfig()


def calculate_skill_score(
    skill: dict,
    candidate_skills: list[str],
    config: ScoringConfig
) -> SkillScore:
    """
    Calculate match score for a single skill.

    Args:
        skill: Skill from framework with weight, effective_weight, etc.
        candidate_skills: List of skills from candidate's resume
        config: Scoring configuration

    Returns:
        SkillScore with match details
    """
    skill_id = skill.get("skill_id", "")
    skill_name = skill.get("name", "").lower()
    category = skill.get("category", "")
    weight = skill.get("weight", 3)
    effective_weight = skill.get("effective_weight", weight)
    is_required = skill.get("is_required", False)
    is_dealbreaker = skill.get("is_dealbreaker", False)

    # Normalize candidate skills for matching
    candidate_skills_lower = [s.lower().strip() for s in candidate_skills]

    # Find best match
    match_type = "none"
    match_evidence = ""
    raw_score = config.no_match_score

    for cs in candidate_skills_lower:
        # Exact match
        if skill_name == cs:
            match_type = "exact"
            match_evidence = cs
            raw_score = config.exact_match_score
            break

        # Strong match (contains or is contained)
        if skill_name in cs or cs in skill_name:
            if match_type not in ["exact"]:
                match_type = "strong"
                match_evidence = cs
                raw_score = config.strong_match_score

        # Partial match (shared significant words)
        skill_words = set(skill_name.split())
        cs_words = set(cs.split())
        common_words = skill_words & cs_words
        # Filter out common stopwords
        significant_common = {w for w in common_words if len(w) > 2}
        if significant_common and match_type not in ["exact", "strong"]:
            match_type = "partial"
            match_evidence = cs
            raw_score = config.partial_match_score

    weighted_score = raw_score * effective_weight

    return SkillScore(
        skill_id=skill_id,
        skill_name=skill.get("name", ""),
        category=category,
        raw_score=round(raw_score, config.score_precision),
        weight=weight,
        effective_weight=effective_weight,
        weighted_score=round(weighted_score, config.score_precision),
        is_required=is_required,
        is_dealbreaker=is_dealbreaker,
        match_type=match_type,
        match_evidence=match_evidence
    )


def aggregate_category_scores(
    skill_scores: list[SkillScore],
    category_weights: list[dict],
    config: ScoringConfig
) -> list[CategoryScore]:
    """
    Aggregate skill scores into category scores.

    Args:
        skill_scores: List of individual skill scores
        category_weights: Category weight definitions from framework
        config: Scoring configuration

    Returns:
        List of CategoryScore, one per category
    """
    # Build category weight lookup
    cat_weight_lookup = {}
    for cw in category_weights:
        cat = cw.get("category", "")
        cat_weight_lookup[cat] = cw.get("weight", 0.2)

    # Group skills by category
    category_skills: dict[str, list[SkillScore]] = {}
    for ss in skill_scores:
        cat = ss.category
        if cat not in category_skills:
            category_skills[cat] = []
        category_skills[cat].append(ss)

    # Calculate category scores
    category_scores = []
    for cat, skills in category_skills.items():
        if not skills:
            continue

        cat_weight = cat_weight_lookup.get(cat, 0.2)

        # Raw average (unweighted)
        raw_sum = sum(s.raw_score for s in skills)
        raw_average = raw_sum / len(skills)

        # Weighted average (by effective_weight)
        weighted_sum = sum(s.weighted_score for s in skills)
        weight_sum = sum(s.effective_weight for s in skills)
        weighted_average = weighted_sum / max(weight_sum, config.min_weight_sum)

        # Coverage ratio (fraction above threshold)
        covered = sum(1 for s in skills if s.raw_score >= config.coverage_threshold)
        coverage_ratio = covered / len(skills)

        # Weighted contribution to final score
        weighted_contribution = weighted_average * cat_weight

        category_scores.append(CategoryScore(
            category=cat,
            category_weight=cat_weight,
            skill_scores=skills,
            raw_average=round(raw_average, config.score_precision),
            weighted_average=round(weighted_average, config.score_precision),
            coverage_ratio=round(coverage_ratio, config.score_precision),
            weighted_contribution=round(weighted_contribution, config.score_precision)
        ))

    return category_scores


def calculate_specialist_generalist_metrics(
    skill_scores: list[SkillScore],
    config: ScoringConfig
) -> tuple[float, float, float]:
    """
    Calculate specialist/generalist metrics from skill scores.

    Returns:
        (weighted_score, coverage_score, topk_score)

    weighted_score: Favors specialists who excel at high-weight skills
    coverage_score: Favors generalists with broad competence
    topk_score: Measures excellence on most critical skills
    """
    if not skill_scores:
        return 0.0, 0.0, 0.0

    # 1. Weighted Score (specialist metric)
    # Higher weights contribute more, so excelling at critical skills matters more
    weighted_sum = sum(s.weighted_score for s in skill_scores)
    weight_sum = sum(s.effective_weight for s in skill_scores)
    weighted_score = weighted_sum / max(weight_sum, config.min_weight_sum)

    # 2. Coverage Score (generalist metric)
    # Percentage of skills above coverage threshold
    covered = sum(1 for s in skill_scores if s.raw_score >= config.coverage_threshold)
    coverage_score = (covered / len(skill_scores)) * 10.0  # Scale to 0-10

    # 3. Top-K Critical Score (critical skill excellence)
    # Sort by effective_weight (highest first), take top K
    sorted_by_weight = sorted(skill_scores, key=lambda s: s.effective_weight, reverse=True)
    top_k = sorted_by_weight[:min(config.top_k_count, len(sorted_by_weight))]
    if top_k:
        topk_score = sum(s.raw_score for s in top_k) / len(top_k)
    else:
        topk_score = 0.0

    return (
        round(weighted_score, config.score_precision),
        round(coverage_score, config.score_precision),
        round(topk_score, config.score_precision)
    )


def combine_specialist_generalist(
    weighted_score: float,
    coverage_score: float,
    topk_score: float,
    config: ScoringConfig
) -> float:
    """
    Combine specialist/generalist metrics into a single skill dimension score.

    The combination weights can be adjusted per-role via config.
    Default: 50% weighted, 30% coverage, 20% top-k.
    """
    combined = (
        weighted_score * config.weighted_score_emphasis +
        coverage_score * config.coverage_score_emphasis +
        topk_score * config.topk_score_emphasis
    )
    return round(combined, config.score_precision)


def calculate_dimension_scores(
    category_scores: list[CategoryScore],
    dimension_weights: list[dict],
    specialist_generalist_score: float,
    config: ScoringConfig
) -> list[DimensionScore]:
    """
    Calculate dimension-level scores.

    Each dimension aggregates relevant signals:
    - technical_fit: From skill category scores
    - experience_fit: From experience-related tradeoffs (computed separately)
    - trajectory_fit: From trajectory matching (computed separately)
    - culture_fit: From soft skill categories
    - problem_solving_fit: From problem-type matching (computed separately)

    For now, we compute technical_fit from skills.
    Other dimensions would need tradeoff and trajectory matching data.
    """
    dimension_scores = []

    for dw in dimension_weights:
        dim = dw.get("dimension", "")
        weight = dw.get("weight", 0.2)
        description = dw.get("description", "")

        # Calculate dimension-specific raw score
        if dim == "technical_fit":
            # Use the specialist/generalist combined score
            raw_score = specialist_generalist_score
            factors = ["skill_weighted_average", "skill_coverage", "critical_skill_excellence"]
        else:
            # For other dimensions, aggregate relevant category scores
            # This is a simplified implementation - full version would
            # include tradeoff matching, trajectory matching, etc.
            if category_scores:
                raw_score = sum(cs.weighted_contribution for cs in category_scores)
            else:
                raw_score = 5.0  # Default neutral score
            factors = ["category_aggregation"]

        weighted_contribution = raw_score * weight

        dimension_scores.append(DimensionScore(
            dimension=dim,
            dimension_weight=weight,
            description=description,
            raw_score=round(raw_score, config.score_precision),
            weighted_contribution=round(weighted_contribution, config.score_precision),
            contributing_factors=factors
        ))

    return dimension_scores


def evaluate_constraints(
    hard_constraints: list[dict],
    candidate_resume_text: str,
    config: ScoringConfig
) -> tuple[list[ConstraintResult], float]:
    """
    Evaluate hard constraints against candidate.

    Returns:
        (constraint_results, ceiling): List of results and max achievable score
    """
    results = []
    ceiling = 10.0  # Start with max possible

    resume_lower = candidate_resume_text.lower()

    for constraint in hard_constraints:
        ct = constraint.get("constraint_type", "")
        original_text = constraint.get("original_text", "")
        description = constraint.get("description", "")
        severity = constraint.get("severity", "important")
        resume_check = constraint.get("resume_check", "")

        # Simple keyword-based check (real implementation would be more sophisticated)
        # Check if any keywords from the constraint appear in resume
        check_words = set(description.lower().split())
        resume_words = set(resume_lower.split())
        overlap = check_words & resume_words

        # Determine violation
        # For dealbreakers and required_day1: violation = NOT found in resume
        # For acceptable_gap: it's okay if not found
        is_violated = False
        evidence = ""
        score_impact = 0.0

        if ct == "dealbreaker":
            # Dealbreaker behaviors - if found, it's bad
            if overlap:
                is_violated = True
                evidence = f"Found concerning indicators: {', '.join(list(overlap)[:3])}"
                score_impact = 10.0 - config.dealbreaker_ceiling
                ceiling = min(ceiling, config.dealbreaker_ceiling)
            else:
                evidence = "No concerning indicators found"

        elif ct == "required_day1":
            # Required on day 1 - must be present
            if not overlap:
                is_violated = True
                evidence = "Required capability not evident in resume"
                score_impact = config.required_day1_penalty
                ceiling = max(0, ceiling - config.required_day1_penalty)
            else:
                evidence = f"Capability indicated: {', '.join(list(overlap)[:3])}"

        elif ct == "acceptable_gap":
            # Acceptable if missing - minor impact
            if not overlap:
                is_violated = True
                evidence = "Gap present but acceptable for this role"
                score_impact = config.acceptable_gap_penalty
                ceiling = max(0, ceiling - config.acceptable_gap_penalty)
            else:
                evidence = "No gap - candidate has this"

        results.append(ConstraintResult(
            constraint_type=ct,
            original_text=original_text,
            is_violated=is_violated,
            severity=severity,
            evidence=evidence,
            score_impact=round(score_impact, config.score_precision)
        ))

    return results, round(ceiling, config.score_precision)


def calculate_final_score(
    dimension_scores: list[DimensionScore],
    constraint_ceiling: float,
    config: ScoringConfig
) -> tuple[float, float]:
    """
    Calculate final composite score.

    Returns:
        (raw_score, final_score): Raw before capping, final after constraint ceiling
    """
    if not dimension_scores:
        return 0.0, 0.0

    # Sum of weighted contributions
    raw_score = sum(ds.weighted_contribution for ds in dimension_scores)

    # Normalize by sum of weights
    weight_sum = sum(ds.dimension_weight for ds in dimension_scores)
    if weight_sum > config.min_weight_sum:
        raw_score = raw_score / weight_sum

    # Apply constraint ceiling
    final_score = min(raw_score, constraint_ceiling)

    return (
        round(raw_score, config.score_precision),
        round(final_score, config.score_precision)
    )


def generate_match_summary(
    skill_scores: list[SkillScore],
    constraint_results: list[ConstraintResult],
    final_score: float,
    config: ScoringConfig
) -> str:
    """Generate a human-readable summary of the match."""
    # Count matches by type
    exact = sum(1 for s in skill_scores if s.match_type == "exact")
    strong = sum(1 for s in skill_scores if s.match_type == "strong")
    partial = sum(1 for s in skill_scores if s.match_type == "partial")
    none = sum(1 for s in skill_scores if s.match_type == "none")

    # Count constraint issues
    violations = sum(1 for c in constraint_results if c.is_violated)
    dealbreaker_hit = any(
        c.is_violated and c.constraint_type == "dealbreaker"
        for c in constraint_results
    )

    parts = [
        f"Score: {final_score}/10.",
        f"Skills: {exact} exact, {strong} strong, {partial} partial, {none} missing.",
    ]

    if dealbreaker_hit:
        parts.append("DEALBREAKER TRIGGERED - score capped.")
    elif violations > 0:
        parts.append(f"{violations} constraint violations reduced score ceiling.")

    return " ".join(parts)


def score_candidate(
    framework: dict,
    candidate: dict,
    config: ScoringConfig | None = None
) -> CandidateScore:
    """
    Main entry point: Score a candidate against an evaluation framework.

    Args:
        framework: The evaluation framework (post-processed)
        candidate: Candidate data including:
            - candidate_id: Unique identifier
            - skills: List of skill strings from resume
            - resume_text: Full resume text for constraint checking
        config: Optional scoring configuration

    Returns:
        CandidateScore with complete hierarchical scoring breakdown
    """
    if config is None:
        config = DEFAULT_SCORING_CONFIG

    candidate_id = candidate.get("candidate_id", "unknown")
    job_id = framework.get("role_context", {}).get("job_id", "unknown")
    candidate_skills = candidate.get("skills", [])
    resume_text = candidate.get("resume_text", "")

    # Level 1: Individual skill matching
    skill_criteria = framework.get("skill_criteria", {})
    framework_skills = skill_criteria.get("skills", [])

    skill_scores = [
        calculate_skill_score(skill, candidate_skills, config)
        for skill in framework_skills
    ]

    # Calculate specialist/generalist metrics
    weighted_score, coverage_score, topk_score = calculate_specialist_generalist_metrics(
        skill_scores, config
    )
    sg_combined = combine_specialist_generalist(
        weighted_score, coverage_score, topk_score, config
    )

    # Level 2: Category aggregation
    category_weights = skill_criteria.get("category_weights", [])
    category_scores = aggregate_category_scores(skill_scores, category_weights, config)

    # Evaluate constraints
    hard_constraints = framework.get("hard_constraints", [])
    constraint_results, constraint_ceiling = evaluate_constraints(
        hard_constraints, resume_text, config
    )

    # Level 3: Dimension aggregation
    dimension_weights = framework.get("dimension_weights", [])
    dimension_scores = calculate_dimension_scores(
        category_scores, dimension_weights, sg_combined, config
    )

    # Level 4: Final score
    raw_composite, final_score = calculate_final_score(
        dimension_scores, constraint_ceiling, config
    )

    # Generate summary
    match_summary = generate_match_summary(
        skill_scores, constraint_results, final_score, config
    )

    # Build detailed breakdown
    scoring_breakdown = {
        "skill_match_summary": {
            "total_skills": len(skill_scores),
            "exact_matches": sum(1 for s in skill_scores if s.match_type == "exact"),
            "strong_matches": sum(1 for s in skill_scores if s.match_type == "strong"),
            "partial_matches": sum(1 for s in skill_scores if s.match_type == "partial"),
            "no_matches": sum(1 for s in skill_scores if s.match_type == "none"),
        },
        "specialist_vs_generalist": {
            "weighted_score": weighted_score,
            "coverage_score": coverage_score,
            "topk_critical_score": topk_score,
            "combined_score": sg_combined,
            "emphasis_weights": {
                "weighted": config.weighted_score_emphasis,
                "coverage": config.coverage_score_emphasis,
                "topk": config.topk_score_emphasis,
            }
        },
        "category_breakdown": [
            {
                "category": cs.category,
                "weight": cs.category_weight,
                "weighted_average": cs.weighted_average,
                "coverage_ratio": cs.coverage_ratio,
                "contribution": cs.weighted_contribution,
            }
            for cs in category_scores
        ],
        "dimension_breakdown": [
            {
                "dimension": ds.dimension,
                "weight": ds.dimension_weight,
                "raw_score": ds.raw_score,
                "contribution": ds.weighted_contribution,
            }
            for ds in dimension_scores
        ],
        "constraint_summary": {
            "total_constraints": len(constraint_results),
            "violations": sum(1 for c in constraint_results if c.is_violated),
            "ceiling_after_constraints": constraint_ceiling,
        },
        "scoring_config": {
            "coverage_threshold": config.coverage_threshold,
            "top_k_count": config.top_k_count,
            "dealbreaker_ceiling": config.dealbreaker_ceiling,
        }
    }

    return CandidateScore(
        candidate_id=candidate_id,
        job_id=job_id,
        skill_scores=skill_scores,
        category_scores=category_scores,
        dimension_scores=dimension_scores,
        constraint_results=constraint_results,
        constraint_ceiling=constraint_ceiling,
        weighted_skill_score=weighted_score,
        coverage_score=coverage_score,
        topk_critical_score=topk_score,
        raw_composite_score=raw_composite,
        final_score=final_score,
        percentile_rank=0.0,  # Computed when ranking multiple candidates
        scoring_breakdown=scoring_breakdown,
        match_summary=match_summary
    )


def rank_candidates(
    framework: dict,
    candidates: list[dict],
    config: ScoringConfig | None = None
) -> list[CandidateScore]:
    """
    Score and rank multiple candidates.

    Returns list of CandidateScore sorted by final_score descending,
    with percentile_rank populated.
    """
    if config is None:
        config = DEFAULT_SCORING_CONFIG

    # Score all candidates
    scored = [score_candidate(framework, c, config) for c in candidates]

    # Sort by final_score descending
    scored.sort(key=lambda s: s.final_score, reverse=True)

    # Calculate percentile ranks
    n = len(scored)
    for i, s in enumerate(scored):
        # Percentile: what percentage of candidates scored lower
        s.percentile_rank = round(((n - i - 1) / max(n - 1, 1)) * 100, 1)

    return scored


def to_dict(score: CandidateScore) -> dict:
    """Convert CandidateScore to dictionary for JSON serialization."""
    return {
        "candidate_id": score.candidate_id,
        "job_id": score.job_id,
        "final_score": score.final_score,
        "raw_composite_score": score.raw_composite_score,
        "percentile_rank": score.percentile_rank,
        "constraint_ceiling": score.constraint_ceiling,
        "specialist_vs_generalist": {
            "weighted_score": score.weighted_skill_score,
            "coverage_score": score.coverage_score,
            "topk_critical_score": score.topk_critical_score,
        },
        "skill_scores": [
            {
                "skill_id": s.skill_id,
                "skill_name": s.skill_name,
                "category": s.category,
                "raw_score": s.raw_score,
                "weight": s.weight,
                "effective_weight": s.effective_weight,
                "weighted_score": s.weighted_score,
                "is_required": s.is_required,
                "match_type": s.match_type,
                "match_evidence": s.match_evidence,
            }
            for s in score.skill_scores
        ],
        "category_scores": [
            {
                "category": c.category,
                "category_weight": c.category_weight,
                "weighted_average": c.weighted_average,
                "coverage_ratio": c.coverage_ratio,
                "weighted_contribution": c.weighted_contribution,
            }
            for c in score.category_scores
        ],
        "dimension_scores": [
            {
                "dimension": d.dimension,
                "dimension_weight": d.dimension_weight,
                "raw_score": d.raw_score,
                "weighted_contribution": d.weighted_contribution,
            }
            for d in score.dimension_scores
        ],
        "constraint_results": [
            {
                "constraint_type": c.constraint_type,
                "original_text": c.original_text,
                "is_violated": c.is_violated,
                "severity": c.severity,
                "evidence": c.evidence,
                "score_impact": c.score_impact,
            }
            for c in score.constraint_results
        ],
        "scoring_breakdown": score.scoring_breakdown,
        "match_summary": score.match_summary,
    }

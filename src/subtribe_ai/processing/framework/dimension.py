"""Dimension weight derivation from calibration selections.

All derivations are purely algorithmic based on selection patterns.
No hardcoded role-specific logic.
"""

from typing import Any

from subtribe_ai.processing.framework.config import PostProcessingConfig

REQUIRED_DIMENSIONS = [
    "technical_fit",
    "experience_fit",
    "trajectory_fit",
    "culture_fit",
    "problem_solving_fit",
]


def derive_dimension_weights_from_selections(calibration: dict) -> dict[str, float]:
    """Derive dimension weights purely from selection patterns.

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
    ratios: dict[str, float] = {}

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
    derived: dict[str, float] = {}

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


def ensure_all_dimensions_present(
    framework: dict,
    derived_weights: dict[str, float]
) -> dict[str, Any]:
    """Ensure all 5 required dimensions are present in framework.

    Add missing dimensions with derived weights.
    """
    result: dict[str, Any] = {
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
                "weight_rationale": (
                    "Added during post-processing - was missing from LLM output. "
                    "Weight derived from calibration selection patterns."
                ),
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
    derived_weights: dict[str, float],
    config: PostProcessingConfig
) -> dict[str, Any]:
    """Compare LLM-generated dimension weights with derived weights.

    Flag if divergence exceeds threshold.
    Role-agnostic - compares whatever dimensions exist.
    """
    result: dict[str, Any] = {
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

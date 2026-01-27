"""Framework post-processing pipeline.

Main entry point for framework validation and normalization.
"""

from datetime import datetime
from typing import Any

from subtribe_ai.processing.framework.config import (
    DEFAULT_CONFIG,
    PostProcessingConfig,
    PostProcessingResult,
)
from subtribe_ai.processing.framework.dimension import (
    compare_dimension_weights,
    derive_dimension_weights_from_selections,
    ensure_all_dimensions_present,
)
from subtribe_ai.processing.framework.enum_normalizer import (
    normalize_enum_values_in_framework,
)
from subtribe_ai.processing.framework.validators import (
    add_missing_items_with_defaults,
    apply_selection_multipliers,
    normalize_weights,
    review_suspicious_items,
    validate_and_fix_ids,
    validate_completeness,
    validate_custom_boost,
    validate_skill_counts,
)


def run_post_processing_pipeline(
    calibration: dict,
    framework: dict,
    config: PostProcessingConfig | None = None
) -> PostProcessingResult:
    """Run the complete post-processing pipeline.

    Pipeline stages (all role-agnostic):
    0. Enum normalization (PascalCase -> snake_case)
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
    stages: dict[str, Any] = {}
    metadata: dict[str, Any] = {
        "completed_at": datetime.utcnow().isoformat(),
        "version": "1.1",
        "config": {
            "missing_error_threshold_pct": config.missing_error_threshold_pct,
            "id_match_similarity_threshold": config.id_match_similarity_threshold,
            "text_match_similarity_threshold": config.text_match_similarity_threshold,
            "weight_divergence_threshold_pct": config.weight_divergence_threshold_pct,
        },
        "stages": stages,
    }

    # Stage 0: Enum normalization (MUST run first)
    enum_norm = normalize_enum_values_in_framework(framework)
    stages["enum_normalization"] = enum_norm
    if enum_norm["normalized_count"] > 0:
        result.warnings.append({
            "stage": "enum_normalization",
            "message": (
                f"Normalized {enum_norm['normalized_count']} enum values "
                "from PascalCase to snake_case"
            ),
        })

    # Stage 1: Completeness validation
    completeness = validate_completeness(calibration, framework, config)
    stages["completeness"] = completeness

    # Decision: If missing > threshold, raise error. Otherwise, add defaults.
    if completeness["missing_percentage"] > config.missing_error_threshold_pct:
        result.errors.append({
            "stage": "completeness",
            "message": (
                f"Missing {completeness['missing_percentage']:.1f}% of selected items "
                f"(threshold: {config.missing_error_threshold_pct}%)"
            ),
            "details": completeness
        })
    elif not completeness["passed"]:
        # Add missing items with defaults
        add_result = add_missing_items_with_defaults(calibration, framework, completeness, config)
        stages["completeness"]["items_added"] = add_result
        result.warnings.append({
            "stage": "completeness",
            "message": (
                f"Added {add_result['skills_added']} skills and "
                f"{add_result['constraints_added']} constraints with default weights"
            ),
        })

    # Stage 2: ID validation and fixing
    id_validation = validate_and_fix_ids(calibration, framework, config)
    stages["id_validation"] = id_validation

    if id_validation["skill_fixes"] or id_validation["tradeoff_fixes"]:
        result.warnings.append({
            "stage": "id_validation",
            "message": (
                f"Fixed {len(id_validation['skill_fixes'])} skill IDs and "
                f"{len(id_validation['tradeoff_fixes'])} tradeoff IDs using Levenshtein matching"
            ),
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
    stages["weight_normalization"] = weight_norm

    # Stage 4: Selection multipliers
    multipliers = apply_selection_multipliers(calibration, framework, config)
    stages["selection_multipliers"] = multipliers

    # Stage 5: Custom boost validation
    custom_boost = validate_custom_boost(calibration, framework)
    stages["custom_boost"] = custom_boost

    if custom_boost["items_with_low_weight"]:
        result.warnings.append({
            "stage": "custom_boost",
            "message": (
                f"Found {len(custom_boost['items_with_low_weight'])} "
                "custom items with potentially low weights"
            ),
            "details": custom_boost["items_with_low_weight"],
        })

    # Stage 6: Skill counts
    skill_counts = validate_skill_counts(framework)
    stages["skill_counts"] = skill_counts

    # Stage 7: Dimension weight derivation and comparison
    derived_weights = derive_dimension_weights_from_selections(calibration)
    stages["derived_dimension_weights"] = derived_weights

    # Ensure all 5 required dimensions are present
    dimension_check = ensure_all_dimensions_present(framework, derived_weights)
    stages["dimension_completeness"] = dimension_check

    if dimension_check["dimensions_added"]:
        result.warnings.append({
            "stage": "dimension_completeness",
            "message": (
                f"Added {len(dimension_check['dimensions_added'])} missing dimensions: "
                f"{', '.join(dimension_check['dimensions_added'])}"
            ),
        })

    weight_comparison = compare_dimension_weights(
        framework.get("dimension_weights", []),
        derived_weights,
        config
    )
    stages["dimension_weight_comparison"] = weight_comparison

    if weight_comparison["needs_override"]:
        result.warnings.append({
            "stage": "dimension_weights",
            "message": (
                f"LLM weights diverge from derived weights by "
                f"{weight_comparison['max_divergence']}% "
                f"(threshold: {config.weight_divergence_threshold_pct}%)"
            ),
            "details": weight_comparison["divergent_dimensions"],
        })
        # Note: We don't auto-override in v1, just warn

    # Stage 8: Suspicious items review
    suspicious = review_suspicious_items(framework)
    stages["suspicious_items"] = suspicious

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

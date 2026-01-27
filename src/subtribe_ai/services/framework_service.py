"""Evaluation framework creation service.

Orchestrates calibration response -> framework generation -> post-processing.
"""

from typing import TypedDict


class FrameworkResult(TypedDict, total=False):
    """Result from framework creation."""
    framework: dict
    post_processing: dict
    timing: dict


class FrameworkService:
    """Service for creating evaluation frameworks from calibration decisions.

    Usage:
        service = FrameworkService()
        result = service.create(calibration_response)
    """

    def __init__(self, enable_tracing: bool = False):
        """Initialize the framework service.

        Args:
            enable_tracing: Whether to enable Langfuse tracing.
        """
        self._enable_tracing = enable_tracing

    def create(self, calibration_response: dict) -> FrameworkResult:
        """Create an evaluation framework from calibration decisions.

        Post-processing pipeline:
        1. Validate completeness (error if >30% missing, add defaults if <=30%)
        2. Fix ID mismatches using Levenshtein distance
        3. Normalize weights to sum to 1.0
        4. Apply selection multipliers (1.0 selected, 0.3 unselected)
        5. Validate custom item boost
        6. Validate skill counts
        7. Compare dimension weights with derived (warn if >20% divergence)

        Args:
            calibration_response: The calibration summary JSON with user selections.

        Returns:
            FrameworkResult with framework and post_processing metadata.
        """
        import time

        from subtribe_ai.baml_client import b
        from subtribe_ai.baml_client.types import CalibrationResponse
        from subtribe_ai.processing.framework import (
            run_post_processing_pipeline,
            PostProcessingResult,
        )

        start = time.time()

        # Parse calibration
        calibration = CalibrationResponse(**calibration_response)

        # Call BAML
        baml_response = b.CreateEvaluationFramework(calibration=calibration)

        # Convert to dict for post-processing
        framework_dict = baml_response.model_dump(mode="json")

        # Run post-processing
        pp_result: PostProcessingResult = run_post_processing_pipeline(
            calibration=calibration_response,
            framework=framework_dict,
        )

        result: FrameworkResult = {
            "framework": pp_result.framework,
            "post_processing": {
                "errors": pp_result.errors,
                "warnings": pp_result.warnings,
                "requires_human_review": pp_result.requires_human_review,
                "metadata": pp_result.metadata,
            },
        }

        # Add timing
        result["timing"] = {"seconds": round(time.time() - start, 2)}

        return result

"""Candidate evaluation service.

Evaluates parsed resume JSON against evaluation framework.
"""

import json
import time
from typing import TypedDict


class EvaluationResult(TypedDict):
    """Result from candidate evaluation."""

    scores: dict
    skill_matches: list
    dimension_assessments: list
    constraint_results: list
    summary: dict
    timing: dict


class EvaluationService:
    """Service for evaluating candidates against evaluation frameworks.

    Usage:
        service = EvaluationService()
        result = service.evaluate(parsed_resume, framework)
    """

    def __init__(self, enable_tracing: bool = False):
        """Initialize the evaluation service.

        Args:
            enable_tracing: Whether to enable Langfuse tracing.
        """
        self._enable_tracing = enable_tracing

    def evaluate(self, parsed_resume: dict, framework: dict) -> EvaluationResult:
        """Evaluate a parsed candidate resume against an evaluation framework.

        Args:
            parsed_resume: Parsed resume JSON from ParseResume.
            framework: Evaluation framework from FrameworkService.

        Returns:
            EvaluationResult with scores, matches, and assessments.
        """
        from subtribe_ai.baml_client import b
        from subtribe_ai.processing.evaluation_processor import run_evaluation_pipeline

        total_start = time.time()

        # Serialize inputs to JSON strings for BAML
        framework_json = json.dumps(framework, indent=2)
        parsed_resume_json = json.dumps(parsed_resume, indent=2)

        # Call BAML evaluation
        eval_start = time.time()
        baml_response = b.EvaluateCandidate(
            framework_json=framework_json,
            parsed_resume_json=parsed_resume_json,
        )
        eval_time = time.time() - eval_start

        # Convert to dict
        evaluation_dict = baml_response.model_dump(mode="json")

        # Run scoring post-processing
        result = run_evaluation_pipeline(
            evaluation=evaluation_dict,
            framework=framework,
        )

        # Add timing
        result["timing"] = {
            "evaluation_seconds": round(eval_time, 2),
            "total_seconds": round(time.time() - total_start, 2),
        }

        return result
